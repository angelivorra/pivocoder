#!/usr/bin/env python3
"""RoboGuitarra — FluidSynth web controller con interfaz 8-bit."""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from pathlib import Path
from typing import Optional

import fluidsynth
import rtmidi
from flask import Flask, jsonify, render_template, request, Response, stream_with_context

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

SF2_DIR = Path("/home/patch/pivocoder/sf2")
STATE_FILE = Path(__file__).parent / "state.json"
app = Flask(__name__)

# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}

def _save_state(key: str, value) -> None:
    state = _load_state()
    state[key] = value
    STATE_FILE.write_text(json.dumps(state, indent=2))

# ---------------------------------------------------------------------------
# Motor FluidSynth
# ---------------------------------------------------------------------------

class FluidEngine:
    def __init__(self):
        self._synth: Optional[fluidsynth.Synth] = None
        self._sfid: Optional[int] = None
        self._loaded_sf2: Optional[str] = None
        self._audio_driver: Optional[str] = None
        self._audio_device: Optional[str] = None
        self._lock = threading.Lock()

    def _ensure_synth(self):
        """Crea e inicia el sintetizador si no está activo."""
        if self._synth is not None:
            return
        state = _load_state()
        saved_driver = state.get("audio_driver")
        saved_device = state.get("audio_device")
        self._start_synth(saved_driver, saved_device)

    def _start_synth(self, driver: Optional[str] = None, device: Optional[str] = None):
        """(Re)crea el sintetizador con el driver/device indicados."""
        if self._synth is not None:
            self._synth.delete()
            self._synth = None
            self._audio_driver = None
            self._audio_device = None

        # JACK corre a 48000 Hz en este sistema; usar ese samplerate
        samplerate = 48000 if (driver == "jack" or (driver is None and _jack_running())) else 44100

        candidates = [driver] if driver else ["jack", "alsa", "pulseaudio"]
        for drv in candidates:
            try:
                synth = fluidsynth.Synth(gain=1.0, samplerate=float(samplerate))
                if drv == "jack":
                    synth.setting("audio.jack.autoconnect", 1)
                kwargs = {"driver": drv}
                if device:
                    kwargs["device"] = device
                synth.start(**kwargs)
                self._synth = synth
                self._audio_driver = drv
                self._audio_device = device
                print(f"[roboguitarra] Audio: {drv}" + (f" / {device}" if device else ""))
                return
            except Exception as exc:
                print(f"[roboguitarra] Audio driver '{drv}' falló: {exc}")
                try:
                    synth.delete()
                except Exception:
                    pass

    def _get_presets_locked(self, sfid: int) -> list[dict]:
        """Devuelve todos los presets disponibles en el SF2. Requiere _lock."""
        presets = []
        for bank in range(128):
            for num in range(128):
                name = self._synth.sfpreset_name(sfid, bank, num)
                if name:
                    presets.append({"bank": bank, "preset": num, "name": name})
        return presets

    def load_sf2(self, sf2_path: str) -> dict:
        with self._lock:
            self._ensure_synth()
            if self._sfid is not None:
                self._synth.sfunload(self._sfid)
                self._sfid = None
            sfid = self._synth.sfload(sf2_path)
            if sfid == -1:
                return {"ok": False, "error": f"No se pudo cargar {sf2_path}"}
            self._sfid = sfid
            self._loaded_sf2 = Path(sf2_path).name

            presets = self._get_presets_locked(sfid)

            # Aplicar instrumento guardado o el primero disponible
            saved = _load_state().get("instruments", {}).get(self._loaded_sf2)
            if saved and any(
                p["bank"] == saved["bank"] and p["preset"] == saved["preset"]
                for p in presets
            ):
                selected = saved
            elif presets:
                selected = presets[0]
            else:
                selected = {"bank": 0, "preset": 0, "name": "default"}

            for ch in range(16):
                self._synth.program_select(ch, sfid, selected["bank"], selected["preset"])
            _save_state("sf2", self._loaded_sf2)
            return {
                "ok": True, "sf2": self._loaded_sf2, "sfid": sfid,
                "presets": presets, "selected": selected,
            }

    def note_on(self, channel: int, note: int, velocity: int) -> bool:
        with self._lock:
            if self._synth is None:
                return False
            self._synth.noteon(channel, note, velocity)
            return True

    def note_off(self, channel: int, note: int) -> bool:
        with self._lock:
            if self._synth is None:
                return False
            self._synth.noteoff(channel, note)
            return True

    def program_change(self, channel: int, bank: int, preset: int) -> bool:
        with self._lock:
            if self._synth is None or self._sfid is None:
                return False
            self._synth.program_select(channel, self._sfid, bank, preset)
            return True

    def select_instrument(self, bank: int, preset: int, name: str) -> bool:
        """Selecciona instrumento y lo guarda como predeterminado para el SF2 actual."""
        with self._lock:
            if self._synth is None or self._sfid is None:
                return False
            for ch in range(16):
                self._synth.program_select(ch, self._sfid, bank, preset)
            if self._loaded_sf2:
                state = _load_state()
                state.setdefault("instruments", {})[self._loaded_sf2] = {
                    "bank": bank, "preset": preset, "name": name
                }
                STATE_FILE.write_text(json.dumps(state, indent=2))
            return True

    def restart_audio(self, driver: str, device: Optional[str] = None) -> dict:
        """Reinicia el sintetizador con nuevo driver/device, recarga el SF2."""
        with self._lock:
            sf2_to_reload = self._loaded_sf2
            self._sfid = None
            self._loaded_sf2 = None
            self._start_synth(driver, device)
            if self._synth is None:
                return {"ok": False, "error": f"No se pudo iniciar driver '{driver}'"}
            _save_state("audio_driver", driver)
            _save_state("audio_device", device)
            # Recargar SF2 si había uno cargado
            if sf2_to_reload:
                sf2_path = SF2_DIR / sf2_to_reload
                if sf2_path.exists():
                    self._reload_sf2_locked(str(sf2_path))
            return {"ok": True, "driver": driver, "device": device}

    def _reload_sf2_locked(self, sf2_path: str):
        """Recarga el SF2 actual. Debe llamarse con _lock."""
        sfid = self._synth.sfload(sf2_path)
        if sfid == -1:
            return
        self._sfid = sfid
        self._loaded_sf2 = Path(sf2_path).name
        saved = _load_state().get("instruments", {}).get(self._loaded_sf2)
        bank   = saved["bank"]   if saved else 0
        preset = saved["preset"] if saved else 0
        for ch in range(16):
            self._synth.program_select(ch, sfid, bank, preset)

    def destroy(self):
        with self._lock:
            if self._synth is not None:
                self._synth.delete()
                self._synth = None
                self._sfid = None
                self._loaded_sf2 = None
                self._audio_driver = None
                self._audio_device = None

    @property
    def loaded_sf2(self) -> Optional[str]:
        return self._loaded_sf2

    @property
    def audio_driver(self) -> Optional[str]:
        return self._audio_driver

    @property
    def audio_device(self) -> Optional[str]:
        return self._audio_device

    @property
    def is_running(self) -> bool:
        return self._synth is not None


# ---------------------------------------------------------------------------
# Estado global
# ---------------------------------------------------------------------------

engine = FluidEngine()

_midi_in: Optional[rtmidi.MidiIn] = None
_midi_port_name: Optional[str] = None
_midi_lock = threading.Lock()

# Cola de eventos MIDI para SSE (máx 200 eventos)
_midi_event_queues: list[queue.Queue] = []
_midi_event_queues_lock = threading.Lock()


# ---------------------------------------------------------------------------
# MIDI listener
# ---------------------------------------------------------------------------

NOTE_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

def _note_name(midi_note: int) -> str:
    return f"{NOTE_NAMES[midi_note % 12]}{midi_note // 12 - 1}"

def _push_midi_event(event: dict) -> None:
    payload = json.dumps(event)
    with _midi_event_queues_lock:
        for q in _midi_event_queues:
            try:
                q.put_nowait(payload)
            except queue.Full:
                pass

def _midi_callback(message, _data):
    """Reenvía mensajes MIDI al sintetizador en modo OMNI (canal 0 siempre)."""
    msg, _ = message
    if not msg:
        return
    status = msg[0] & 0xF0
    in_ch  = msg[0] & 0x0F   # canal original (solo para el log)
    ts = time.strftime("%H:%M:%S")

    if status == 0x90 and len(msg) >= 3:
        vel = msg[2]
        note = msg[1]
        if vel > 0:
            engine.note_on(0, note, vel)
            _push_midi_event({"type": "NOTE_ON", "ch": in_ch, "note": note,
                               "name": _note_name(note), "vel": vel, "ts": ts})
        else:
            engine.note_off(0, note)
            _push_midi_event({"type": "NOTE_OFF", "ch": in_ch, "note": note,
                               "name": _note_name(note), "vel": 0, "ts": ts})
    elif status == 0x80 and len(msg) >= 3:
        note = msg[1]
        engine.note_off(0, note)
        _push_midi_event({"type": "NOTE_OFF", "ch": in_ch, "note": note,
                           "name": _note_name(note), "vel": 0, "ts": ts})
    elif status == 0xC0 and len(msg) >= 2:
        engine.program_change(0, 0, msg[1])
        _push_midi_event({"type": "PROG_CHG", "ch": in_ch, "prog": msg[1],
                           "name": f"PC {msg[1]}", "vel": 0, "ts": ts})
    elif status == 0xB0 and len(msg) >= 3:
        _push_midi_event({"type": "CC", "ch": in_ch, "cc": msg[1],
                           "name": f"CC{msg[1]}", "vel": msg[2], "ts": ts})
    elif status == 0xE0 and len(msg) >= 3:
        bend = ((msg[2] << 7) | msg[1]) - 8192
        _push_midi_event({"type": "PITCH", "ch": in_ch, "bend": bend,
                           "name": "PITCH", "vel": 0, "ts": ts})


def _connect_midi(port_index: int, port_name: str):
    global _midi_in, _midi_port_name
    with _midi_lock:
        if _midi_in is not None:
            _midi_in.cancel_callback()
            _midi_in.close_port()
            _midi_in = None
            _midi_port_name = None
        midi_in = rtmidi.MidiIn()
        midi_in.open_port(port_index)
        midi_in.set_callback(_midi_callback)
        _midi_in = midi_in
        _midi_port_name = port_name
        _save_state("midi_port", port_name)


# ---------------------------------------------------------------------------
# Helpers de audio
# ---------------------------------------------------------------------------

def _jack_running() -> bool:
    import subprocess
    try:
        return subprocess.run(["pgrep", "-x", "jackd"], capture_output=True).returncode == 0
    except Exception:
        return False

def get_audio_devices() -> dict:
    import subprocess
    alsa_cards = []
    try:
        out = subprocess.check_output(["aplay", "-l"], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            if line.startswith("card "):
                # "card 3: pisound [pisound], device 0: ..."
                parts = line.split(":")
                card_num = parts[0].split()[1]
                card_name = parts[1].strip().split("[")[-1].rstrip("]").strip() \
                    if "[" in parts[1] else parts[1].strip().split(",")[0].strip()
                alsa_cards.append({
                    "label": f"ALSA: {card_name} (hw:{card_num})",
                    "driver": "alsa",
                    "device": f"hw:{card_num}",
                })
    except Exception:
        pass
    jack = _jack_running()
    drivers = []
    if jack:
        drivers.append({"label": "JACK (recomendado)", "driver": "jack", "device": None})
    drivers += alsa_cards
    drivers.append({"label": "PulseAudio", "driver": "pulseaudio", "device": None})
    return {"drivers": drivers, "jack_running": jack}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_sf2_files() -> list[str]:
    return sorted(p.name for p in SF2_DIR.glob("*.sf2"))


def get_midi_ports() -> list[dict]:
    tmp = rtmidi.MidiIn()
    ports = [{"index": i, "name": n} for i, n in enumerate(tmp.get_ports())]
    tmp.close_port()
    return ports


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    sf2 = engine.loaded_sf2
    saved_inst = _load_state().get("instruments", {}).get(sf2) if sf2 else None
    return jsonify({
        "running": engine.is_running,
        "loaded_sf2": sf2,
        "midi_port": _midi_port_name,
        "instrument": saved_inst,
        "audio_driver": engine.audio_driver,
        "audio_device": engine.audio_device,
    })


@app.route("/api/audio-info")
def api_audio_info():
    info = get_audio_devices()
    info["current_driver"] = engine.audio_driver
    info["current_device"] = engine.audio_device
    return jsonify(info)


@app.route("/api/set-audio", methods=["POST"])
def api_set_audio():
    data = request.get_json(silent=True) or {}
    driver = data.get("driver", "").strip()
    device = data.get("device") or None
    if not driver:
        return jsonify({"ok": False, "error": "Falta 'driver'"}), 400
    result = engine.restart_audio(driver, device)
    return jsonify(result)


@app.route("/api/sf2files")
def api_sf2files():
    return jsonify({"files": get_sf2_files()})


@app.route("/api/midi-ports")
def api_midi_ports():
    return jsonify({"ports": get_midi_ports()})


@app.route("/api/load-sf2", methods=["POST"])
def api_load_sf2():
    data = request.get_json(silent=True) or {}
    filename = data.get("file", "").strip()
    if not filename:
        return jsonify({"ok": False, "error": "Falta 'file'"}), 400
    sf2_path = SF2_DIR / filename
    if not sf2_path.exists():
        return jsonify({"ok": False, "error": f"No existe: {filename}"}), 404
    result = engine.load_sf2(str(sf2_path))
    return jsonify(result)


@app.route("/api/midi-connect", methods=["POST"])
def api_midi_connect():
    data = request.get_json(silent=True) or {}
    port_index = data.get("index")
    port_name = data.get("name", "")
    if port_index is None:
        return jsonify({"ok": False, "error": "Falta 'index'"}), 400
    try:
        _connect_midi(int(port_index), port_name)
        return jsonify({"ok": True, "port": port_name})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/noteon", methods=["POST"])
def api_noteon():
    data = request.get_json(silent=True) or {}
    note = int(data.get("note", 60))
    vel = int(data.get("velocity", 100))
    channel = int(data.get("channel", 0))
    ok = engine.note_on(channel, note, vel)
    return jsonify({"ok": ok})


@app.route("/api/noteoff", methods=["POST"])
def api_noteoff():
    data = request.get_json(silent=True) or {}
    note = int(data.get("note", 60))
    channel = int(data.get("channel", 0))
    ok = engine.note_off(channel, note)
    return jsonify({"ok": ok})


@app.route("/api/presets")
def api_presets():
    """Devuelve los presets del SF2 actualmente cargado."""
    with engine._lock:
        if engine._synth is None or engine._sfid is None:
            return jsonify({"presets": []})
        presets = engine._get_presets_locked(engine._sfid)
    return jsonify({"presets": presets})


@app.route("/api/select-instrument", methods=["POST"])
def api_select_instrument():
    data = request.get_json(silent=True) or {}
    bank   = int(data.get("bank", 0))
    preset = int(data.get("preset", 0))
    name   = data.get("name", "")
    ok = engine.select_instrument(bank, preset, name)
    return jsonify({"ok": ok, "bank": bank, "preset": preset, "name": name})


@app.route("/api/program", methods=["POST"])
def api_program():
    data = request.get_json(silent=True) or {}
    bank = int(data.get("bank", 0))
    preset = int(data.get("preset", 0))
    channel = int(data.get("channel", 0))
    ok = engine.program_change(channel, bank, preset)
    return jsonify({"ok": ok})


@app.route("/api/midi-stream")
def api_midi_stream():
    """SSE: emite eventos MIDI en tiempo real."""
    q: queue.Queue = queue.Queue(maxsize=200)
    with _midi_event_queues_lock:
        _midi_event_queues.append(q)

    def generate():
        try:
            yield "retry: 1000\n\n"
            while True:
                try:
                    payload = q.get(timeout=15)
                    yield f"data: {payload}\n\n"
                except queue.Empty:
                    yield ": ping\n\n"  # keep-alive
        finally:
            with _midi_event_queues_lock:
                _midi_event_queues.remove(q)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/restart-service", methods=["POST"])
def api_restart_service():
    """Reinicia el servicio systemd roboguitarra."""
    import subprocess
    try:
        subprocess.Popen(
            ["systemctl", "--user", "restart", "roboguitarra.service"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Auto-carga del último estado al arrancar
# ---------------------------------------------------------------------------

def _restore_state() -> None:
    import time
    time.sleep(1)  # esperar a que Flask esté listo
    state = _load_state()

    sf2_name = state.get("sf2")
    if sf2_name:
        sf2_path = SF2_DIR / sf2_name
        if sf2_path.exists():
            result = engine.load_sf2(str(sf2_path))
            print(f"[roboguitarra] SF2 restaurado: {sf2_name} → {result}")
        else:
            print(f"[roboguitarra] SF2 guardado no encontrado: {sf2_name}")

    midi_name = state.get("midi_port")
    if midi_name:
        ports = get_midi_ports()
        match = next((p for p in ports if p["name"] == midi_name), None)
        if match:
            try:
                _connect_midi(match["index"], match["name"])
                print(f"[roboguitarra] MIDI restaurado: {midi_name}")
            except Exception as exc:
                print(f"[roboguitarra] Error restaurando MIDI: {exc}")
        else:
            print(f"[roboguitarra] Puerto MIDI guardado no disponible: {midi_name}")

threading.Thread(target=_restore_state, daemon=True).start()


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)

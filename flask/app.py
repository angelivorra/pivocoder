#!/usr/bin/env python3
"""Pivocoder Flask Web Interface.

Gestiona Carla en modo headless y expone una interfaz web para controlar
el vocoder: cambio de presets, estado de JACK/Carla y reinicio del sistema.
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, render_template, request

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

PRESET_DIR = Path("/home/patch/pivocoder/prod")
CARLA_ENV = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Estado global de Carla
# ---------------------------------------------------------------------------

_carla_process: Optional[subprocess.Popen] = None
_current_preset: Optional[str] = None
_carla_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Gestión de Carla
# ---------------------------------------------------------------------------

def _stop_carla() -> None:
    """Detiene el proceso de Carla si está corriendo. Debe llamarse con _carla_lock."""
    global _carla_process, _current_preset
    if _carla_process is None:
        return
    if _carla_process.poll() is None:
        _carla_process.terminate()
        try:
            _carla_process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            _carla_process.kill()
            _carla_process.wait()
    _carla_process = None
    _current_preset = None


def _start_carla(preset_name: str) -> None:
    """Lanza Carla con el preset indicado. Debe llamarse con _carla_lock adquirido."""
    global _carla_process, _current_preset
    preset_path = PRESET_DIR / preset_name
    if not preset_path.exists():
        raise FileNotFoundError(f"Preset no encontrado: {preset_path}")
    _stop_carla()
    _carla_process = subprocess.Popen(
        ["carla", "-n", str(preset_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=CARLA_ENV,
    )
    _current_preset = preset_name


def get_sorted_presets() -> list[str]:
    """Devuelve los archivos .carxp de PRESET_DIR ordenados alfabéticamente."""
    return sorted(p.name for p in PRESET_DIR.glob("*.carxp"))


def is_jack_running() -> bool:
    """Comprueba si jackd está activo."""
    try:
        result = subprocess.run(
            ["jack_control", "status"],
            capture_output=True,
            timeout=2,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    try:
        result = subprocess.run(
            ["pgrep", "-x", "jackd"],
            capture_output=True,
            timeout=2,
        )
        return result.returncode == 0
    except Exception:
        return False


def is_carla_running() -> bool:
    """Comprueba si el proceso de Carla gestionado está vivo."""
    return _carla_process is not None and _carla_process.poll() is None


def init_carla() -> None:
    """Arranca Carla con el primer preset disponible al iniciar la app."""
    time.sleep(1)  # pequeña espera para que Flask esté listo
    presets = get_sorted_presets()
    if not presets:
        print("[pivocoder] No se encontraron presets en", PRESET_DIR)
        return
    with _carla_lock:
        try:
            _start_carla(presets[0])
            print(f"[pivocoder] Carla arrancada con '{presets[0]}'")
        except Exception as exc:
            print(f"[pivocoder] Error al arrancar Carla: {exc}")


# Lanzar Carla en segundo plano al importar el módulo
threading.Thread(target=init_carla, daemon=True).start()


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/robot")
def index_robot():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    carla_pid = (
        _carla_process.pid
        if _carla_process is not None and _carla_process.poll() is None
        else None
    )
    return jsonify({
        "jack": is_jack_running(),
        "carla": is_carla_running(),
        "preset": _current_preset,
        "carla_pid": carla_pid,
    })


@app.route("/api/presets")
def api_presets():
    return jsonify({
        "presets": get_sorted_presets(),
        "current": _current_preset,
    })


@app.route("/api/preset", methods=["POST"])
def api_load_preset():
    data = request.get_json(silent=True) or {}
    preset_name = data.get("preset", "").strip()
    if not preset_name:
        return jsonify({"error": "Falta el campo 'preset'"}), 400
    with _carla_lock:
        try:
            _start_carla(preset_name)
            return jsonify({"ok": True, "preset": preset_name})
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500


@app.route("/api/restart", methods=["POST"])
def api_restart():
    with _carla_lock:
        preset = _current_preset
        try:
            if preset:
                _start_carla(preset)
            else:
                presets = get_sorted_presets()
                if not presets:
                    return jsonify({"error": "Sin presets disponibles"}), 500
                _start_carla(presets[0])
            return jsonify({"ok": True, "preset": _current_preset})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

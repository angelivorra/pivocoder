"""Cliente TCP persistente para recibir eventos del servidor lgptclient.

Protocolo: líneas de texto UTF-8 terminadas en \\n.
  BPM,{ts_ms},{bpm}    → actualiza bpm y last_sync_ms
  SYNC,{ts_ms}         → actualiza last_sync_ms
  CONFIG,...           → ignorado
  START / END / NOTA   → ignorados
"""

from __future__ import annotations

import socket
import threading
import time


SERVER_HOST = "192.168.0.2"
SERVER_PORT = 8888
_BACKOFF_INITIAL = 2
_BACKOFF_MAX = 30


class BpmState:
    """Estado compartido thread-safe entre el cliente TCP y Flask."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.bpm: float | None = None
        self.connected: bool = False
        self.last_sync_ms: int | None = None

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "bpm": self.bpm,
                "connected": self.connected,
                "last_sync_ms": self.last_sync_ms,
            }


class _TCPClient:
    def __init__(self, state: BpmState) -> None:
        self._state = state

    def _handle_line(self, line: str) -> None:
        if not line:
            return
        parts = line.split(",")
        tag = parts[0]
        if tag == "BPM" and len(parts) >= 3:
            try:
                bpm = float(parts[2])
                ts = int(parts[1])
                with self._state._lock:
                    self._state.bpm = bpm
                    self._state.last_sync_ms = ts
                print(f"[tcp] BPM = {bpm}")
            except ValueError:
                pass
        elif tag == "SYNC" and len(parts) >= 2:
            try:
                ts = int(parts[1])
                with self._state._lock:
                    self._state.last_sync_ms = ts
            except ValueError:
                pass

    def _connect_and_read(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((SERVER_HOST, SERVER_PORT))
            sock.settimeout(60)
            with self._state._lock:
                self._state.connected = True
            print(f"[tcp] Conectado a {SERVER_HOST}:{SERVER_PORT}")
            buf = ""
            while True:
                chunk = sock.recv(1024).decode("utf-8", errors="replace")
                if not chunk:
                    break
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    self._handle_line(line.strip())

    def run(self) -> None:
        backoff = _BACKOFF_INITIAL
        while True:
            try:
                self._connect_and_read()
            except Exception as exc:
                print(f"[tcp] Desconectado: {exc}")
            with self._state._lock:
                self._state.connected = False
            time.sleep(backoff)
            backoff = min(backoff * 2, _BACKOFF_MAX)


_singleton: BpmState | None = None
_singleton_lock = threading.Lock()


def start_tcp_client() -> BpmState:
    """Lanza el cliente TCP en un hilo daemon y devuelve el estado compartido.

    Guarda de singleton para que gunicorn (master + worker) no abra dos conexiones.
    """
    global _singleton
    with _singleton_lock:
        if _singleton is not None:
            return _singleton
        state = BpmState()
        client = _TCPClient(state)
        thread = threading.Thread(target=client.run, daemon=True, name="tcp-bpm-client")
        thread.start()
        _singleton = state
        return state

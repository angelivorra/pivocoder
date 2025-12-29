#!/usr/bin/env python3
"""Supervisor para ejecutar Carla en modo headless y reiniciarlo si se cierra.

Este script está pensado para ejecutarse como servicio de usuario (systemd
--user). Mantiene un preset fijo cargado y reinicia Carla automáticamente en
caso de cierre inesperado (segfault, crash, etc.).
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# Configuración general -----------------------------------------------------

# Ruta del preset que se desea cargar siempre. Ajusta según tu entorno.
PRESET_PATH = Path("/home/patch/pivocoder/prod/script02.carxp")

# Comando base para arrancar Carla en modo headless con el preset elegido.
CARLA_CMD = [
    "carla",
    "-n",
    str(PRESET_PATH),
]

# Retraso inicial entre reinicios (segundos) y máximos para retroceso exponencial
RESTART_DELAY_SECONDS = 3
MAX_BACKOFF_SECONDS = 60

# Directorio para logs propios del supervisor.
LOG_DIR = Path.home() / ".local" / "share" / "carla-service"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "carla-service.log"

# ---------------------------------------------------------------------------

stop_requested = False
current_process: Optional[subprocess.Popen[bytes]] = None

def log(message: str) -> None:
    """Escribe un mensaje tanto por stdout como al archivo de log."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    print(formatted, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(formatted + "\n")

def ensure_preset_exists() -> None:
    if not PRESET_PATH.exists():
        log(f"ERROR: El preset '{PRESET_PATH}' no existe. Abortando.")
        sys.exit(1)

def launch_carla(stdout_target) -> subprocess.Popen:
    """Lanza Carla con el preset configurado y devuelve el proceso."""
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    log(f"Iniciando Carla con preset '{PRESET_PATH}'...")
    try:
        process = subprocess.Popen(
            CARLA_CMD,
            stdout=stdout_target,
            stderr=subprocess.STDOUT,
            env=env,
        )
    except FileNotFoundError:
        log("ERROR: No se encontró el ejecutable 'carla'. Asegúrate de que esté en el PATH.")
        raise
    except Exception as exc:  # pylint: disable=broad-except
        log(f"ERROR: Fallo al lanzar Carla: {exc}")
        raise
    log(f"Carla arrancada (PID {process.pid}).")
    return process

def terminate_process(process: subprocess.Popen) -> None:
    """Intenta terminar Carla cortésmente y, si no responde, la mata."""
    if process.poll() is not None:
        return
    log("Enviando SIGTERM a Carla...")
    process.terminate()
    try:
        process.wait(timeout=10)
        log("Carla terminó correctamente tras SIGTERM.")
    except subprocess.TimeoutExpired:
        log("Carla no respondió a SIGTERM. Enviando SIGKILL...")
        process.kill()
        process.wait(timeout=5)
        log("Carla finalizada con SIGKILL.")

def signal_handler(signum, _frame) -> None:
    global stop_requested
    log(f"Señal {signum} recibida. Preparando apagado del supervisor.")
    stop_requested = True
    if current_process and current_process.poll() is None:
        terminate_process(current_process)

def supervise() -> None:
    global current_process

    ensure_preset_exists()

    backoff = RESTART_DELAY_SECONDS
    while not stop_requested:
        # Abrimos el archivo de log de Carla en modo append y sin buffering para capturar su salida.
        with LOG_PATH.open("ab", buffering=0) as carla_log:
            try:
                current_process = launch_carla(carla_log)
            except Exception:
                log(f"Reintentando en {backoff} segundos...")
                if stop_requested:
                    break
                time.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
                continue

            start_time = time.monotonic()
            exit_code: Optional[int] = None

            # Esperamos a que termine pero comprobando periódicamente si se solicitó parada.
            while exit_code is None and not stop_requested:
                try:
                    exit_code = current_process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    continue

            # Si nos pidieron parar, terminamos el proceso si sigue vivo.
            if stop_requested:
                terminate_process(current_process)
                break

            run_seconds = time.monotonic() - start_time
            exit_code = exit_code if exit_code is not None else -1
            if exit_code == 0:
                log(f"Carla terminó con código 0 tras {run_seconds:.1f}s. Reiniciando en {RESTART_DELAY_SECONDS}s...")
            else:
                log(f"Carla se cerró inesperadamente (código {exit_code}) tras {run_seconds:.1f}s.\nReintentando en {backoff}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_SECONDS) if run_seconds < 30 else RESTART_DELAY_SECONDS

    log("Supervisor detenido. ¡Hasta la próxima!")


def main() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        supervise()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    finally:
        if current_process and current_process.poll() is None:
            terminate_process(current_process)


if __name__ == "__main__":
    main()

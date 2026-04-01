import os
import subprocess
import signal
import sys
import time

# Sample rate configurable via variable de entorno SAMPLE_RATE (44100 o 48000, por defecto 48000)
_sr_env = os.environ.get("SAMPLE_RATE", "48000")
SAMPLE_RATE = "44100" if _sr_env == "44100" else "48000"

JACKD_CMD = [
    "jackd",
    "-t", "2000",
    "-R",
    "-P", "95",
    "-d", "alsa",
    "-d", "hw:pisound",
    "-r", SAMPLE_RATE,
    "-p", "128",
    "-n", "2",
    "-X", "seq",
    "-s",
    "-S",
]

jackd_process = None

LED_ERROR = 200
LED_OK = 20


def flash_led(value):
    try:
        subprocess.run(
            f'sudo sh -c "echo {value} > /sys/kernel/pisound/led"',
            shell=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error setting LED: {e}")


def start_jackd():
    global jackd_process

    try:
        status = subprocess.run(
            ["jack_control", "status"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        if "running" in status.stdout.lower():
            print("jackd ya está corriendo. Deteniéndolo primero...")
            subprocess.run(["jack_control", "stop"], check=True)
            time.sleep(1)
    except (subprocess.SubprocessError, FileNotFoundError):
        subprocess.run(
            ["pkill", "-9", "jackd"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(1)

    print("Arrancando jackd...")
    jackd_process = subprocess.Popen(JACKD_CMD)

    time.sleep(1)
    if jackd_process.poll() is not None:
        print(f"Error: jackd falló al iniciar (código {jackd_process.returncode})")
        flash_led(LED_ERROR)
        return False

    flash_led(LED_OK)
    print(f"jackd arrancado con PID: {jackd_process.pid}")
    return True


def stop_processes():
    global jackd_process

    if jackd_process:
        print("Deteniendo jackd...")
        jackd_process.terminate()
        try:
            jackd_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            jackd_process.kill()
        jackd_process = None
        print("jackd detenido.")


def handle_signal(signum, frame):
    print(f"Señal {signum} recibida, deteniendo procesos...")
    stop_processes()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    if not start_jackd():
        print("No se pudo arrancar jackd. Saliendo...")
        sys.exit(1)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle_signal(signal.SIGINT, None)

import os
import sys
import time
import signal
import threading
import mido
import jack
import wave
import numpy as np
import subprocess

LED_ERROR = 200
LED_OK = 20

carla_process = None
jackd_process = None
alsa_in_process = None
recording_process = None  # Add this line to track recording process
current_preset = 0

# Configuración de JACKD
JACKD_CMD = [
    "jackd",
    "-t", "2000",
    "-R",
    "-P", "95",
    "-d", "alsa",
    "-d", "hw:pisound",
    "-r", "48000",
    "-p", "128",
    "-n", "2",
    "-X", "seq",
    "-s",
    "-S"
]

def flash_led(value):
    try:
        cmd = f'sudo sh -c "echo {value} > /sys/kernel/pisound/led"'
        os.system(cmd)
        print(f"LED value set to: {value}")
    except Exception as e:
        print(f"Error setting LED value: {e}")

def start_jackd():
    global jackd_process
    # Parar jackd si ya está corriendo
    try:
        status = subprocess.run(["jack_control", "status"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
        if "running" in status.stdout.lower():
            print("jackd is already running. Stopping it first...")
            subprocess.run(["jack_control", "stop"], check=True)
            time.sleep(1)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Stopping any existing jackd processes...")
        subprocess.run(["pkill", "-9", "jackd"],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        time.sleep(1)
    print("Arrancando jackd...")
    jackd_process = subprocess.Popen(JACKD_CMD)
    time.sleep(1)
    if jackd_process.poll() is not None:
        print(f"Error: jackd falló al iniciar con código {jackd_process.returncode}")
        flash_led(LED_ERROR)
        return False
    print(f"jackd arrancado con PID: {jackd_process.pid}")
    return True

def stop_jackd():
    global jackd_process
    if jackd_process:
        print("Deteniendo jackd...")
        jackd_process.terminate()
        try:
            jackd_process.wait(timeout=5)
        except Exception:
            jackd_process.kill()
        print("jackd detenido.")
        jackd_process = None

def get_usb_audio_device():
    try:
        output = subprocess.check_output(["arecord", "-l"], text=True)
    except subprocess.CalledProcessError:
        print("Error al ejecutar arecord -l; usando dispositivo por defecto hw:3,0")
        return "hw:3,0"
    for line in output.splitlines():
        if "USB Composite Device" in line:
            import re
            match = re.search(r'card (\d+):', line)
            if match:
                card_id = match.group(1)
                return f"hw:{card_id},0"
    print("No se encontró 'USB Composite Device'; usando dispositivo por defecto hw:3,0")
    return "hw:3,0"

def start_alsa_in():
    global alsa_in_process
    device = get_usb_audio_device()
    print(f"Arrancando alsa_in con dispositivo {device}...")
    alsa_in_cmd = [
        "alsa_in",
        "-d", device,
        "-j", "usb_mic",
        "-r", "48000",
        "-p", "128",
        "-c", "1"
    ]
    with open("/dev/null", "w") as devnull:
        alsa_in_process = subprocess.Popen(
            alsa_in_cmd,
            stdout=devnull,
            stderr=devnull
        )
    print(f"alsa_in arrancado con PID: {alsa_in_process.pid}")

def stop_alsa_in():
    global alsa_in_process
    if alsa_in_process:
        print("Deteniendo alsa_in...")
        alsa_in_process.terminate()
        try:
            alsa_in_process.wait(timeout=5)
        except Exception:
            alsa_in_process.kill()
        print("alsa_in detenido.")
        alsa_in_process = None

def start_carla(program_number):
    global carla_process, current_preset
    preset_path = f"/home/patch/pivocoder/program{program_number}.carxp"
    print(f"Arrancando Carla con preset: {preset_path}...")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    carla_cmd = ["carla", "-n", preset_path]
    carla_process = subprocess.Popen(carla_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)
    if carla_process.poll() is not None:
        print(f"Error: Carla no se inicializó correctamente. Código: {carla_process.returncode}")
        flash_led(LED_ERROR)
        return False
    flash_led(LED_OK)
    print(f"Carla arrancada con PID: {carla_process.pid}")
    return True

def stop_carla():
    global carla_process
    if carla_process:
        print("Deteniendo Carla...")
        carla_process.terminate()
        try:
            carla_process.wait(timeout=5)
        except Exception:
            carla_process.kill()
        print("Carla detenida.")
        carla_process = None

def stop_recording():
    global recording_process
    if recording_process:
        print("Deteniendo captura de audio...")
        recording_process.terminate()
        try:
            recording_process.wait(timeout=5)
        except Exception:
            recording_process.kill()
        print("Captura de audio detenida.")
        recording_process = None

def stop_processes():
    stop_carla()
    stop_alsa_in()
    stop_jackd()
    stop_recording()

def handle_signal(signum, frame):
    print(f"Señal {signum} recibida, deteniendo procesos...")
    stop_processes()
    sys.exit(0 if signum == signal.SIGTERM else 1)

def get_pisound_midi_port():
    available_ports = mido.get_input_names()
    for port in available_ports:
        if 'pisound' in port.lower():
            return port
    return available_ports[0] if available_ports else None

def change_carla_preset(program_number):
    global current_preset
    if program_number != current_preset:
        print(f"Cambiando al preset {program_number}...")
        stop_carla()
        current_preset = program_number
        if current_preset > 0:
            start_carla(current_preset)

def monitor_midi():
    try:
        port_name = get_pisound_midi_port()
        if port_name is None:
            print("No se pudo encontrar un puerto MIDI válido.")
            return
        print(f"Abriendo puerto MIDI: {port_name}")
        with mido.open_input(port_name) as port:
            for msg in port:
                if msg.type == 'program_change':
                    print(f"Mensaje MIDI recibido: {msg.program}")
                    change_carla_preset(msg.program)
    except Exception as e:
        print("Error al monitorizar MIDI:", e)
        flash_led(LED_ERROR)
        stop_processes()
        sys.exit(1)

def start_recording():
    """Función para capturar la salida de audio de jack y guardarla en test.wav."""
    global recording_process
    print("Iniciando captura de audio en test.wav...")
    # Se asume que jack_capture está instalado y configurado
    recording_process = subprocess.Popen(["jack_capture", "-f", "test.wav"])
    print(f"Captura iniciada con PID: {recording_process.pid}")

def main():
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    if not start_jackd():
        print("No se pudo arrancar jackd. Saliendo...")
        flash_led(LED_ERROR)
        sys.exit(1)
    
    start_alsa_in()
    time.sleep(1)

    client = jack.Client("pivocoder")
    print("Conectado a JACK.")

    midi_thread = threading.Thread(target=monitor_midi, daemon=True)
    midi_thread.start()

    flash_led(LED_OK)

    if len(sys.argv) > 1 and sys.argv[1].lower() == "graba":
        start_recording()

    # Mostrar latencia real cada segundo
    periods = 2  # Debe coincidir con tu -n en JACKD_CMD
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle_signal(signal.SIGINT, None)

if __name__ == "__main__":
    main()
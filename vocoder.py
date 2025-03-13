import re
import subprocess
import signal
import sys
import time
from rtmidi.midiutil import open_midiinput

# Comando para arrancar jackd
JACKD_CMD = [
    "jackd",
    "-t", "2000",
    "-R",
    "-P", "95",
    "-d", "alsa",
    "-d", "hw:pisound", #"hw:4,0", 
    "-r", "48000",
    "-p", "128",
    "-n", "2",
    "-X", "seq",
    "-s",
    "-S"
]

# Variables para almacenar los procesos
jackd_process = None
alsa_in_process = None
carla_process = None
recording_process = None
current_preset = 1

def monitor_midi(port_name):
    """Monitorea las señales MIDI y cambia el preset de Carla si se detecta un mensaje específico."""

def get_usb_audio_device():
    """Parsea la salida de 'arecord -l' para obtener el dispositivo USB Audio Device."""
    try:
        output = subprocess.check_output(["arecord", "-l"], text=True)
    except subprocess.CalledProcessError:
        print("Error al ejecutar arecord -l; usando dispositivo por defecto hw:3,0")
        return "hw:3,0"
    for line in output.splitlines():
        if "USB Audio Device" in line:
            match = re.search(r'card (\d+):', line)
            if match:
                card_id = match.group(1)
                return f"hw:{card_id},0"
    print("No se encontró 'USB Audio Device'; usando dispositivo por defecto hw:3,0")
    return "hw:3,0"

def start_jackd():
    """Función para arrancar jackd."""
    global jackd_process
    subprocess.run(["pkill", "jackd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "alsa_in"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Arrancando jackd...")
    jackd_process = subprocess.Popen(JACKD_CMD)
    print(f"jackd arrancado con PID: {jackd_process.pid}")

def start_alsa_in():
    """Función para arrancar alsa_in."""
    global alsa_in_process
    device = get_usb_audio_device()
    print(f"Arrancando alsa_in con dispositivo {device}...")
    alsa_in_cmd = [
        "alsa_in",
        "-d", device,  # Dispositivo de entrada (tarjeta USB)
        "-j", "usb_mic",  # Nombre de los puertos en JACK
        "-r", "48000",    # Tasa de muestreo (debe coincidir con jackd)
        "-p", "128",      # Tamaño del buffer (debe coincidir con jackd)
        "-c", "1"         # Número de canales (1 para mono, 2 para estéreo)
    ]
    # Redirigir stdout y stderr a /dev/null para silenciar los mensajes
    with open("/dev/null", "w") as devnull:
        alsa_in_process = subprocess.Popen(
            alsa_in_cmd,
            stdout=devnull,  # Redirigir stdout
            stderr=devnull   # Redirigir stderr
        )
    print(f"alsa_in arrancado con PID: {alsa_in_process.pid}")


def start_carla():
    """Función para arrancar Carla en modo headless con un preset específico."""
    global carla_process, current_preset
    preset_path = "/home/patch/pivocoder/prueba_completa_02.carxp"
    print(f"Arrancando Carla con preset: {preset_path}...")
    carla_cmd = [
        "/usr/bin/carla",
        "--no-ui",  # Modo headless (sin interfaz gráfica)
        "--load-preset", 
        preset_path  # Ruta al preset de Carla
    ]
    carla_process = subprocess.Popen(carla_cmd)
    print(f"Carla arrancada con PID: {carla_process.pid}")

def connect_ports():
    """Función para conectar los puertos de audio y MIDI."""
    print("Conectando puertos de audio y MIDI...")
    
    # Conectar el micrófono a la entrada del vocoder en Carla
    subprocess.run(["jack_connect", "usb_mic:capture_1", "Carla:input_1"])
    print("Conectado usb_mic:capture_1 a Carla:input_1")

    # Conectar la salida del vocoder en Carla a los altavoces
    subprocess.run(["jack_connect", "Carla:output_1", "system:playback_1"])
    subprocess.run(["jack_connect", "Carla:output_2", "system:playback_2"])
    print("Conectado Carla:output_1 a system:playback_1")
    print("Conectado Carla:output_2 a system:playback_2")

    # Conectar el puerto MIDI a la entrada MIDI del vocoder en Carla
    subprocess.run(["jack_connect", "pisound:midi/capture_1", "Carla:midi_in"])
    print("Conectado pisound:midi/capture_1 a Carla:midi_in")

def start_recording():
    """Función para capturar la salida de audio de jack y guardarla en test.wav."""
    global recording_process
    print("Iniciando captura de audio en test.wav...")
    # Se asume que jack_capture está instalado y configurado
    recording_process = subprocess.Popen(["jack_capture", "-f", "test.wav"])
    print(f"Captura iniciada con PID: {recording_process.pid}")

def stop_processes():
    """Función para detener jackd, alsa_in, Carla y la captura de audio."""
    global jackd_process, alsa_in_process, carla_process, recording_process
    # Detener Carla
    if carla_process:
        print("Deteniendo Carla...")
        carla_process.terminate()
        try:
            carla_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Carla no respondió a SIGTERM, enviando SIGKILL...")
            carla_process.kill()
        print("Carla detenida.")
        carla_process = None

    # Detener alsa_in
    if alsa_in_process:
        print("Deteniendo alsa_in...")
        alsa_in_process.terminate()
        try:
            alsa_in_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("alsa_in no respondió a SIGTERM, enviando SIGKILL...")
            alsa_in_process.kill()
        print("alsa_in detenido.")
        alsa_in_process = None

    # Detener jackd
    if jackd_process:
        print("Deteniendo jackd...")
        jackd_process.terminate()
        try:
            jackd_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("jackd no respondió a SIGTERM, enviando SIGKILL...")
            jackd_process.kill()
        print("jackd detenido.")
        jackd_process = None

    # Detener captura de audio
    if recording_process:
        print("Deteniendo captura de audio...")
        recording_process.terminate()
        try:
            recording_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("La captura no respondió a SIGTERM, enviando SIGKILL...")
            recording_process.kill()
        print("Captura de audio detenida.")
        recording_process = None

class MidiInputHandler(object):
    def __init__(self, port):
        self.port = port
        self._wallclock = time.time()

    def __call__(self, event, data=None):
        message, deltatime = event
        self._wallclock += deltatime
        print("[%s] @%0.6f %r" % (self.port, self._wallclock, message))


def handle_signal(signum, frame):
    """Manejador de señales para detener los procesos al recibir SIGTERM o SIGINT."""
    print(f"Señal {signum} recibida, deteniendo procesos...")
    stop_processes()
    sys.exit(0)

if __name__ == "__main__":
    # Configurar manejadores de señales
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Arrancar jackd
    start_jackd()

    # Esperar un momento para que jackd se estabilice
    time.sleep(2)

    # Arrancar alsa_in
    start_alsa_in()

    # Arrancar Carla
    
    #start_carla()
    

    # Iniciar la captura de audio a test.wav solo si se pasó el argumento "graba"
    if len(sys.argv) > 1 and sys.argv[1].lower() == "graba":
        start_recording()

    # Mantener el script en ejecución
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle_signal(signal.SIGINT, None)
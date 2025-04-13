import os
import re
import subprocess
import signal
import sys
import time
import threading
import mido

# Comando para arrancar jackd
JACKD_CMD = [
    "jackd",
    "-t", "2000",
    "-R",
    "-P", "95",
    "-d", "alsa",
    "-d", "hw:pisound", #"hw:4,0", 
    "-r", "44100",
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
current_preset = 0


LED_ERROR = 200
LED_OK = 20

def change_carla_preset(program_number):
    """Cambia el preset de Carla según el número de programa recibido."""
    global current_preset, carla_process
    
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
    
    if program_number != current_preset:
        print(f"Cambiando al preset {program_number}...")
        # Aquí puedes agregar la lógica para cambiar el preset en Carla
        current_preset = program_number
        if current_preset > 0:
            start_carla(current_preset)

def get_usb_audio_device():
    """Parsea la salida de 'arecord -l' para obtener el dispositivo USB Composite Device."""
    try:
        output = subprocess.check_output(["arecord", "-l"], text=True)
    except subprocess.CalledProcessError:
        print("Error al ejecutar arecord -l; usando dispositivo por defecto hw:3,0")
        return "hw:3,0"
    for line in output.splitlines():
        if "USB Composite Device" in line:
            match = re.search(r'card (\d+):', line)
            if match:
                card_id = match.group(1)
                return f"hw:{card_id},0"
    print("No se encontró 'USB Composite Device'; usando dispositivo por defecto hw:3,0")
    return "hw:3,0"

def start_jackd():
    """Función para arrancar jackd."""
    global jackd_process
    
    # Check if jackd is already running
    try:
        # Use jack_control to check status instead of killing blindly
        status = subprocess.run(["jack_control", "status"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        if "running" in status.stdout.lower():
            print("jackd is already running. Stopping it first...")
            subprocess.run(["jack_control", "stop"], check=True)
            time.sleep(1)  # Give it time to shut down properly
    except (subprocess.SubprocessError, FileNotFoundError):
        # If jack_control isn't available, fall back to pkill
        print("Stopping any existing jackd processes...")
        subprocess.run(["pkill", "-9", "jackd"], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
        time.sleep(1)  # Give it time to shut down properly
    
    print("Arrancando jackd...")
    jackd_process = subprocess.Popen(JACKD_CMD)
    
    # Check if jackd started successfully
    time.sleep(1)
    if jackd_process.poll() is not None:  # If process has already terminated
        print(f"Error: jackd falló al iniciar con código {jackd_process.returncode}")
        flash_led(LED_ERROR)
        return False
    
    print(f"jackd arrancado con PID: {jackd_process.pid}")
    return True

def start_alsa_in():
    """Función para arrancar alsa_in."""
    global alsa_in_process
    device = get_usb_audio_device()
    print(f"Arrancando alsa_in con dispositivo {device}...")
    alsa_in_cmd = [
        "alsa_in",
        "-d", device,  # Dispositivo de entrada (tarjeta USB)
        "-j", "usb_mic",  # Nombre de los puertos en JACK
        "-r", "44100",    # Tasa de muestreo (debe coincidir con jackd)
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


def flash_led(value):
    """
    Controls the Pisound LED by writing an integer value to the LED control file.
    
    Args:
        value (int): The value to write to the LED control file.
                    Different values trigger different LED behaviors.
    """
    try:
        cmd = f'sudo sh -c "echo {value} > /sys/kernel/pisound/led"'
        subprocess.run(cmd, shell=True, check=True)
        print(f"LED value set to: {value}")
    except subprocess.CalledProcessError as e:
        print(f"Error setting LED value: {e}")

def start_carla(program_number):
    """Función para arrancar Carla en modo headless con un preset específico."""
    global carla_process, current_preset
    preset_path = f"/home/patch/pivocoder/program{program_number}.carxp"
    print(f"Arrancando Carla con preset: {preset_path}...")

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    carla_cmd = ["carla", "-n", preset_path]
    carla_process = subprocess.Popen(carla_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Esperar hasta 10 segundos para que Carla se inicialice
    timeout = 10
    start_time = time.time()
    while carla_process.poll() is None and (time.time() - start_time) < timeout:
        time.sleep(0.1)

    if carla_process.poll() is not None:
        print(f"Error: Carla no se inicializó correctamente. Código: {carla_process.returncode}")
        print(f"Salida de Carla: {carla_process.stdout.read().decode()}")
        print(f"Errores de Carla: {carla_process.stderr.read().decode()}")
        flash_led(LED_ERROR)
        return False

    flash_led(LED_OK)
    print(f"Carla arrancada con PID: {carla_process.pid}")
    return True

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

def handle_signal(signum, frame):
    """Manejador de señales para detener los procesos al recibir SIGTERM o SIGINT."""
    print(f"Señal {signum} recibida, deteniendo procesos...")
    stop_processes()
    sys.exit(0 if signum == signal.SIGTERM else 1)


def get_pisound_midi_port():
    """Find the available pisound MIDI port."""
    available_ports = mido.get_input_names()
    print(f"Available MIDI input ports: {available_ports}")
    
    # Try to find a port with 'pisound' in the name
    for port in available_ports:
        if 'pisound' in port.lower():
            print(f"Found pisound MIDI port: {port}")
            return port
            
    # If no port found with 'pisound'
    if available_ports:
        print(f"No pisound MIDI port found. Using first available port: {available_ports[0]}")
        return available_ports[0]
    else:
        print("No MIDI ports available")
        return None


def monitor_midi():
    """Monitorea el puerto MIDI y imprime mensajes que no sean de clock."""
    try:
        port_name = get_pisound_midi_port()
        if port_name is None:
            print("No se pudo encontrar un puerto MIDI válido.")
            return

        print(f"Intentando abrir el puerto MIDI: {port_name}")
        with mido.open_input(port_name) as port:
            print(f"Puerto MIDI abierto: {port}")
            for msg in port:
                if msg.type == 'program_change':
                    print(f"Mensaje MIDI recibido: {msg.program}")
                    change_carla_preset(msg.program)
    except Exception as e:
        print("Error al monitorizar MIDI:", e)
        flash_led(LED_ERROR)
        stop_processes()
        sys.exit(1)

if __name__ == "__main__":
    # Configurar manejadores de señales
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Arrancar jackd
    if not start_jackd():
        print("No se pudo arrancar jackd. Saliendo...")
        flash_led(LED_ERROR)
        sys.exit(1)

    # Esperar un momento para que jackd se estabilice
    time.sleep(2)

    # Arrancar alsa_in
    start_alsa_in()

    time.sleep(1)

    # # Iniciar monitorización de MIDI en un hilo
    # midi_thread = threading.Thread(target=monitor_midi, daemon=True)
    # midi_thread.start()  
    
    flash_led(LED_OK)

    #pisound:pisound MIDI PS-1HPT6W6 32:0

    # Iniciar la captura de audio a test.wav solo si se pasó el argumento "graba"
    if len(sys.argv) > 1 and sys.argv[1].lower() == "graba":
        start_recording()

    # Mantener el script en ejecución
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle_signal(signal.SIGINT, None)
import os
import re
import subprocess
import signal
import sys
import time
import threading
import mido
import socket # Added for TCP server
import queue # Added for message queue (optional, but good for decoupling)

# Comando para arrancar jackd
JACKD_CMD = [
    "jackd",
    "-t", "2000",    # Tiempo de espera para mensajes (ms)
    "-R",            # Modo realtime (importante)
    "-P", "95",      # Prioridad alta (95 es casi máximo)
    "-d", "alsa",
    "-d", "hw:pisound",  # ¿Usas una Pisound? Asegúrate de que es la mejor opción vs "hw:1"
    "-r", "48000",   # Sample rate (puedes probar 48000 si la interfaz lo soporta)
    "-p", "128",     # Buffer pequeño (latencia ~5-10 ms)
    "-n", "2",       # Número de periodos (2 es óptimo para baja latencia)
    "-X", "seq",     # Soporte MIDI ALSA
    "-s",            # Silenciar mensajes no críticos
    "-S"             # Evita que otros dispositivos usen ALSA
]

# Variables para almacenar los procesos
jackd_process = None
alsa_in_process = None
carla_process = None
recording_process = None
current_preset = 0

# TCP Server related globals
tcp_server_socket = None
client_handler_threads = []
server_running = True # Flag to control server loop
tcp_server_started_event = threading.Event() # To signal server startup
# Port for the TCP server, you can change this
TCP_PORT = 12345
TCP_HOST = '0.0.0.0' # Listen on all available interfaces


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

def start_carla():
    """Función para arrancar Carla en modo headless con un preset específico."""
    global carla_process, current_preset
    preset_path = f"/home/patch/pivocoder/buenos/z_nnn.carxp"
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

def handle_client_connection(client_socket, client_address):
    """Handles an individual client connection."""
    global server_running
    print(f"TCP: Accepted connection from {client_address}")
    try:
        while server_running:
            # Set a timeout for recv to periodically check server_running flag
            client_socket.settimeout(1.0)
            try:
                data = client_socket.recv(1024)
            except socket.timeout:
                continue # No data received, loop back to check server_running
            
            if not data:
                print(f"TCP: Client {client_address} disconnected gracefully.")
                break
            
            message = data.decode().strip()
            if not message: # Skip empty messages after strip
                continue

            print(f"TCP: Received from {client_address}: '{message}'")

    except ConnectionResetError:
        print(f"TCP: Client {client_address} reset the connection.")
    except socket.error as e:
        if server_running: # Avoid error message if server is shutting down
             print(f"TCP: Socket error with client {client_address}: {e}")
    except Exception as e:
        print(f"TCP: Unexpected error with client {client_address}: {e}")
    finally:
        print(f"TCP: Closing connection with {client_address}")
        client_socket.close()
        # Remove thread from list if it's being tracked for joining (optional)
        # For daemon threads, this is less critical.

def start_tcp_server(host=TCP_HOST, port=TCP_PORT):
    """Starts the TCP server to listen for MIDI program changes."""
    global tcp_server_socket, client_handler_threads, server_running, tcp_server_started_event
    
    server_running = True # Ensure flag is true at start
    tcp_server_started_event.clear()

    tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        tcp_server_socket.bind((host, port))
        tcp_server_socket.listen(5) # Allow up to 5 queued connections
        print(f"TCP server listening on {host}:{port}")
        tcp_server_started_event.set() # Signal that bind and listen were successful
    except OSError as e:
        print(f"TCP: Error binding/listening on {host}:{port}: {e}")
        flash_led(LED_ERROR)
        if tcp_server_socket:
            tcp_server_socket.close()
            tcp_server_socket = None
        return # Exit thread if bind fails

    # Set a timeout for accept() so the loop can be interrupted by server_running flag
    tcp_server_socket.settimeout(1.0) 

    try:
        while server_running:
            try:
                client_socket, client_address = tcp_server_socket.accept()
                thread = threading.Thread(target=handle_client_connection, args=(client_socket, client_address))
                thread.daemon = True # Allows main program to exit even if threads are running
                thread.start()
                client_handler_threads.append(thread) # Keep track if needed for explicit join later
            except socket.timeout:
                continue # Timeout allows checking server_running flag
            except OSError as e:
                if server_running: # Only print error if we weren't expecting to stop
                    print(f"TCP: Error accepting connection: {e}")
                break # Exit loop if socket error (e.g. closed by stop_processes)
    except Exception as e:
        if server_running:
            print(f"TCP: Server loop error: {e}")
    finally:
        print("TCP: Server accept loop exiting.")
        # Close any remaining client sockets (though client_handler_threads should do this)
        # This part is tricky as client_handler_threads might still be running.
        # Daemon threads and individual client socket closures are primary cleanup.
        if tcp_server_socket:
            tcp_server_socket.close()
            tcp_server_socket = None
        print("TCP: Server socket closed.")


def stop_processes():
    """Función para detener jackd, alsa_in, Carla, la captura de audio y el servidor TCP."""
    global jackd_process, alsa_in_process, carla_process, recording_process
    global tcp_server_socket, server_running, client_handler_threads

    print("Stopping processes...")

    # Stop TCP Server
    print("TCP: Signaling server and client handlers to stop...")
    server_running = False # Signal all server-related threads to stop

    if tcp_server_socket:
        print("TCP: Closing server socket...")
        # Closing the server socket will cause accept() to raise an error,
        # helping the server_thread to exit its loop if it's blocked there.
        tcp_server_socket.close() 
        tcp_server_socket = None 
        # Note: client sockets are closed by their respective handler threads.

    # Optionally, wait for client handler threads to finish
    # This is complex if they are blocked on recv().
    # Daemon threads will exit when the main program exits.
    # The server_running flag and socket timeouts in handle_client_connection help.
    # for thread in client_handler_threads:
    #    if thread.is_alive():
    #        thread.join(timeout=1.0) # Wait briefly

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

    print("All processes signaled to stop.")


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

    # Arrancar servidor TCP
    print("Main: Starting TCP server thread...")
    tcp_server_thread = threading.Thread(target=start_tcp_server, args=(TCP_HOST, TCP_PORT), daemon=True)
    tcp_server_thread.start()

    # Esperar a que el servidor TCP confirme el arranque (bind exitoso)
    if not tcp_server_started_event.wait(timeout=5): # Espera hasta 5 segundos
        print("Main: TCP server failed to start (bind error or timeout). Saliendo...")
        flash_led(LED_ERROR)
        stop_processes() # Limpiar lo que ya se haya arrancado
        sys.exit(1)
    else:
        print(f"Main: TCP server started successfully on port {TCP_PORT}.")

    if "graba" in [arg.lower() for arg in sys.argv]:
        start_recording()

    if "carla" in [arg.lower() for arg in sys.argv]:
        start_carla()

    # Mantener el script en ejecución
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle_signal(signal.SIGINT, None)
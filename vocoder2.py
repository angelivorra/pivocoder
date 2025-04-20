import os
import re
import subprocess
import signal
import sys
import time
import threading
import mido
import jack
import numpy as np
from collections import deque

# Configuración JACK
JACK_CONFIG = {
    "client_name": "pivocoder",
    "samplerate": 44100,
    "blocksize": 128,
    "periods": 2,
    "device": "hw:pisound",
    "midi_in": "pisound:pisound MIDI",
    "max_delay_ms": 15  # Umbral de latencia para alertas
}

# Estados del sistema
class SystemState:
    def __init__(self):
        self.current_preset = 0
        self.jack_client = None
        self.alsa_process = None
        self.carla_process = None
        self.recording_process = None
        self.latency_history = deque(maxlen=10)
        self.xrun_count = 0

# Instancia global
state = SystemState()

# LED Control
LED_ERROR = 200
LED_OK = 20

def flash_led(value):
    """Controla el LED de Pisound"""
    try:
        with open("/sys/kernel/pisound/led", "w") as f:
            f.write(str(value))
    except IOError as e:
        print(f"Error controlando LED: {e}")

# JACK Client Setup
def setup_jack_client():
    """Configura el cliente JACK con manejo de latencia"""
    try:
        client = jack.Client(JACK_CONFIG["client_name"])
        client.set_process_callback(process_callback)
        client.set_shutdown_callback(shutdown_callback)
        client.set_xrun_callback(xrun_callback)
        
        # Configuración de puertos
        client.inports.register("audio_in")
        client.outports.register("audio_out")
        client.midi_inports.register("midi_in")
        
        return client
    except jack.JackError as e:
        print(f"Error inicializando JACK: {e}")
        flash_led(LED_ERROR)
        return None

def process_callback(frames):
    """Callback de procesamiento JACK para monitoreo de latencia"""
    # Medición de latencia en tiempo real
    latency = state.jack_client.get_latency_range(jack.LatencyType.Output)[1]
    latency_ms = (latency / JACK_CONFIG["samplerate"]) * 1000
    state.latency_history.append(latency_ms)
    
    # Manejo de MIDI
    for midi_in in state.jack_client.midi_inports:
        for msg in midi_in.incoming_midi_events():
            if msg[0] == 0xC0:  # Program Change
                program = msg[1] + 1  # Los presets comienzan en 1
                change_carla_preset(program)

def xrun_callback(delay):
    """Callback para XRUNs"""
    state.xrun_count += 1
    print(f"XRUN detectado (total: {state.xrun_count})")
    if state.xrun_count > 5:
        adjust_jack_settings()

def shutdown_callback(status, reason):
    """Manejo de cierre de JACK"""
    print(f"JACK se cerró: {reason}")
    flash_led(LED_ERROR)
    cleanup()
    sys.exit(1)

def adjust_jack_settings():
    """Ajusta dinámicamente la configuración JACK"""
    current_buffer = JACK_CONFIG["blocksize"]
    if state.xrun_count > 5 and current_buffer < 512:
        new_buffer = min(current_buffer * 2, 512)
        print(f"Ajustando buffer a {new_buffer} por XRUNs frecuentes")
        restart_jack(new_buffer)

def restart_jack(new_buffer):
    """Reinicia JACK con nueva configuración"""
    print(f"Reiniciando JACK con buffer={new_buffer}")
    cleanup_processes()
    JACK_CONFIG["blocksize"] = new_buffer
    initialize_system()

# Carla Control
def change_carla_preset(program_number):
    """Cambia presets en Carla"""
    if program_number == state.current_preset:
        return

    print(f"Cambiando al preset {program_number}")
    if state.carla_process:
        state.carla_process.terminate()
        state.carla_process.wait(timeout=2)
    
    preset_path = f"/home/patch/pivocoder/program{program_number}.carxp"
    if os.path.exists(preset_path):
        state.carla_process = subprocess.Popen(
            ["carla", "-n", preset_path],
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"}
        )
        state.current_preset = program_number
        flash_led(LED_OK)
    else:
        print(f"Error: Preset {preset_path} no existe")
        flash_led(LED_ERROR)

# System Initialization
def initialize_system():
    """Inicializa todos los componentes"""
    try:
        # JACK Client
        state.jack_client = setup_jack_client()
        if not state.jack_client:
            raise RuntimeError("No se pudo inicializar JACK")
        
        # Alsa In (si es necesario)
        state.alsa_process = subprocess.Popen(
            ["alsa_in", "-d", JACK_CONFIG["device"], "-j", "usb_mic"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        
        # Conectar puertos
        time.sleep(1)  # Esperar inicialización
        state.jack_client.activate()
        connect_ports()
        
        flash_led(LED_OK)
        print("Sistema inicializado correctamente")
        return True
    except Exception as e:
        print(f"Error inicializando sistema: {e}")
        flash_led(LED_ERROR)
        cleanup()
        return False

def connect_ports():
    """Conecta los puertos JACK automáticamente"""
    # Conexión ALSA -> JACK
    try:
        state.jack_client.connect("usb_mic:capture_1", f"{JACK_CONFIG['client_name']}:audio_in")
        state.jack_client.connect(f"{JACK_CONFIG['client_name']}:audio_out", "system:playback_1")
    except jack.JackError as e:
        print(f"Error conectando puertos: {e}")

# Cleanup
def cleanup():
    """Limpieza ordenada del sistema"""
    if state.jack_client:
        state.jack_client.deactivate()
        state.jack_client.close()
    
    cleanup_processes()

def cleanup_processes():
    """Detiene todos los procesos"""
    for proc in [state.alsa_process, state.carla_process, state.recording_process]:
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

# Signal Handling
def handle_signal(signum, frame):
    """Maneja señales de terminación"""
    print(f"\nRecibida señal {signum}, limpiando...")
    cleanup()
    sys.exit(0)

# Main Execution
if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    if not initialize_system():
        sys.exit(1)
    
    try:
        # Monitoreo de latencia en segundo plano
        def latency_monitor():
            while True:
                if state.latency_history:
                    avg_latency = np.mean(state.latency_history)
                    if avg_latency > JACK_CONFIG["max_delay_ms"]:
                        print(f"¡Alerta! Latencia alta: {avg_latency:.2f}ms")
                time.sleep(5)
        
        threading.Thread(target=latency_monitor, daemon=True).start()
        
        # Bucle principal
        while True:
            time.sleep(1)
            if state.xrun_count > 10:
                print("Demasiados XRUNs, reiniciando...")
                restart_jack(JACK_CONFIG["blocksize"] * 2)
                state.xrun_count = 0
                
    except KeyboardInterrupt:
        handle_signal(signal.SIGINT, None)
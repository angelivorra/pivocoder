#!/usr/bin/env python3
import subprocess
import re
import time
import sys

# Configuración (ajusta estos nombres si cambian)
DEVICE_NAMES = {
    "mic": "USB Composite Device",
    "midi": "pisound",
    "output": "pisound"
}

def get_audio_device_id(device_type, name):
    try:
        cmd = "arecord -l" if device_type == "mic" else "aplay -l"
        output = subprocess.check_output(cmd, shell=True, text=True)
        
        for line in output.split('\n'):
            if name in line:
                match = re.search(r'card (\d+).*device (\d+)', line)
                if match:
                    return f"hw:{match.group(1)},{match.group(2)}"
        raise ValueError(f"Dispositivo no encontrado: {name}")
    except Exception as e:
        print(f"Error detectando {device_type}: {e}")
        sys.exit(1)

def get_midi_port(name):
    try:
        output = subprocess.check_output("aconnect -l", shell=True, text=True)
        
        for line in output.split('\n'):
            if name in line:
                match = re.search(r'client (\d+):', line)
                if match:
                    return f"{match.group(1)}:0"
        raise ValueError(f"MIDI no encontrado: {name}")
    except Exception as e:
        print(f"Error detectando MIDI: {e}")
        sys.exit(1)

def start_vocoder(mic_dev, midi_port, out_dev):
    cmd = [
        "/home/patch/vocoder/build/src/vocoder",
        "--input", mic_dev,
        "--midi", midi_port,
        "--output", out_dev,
        "--bandas", "16",
        "--carrier", "440"
    ]
    print("Ejecutando:", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar vocoder: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=== Auto-Vocoder (Detector de Dispositivos) ===")
    
    # Detección automática
    mic = get_audio_device_id("mic", DEVICE_NAMES["mic"])
    midi = get_midi_port(DEVICE_NAMES["midi"])
    output = get_audio_device_id("output", DEVICE_NAMES["output"])
    
    print(f"\nDispositivos detectados:")
    print(f"Micrófono: {mic}")
    print(f"MIDI: {midi}")
    print(f"Salida: {output}\n")
    
    start_vocoder(mic, midi, output)
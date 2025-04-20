import os
import sys
import numpy as np
import soundfile as sf
from scipy.io import wavfile


def detect_speech_intervals(audio, sample_rate, silence_threshold=-40, min_silence_duration=0.5, min_speech_duration=0.3):
    """
    Detecta intervalos de habla en una señal de audio.
    
    Args:
        audio: Señal de audio (numpy array)
        sample_rate: Tasa de muestreo
        silence_threshold: Umbral en dB para considerar silencio
        min_silence_duration: Duración mínima de silencio para separar frases (segundos)
        min_speech_duration: Duración mínima de un segmento de habla (segundos)
        
    Returns:
        Lista de tuplas (start, end) en muestras
    """
    # Convertir a mono si es estereo
    if len(audio.shape) > 1:
        audio = np.mean(audio, axis=1)
    
    # Calcular energía en ventanas cortas
    window_size = int(0.02 * sample_rate)  # 20 ms
    hop_size = window_size // 2
    energy = []
    
    for i in range(0, len(audio) - window_size, hop_size):
        window = audio[i:i + window_size]
        window_energy = 10 * np.log10(np.mean(window**2) + 1e-10)
        energy.append(window_energy)
    
    energy = np.array(energy)
    
    # Detectar silencios
    is_silence = energy < silence_threshold
    silence_samples = np.where(is_silence)[0]
    
    # Encontrar cambios entre silencio y habla
    changes = np.diff(is_silence.astype(int))
    speech_starts = np.where(changes == -1)[0]  # Silencio -> Habla
    speech_ends = np.where(changes == 1)[0]     # Habla -> Silencio
    
    # Asegurarse de que empezamos con habla si el audio no empieza con silencio
    if len(speech_ends) > 0 and (len(speech_starts) == 0 or speech_ends[0] < speech_starts[0]):
        speech_starts = np.insert(speech_starts, 0, 0)
    
    # Asegurarse de que terminamos con habla si el audio no termina con silencio
    if len(speech_starts) > 0 and (len(speech_ends) == 0 or speech_starts[-1] > speech_ends[-1]):
        speech_ends = np.append(speech_ends, len(is_silence) - 1)
    
    # Convertir ventanas a muestras y aplicar duraciones mínimas
    min_silence_frames = int(min_silence_duration * sample_rate / hop_size)
    min_speech_frames = int(min_speech_duration * sample_rate / hop_size)
    
    intervals = []
    for start, end in zip(speech_starts, speech_ends):
        duration_frames = end - start
        if duration_frames >= min_speech_frames:
            start_sample = start * hop_size
            end_sample = end * hop_size + window_size
            intervals.append((start_sample, end_sample))
    
    # Combinar intervalos cercanos separados por silencios cortos
    if len(intervals) > 1:
        merged_intervals = [intervals[0]]
        for current in intervals[1:]:
            last = merged_intervals[-1]
            silence_duration = (current[0] - last[1]) / sample_rate
            if silence_duration < min_silence_duration:
                # Combinar intervalos
                merged_intervals[-1] = (last[0], current[1])
            else:
                merged_intervals.append(current)
        intervals = merged_intervals
    
    return intervals


def split_audio(input_wav, output_dir):
    """
    Divide un archivo WAV en segmentos de habla.
    
    Args:
        input_wav: Ruta al archivo WAV de entrada
        output_dir: Directorio de salida para los segmentos
    """
    # Crear directorio de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Leer archivo WAV
    sample_rate, audio = wavfile.read(input_wav)
    
    # Detectar intervalos de habla
    intervals = detect_speech_intervals(audio, sample_rate)
    
    # Guardar cada segmento
    base_name = os.path.splitext(os.path.basename(input_wav))[0]
    
    for i, (start, end) in enumerate(intervals, 1):
        segment = audio[start:end]
        
        # Convertir a mono si es estereo
        if len(segment.shape) > 1:
            segment = np.mean(segment, axis=1)
        
        # Crear nombre de archivo
        output_path = os.path.join(output_dir, f"{base_name}_{i:03d}.wav")
        
        # Guardar segmento
        sf.write(output_path, segment, sample_rate, subtype='PCM_16')
    
    print(f"Procesado {input_wav}: {len(intervals)} segmentos guardados en {output_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python split_audio.py archivo.wav")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_directory = "out"
    
    if not os.path.isfile(input_file):
        print(f"Error: El archivo {input_file} no existe.")
        sys.exit(1)
    
    split_audio(input_file, output_directory)
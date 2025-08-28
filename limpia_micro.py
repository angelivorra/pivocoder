
import os
import shutil
import subprocess
import librosa
import soundfile as sf
import webrtcvad
import numpy as np


def split_audio(
    input_file,
    output_dir,
    vad_aggressiveness=3,
    trim_db=30,
    gain_factor=1.6,
    softclip=True,
    softclip_drive=2.5,
):
    """
    Divide un archivo de audio en segmentos basados en la detección de silencio.
    Elimina el silencio al principio de cada segmento.

    Args:
        input_file (str): Ruta al archivo de audio de entrada.
        output_dir (str): Ruta al directorio de salida para los segmentos.
        vad_aggressiveness (int): Nivel de agresividad del VAD (0-3).
        trim_db (float): Nivel de recorte en dB para eliminar silencio al principio de cada sample.
    """
    try:
        audio, sr = librosa.load(input_file, sr=None)
    except Exception as e:
        print(f"Error al cargar {input_file}: {e}")
        return

    if len(audio.shape) > 1:
        audio = librosa.to_mono(audio)

    audio_int16 = np.int16(audio * 32768)
    vad = webrtcvad.Vad(vad_aggressiveness)

    frame_duration = 30  # ms
    frame_samples = int(sr * frame_duration / 1000)
    frame_bytes = frame_samples * 2  # 16 bits

    def frame_generator(audio_int16, frame_samples):
        for start in range(0, len(audio_int16), frame_samples):
            yield audio_int16[start:start + frame_samples]

    frames = list(frame_generator(audio_int16, frame_samples))

    segments = []
    segment_start = None
    for i, frame in enumerate(frames):
        if len(frame) < frame_samples:
            continue
        is_speech = vad.is_speech(frame.tobytes(), sr)
        if is_speech and segment_start is None:
            segment_start = i * frame_duration / 1000
        elif not is_speech and segment_start is not None:
            segment_end = i * frame_duration / 1000
            if segment_end - segment_start > 0.1:  # descartar segmentos muy cortos
                segments.append((segment_start, segment_end))
            segment_start = None
    # Si termina en voz
    if segment_start is not None:
        segment_end = len(frames) * frame_duration / 1000
        if segment_end - segment_start > 0.1:
            segments.append((segment_start, segment_end))

    for i, (start, end) in enumerate(segments):
        segment = audio[int(start * sr):int(end * sr)]
        # Eliminar silencio al principio y final del segmento
        segment, _ = librosa.effects.trim(segment, top_db=trim_db)
        if len(segment) == 0:
            continue
        # Normalizar el sample a -1.0 ... 1.0 (peak normalization)
        peak = np.max(np.abs(segment))
        if peak > 0:
            segment = segment / peak
        # Aumentar volumen (post-normalización)
        if gain_factor and gain_factor != 1.0:
            segment = segment * float(gain_factor)
        # Soft clip/tanh para más loudness sin distorsión dura
        if softclip:
            drive = max(0.1, float(softclip_drive))
            segment = np.tanh(segment * drive) / np.tanh(drive)
        # Normalización final para asegurar peak <= 0.999
        peak2 = np.max(np.abs(segment))
        if peak2 > 0:
            segment = (segment / peak2) * 0.999
        output_file = os.path.join(output_dir, f"{i+1:02d}.wav")
        sf.write(output_file, segment, sr)
        print(f"Guardado WAV: {output_file}")

        # Intentar generar MP3 paralelo usando ffmpeg (libmp3lame)
        ffmpeg = shutil.which('ffmpeg')
        if ffmpeg:
            mp3_file = os.path.splitext(output_file)[0] + '.mp3'
            cmd = [ffmpeg, '-y', '-i', output_file, '-codec:a', 'libmp3lame', '-b:a', '192k', mp3_file]
            try:
                subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"Guardado MP3: {mp3_file}")
            except subprocess.CalledProcessError:
                print(f"Error al convertir a MP3: {output_file}")
        else:
            print("ffmpeg no encontrado; omitiendo conversión a MP3.")


def main():
    """
    Función principal para buscar archivos de audio y procesarlos.
    Borra el contenido de la carpeta rsamples antes de empezar.
    """
    home_dir = os.path.expanduser("~")
    rsamples_dir = os.path.join(home_dir, "rsamples")

    # Borrar carpeta rsamples si existe
    if os.path.exists(rsamples_dir):
        shutil.rmtree(rsamples_dir)
    os.makedirs(rsamples_dir, exist_ok=True)

    # Parámetros configurables
    vad_aggressiveness = 3  # 0-3, 3 es más agresivo
    trim_db = 30  # dB para recorte de silencio
    gain_factor = 1.6  # Más volumen (aprox +4 dB)
    softclip = True
    softclip_drive = 2.5  # Aumentar para más saturación

    for filename in os.listdir(home_dir):
        if filename.startswith("jack_capture_") and filename.endswith(".wav"):
            input_file = os.path.join(home_dir, filename)
            output_dir = os.path.join(rsamples_dir, os.path.splitext(filename)[0])
            os.makedirs(output_dir, exist_ok=True)
            print(f"Procesando: {input_file}")
            split_audio(
                input_file,
                output_dir,
                vad_aggressiveness=vad_aggressiveness,
                trim_db=trim_db,
                gain_factor=gain_factor,
                softclip=softclip,
                softclip_drive=softclip_drive,
            )

if __name__ == "__main__":
    main()
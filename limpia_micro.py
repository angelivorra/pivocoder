
import os
import shutil
import subprocess
import librosa
import soundfile as sf
import webrtcvad
import numpy as np
import argparse


def split_audio(
    input_file,
    output_dir,
    vad_aggressiveness=3,
    trim_db=30,
    gain_factor=1.6,
    softclip=True,
    softclip_drive=2.5,
    mp3=False,
    stereo=False,
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
        # Cargar sin forzar a mono para conservar canales originales
        audio, sr = librosa.load(input_file, sr=None, mono=False)
    except Exception as e:
        print(f"Error al cargar {input_file}: {e}")
        return
    # audio puede ser (n,) o (canales, n)
    if audio.ndim == 1:
        audio_mono = audio
    else:
        # Crear mezcla mono solo para VAD / segmentación
        audio_mono = librosa.to_mono(audio)

    audio_mono_int16 = np.int16(audio_mono * 32768)
    vad = webrtcvad.Vad(vad_aggressiveness)

    frame_duration = 30  # ms
    frame_samples = int(sr * frame_duration / 1000)
    frame_bytes = frame_samples * 2  # 16 bits

    def frame_generator(audio_int16, frame_samples):
        for start in range(0, len(audio_int16), frame_samples):
            yield audio_int16[start:start + frame_samples]

    frames = list(frame_generator(audio_mono_int16, frame_samples))

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
        start_idx = int(start * sr)
        end_idx = int(end * sr)

        # Extraer segmento original (puede ser multi-canal)
        if audio.ndim == 1:
            seg_full = audio[start_idx:end_idx]
        else:
            seg_full = audio[:, start_idx:end_idx]  # (canales, n)

        # Usar mezcla mono para trimming y obtener índices
        seg_mono = audio_mono[start_idx:end_idx]
        seg_mono_trim, trim_idx = librosa.effects.trim(seg_mono, top_db=trim_db)
        trim_start_rel, trim_end_rel = trim_idx
        if seg_mono_trim.size == 0:
            continue
        if audio.ndim == 1:
            seg_full = seg_full[trim_start_rel:trim_end_rel]
        else:
            seg_full = seg_full[:, trim_start_rel:trim_end_rel]

        if seg_full.size == 0:
            continue

        # Normalización peak común a todos los canales
        peak = np.max(np.abs(seg_full))
        if peak > 0:
            seg_full = seg_full / peak
        # Ganancia
        if gain_factor and gain_factor != 1.0:
            seg_full = seg_full * float(gain_factor)
        # Soft clip
        if softclip:
            drive = max(0.1, float(softclip_drive))
            seg_full = np.tanh(seg_full * drive) / np.tanh(drive)
        # Normalización final
        peak2 = np.max(np.abs(seg_full))
        if peak2 > 0:
            seg_full = (seg_full / peak2) * 0.999

        # Preparar forma (n_frames, n_channels) para escribir si es multi-canal
        # Preparar datos mono y estéreo
        if audio.ndim == 1:
            mono_data = seg_full  # ya mono (n,)
            stereo_data = np.stack([mono_data, mono_data], axis=1)  # duplicar
        else:
            # seg_full shape (canales, n)
            mono_data = np.mean(seg_full, axis=0)
            # Limitar a 2 canales para estéreo: si hay más, tomar los dos primeros
            if seg_full.shape[0] >= 2:
                stereo_data = seg_full[:2, :].T  # (n,2)
            else:
                stereo_data = np.stack([mono_data, mono_data], axis=1)

        # Guardar mono WAV
        mono_file = os.path.join(output_dir, f"{i+1:02d}.wav")
        sf.write(mono_file, mono_data, sr)
        print(f"Guardado WAV mono: {mono_file}")

        # Guardar estéreo WAV
        stereo_file = os.path.join(output_dir, f"{i+1:02d}.stereo.wav")
        sf.write(stereo_file, stereo_data, sr)
        print(f"Guardado WAV estéreo: {stereo_file}")

        # MP3 desde la versión mono o estéreo según flags
        if mp3 and stereo:
            ffmpeg = shutil.which('ffmpeg')
            if ffmpeg:
                mp3_data = stereo_data if stereo else mono_data
                mp3_file = os.path.join(output_dir, f"{i+1:02d}.mp3")
                cmd = [ffmpeg, '-y', '-i', 'pipe:0', '-f', 'wav', '-codec:a', 'libmp3lame', '-b:a', '192k', mp3_file]
                # Since we have numpy array, need to write to pipe
                # Actually, better to write temp wav and convert
                temp_wav = os.path.join(output_dir, f"temp_{i+1:02d}.wav")
                sf.write(temp_wav, mp3_data, sr)
                cmd = [ffmpeg, '-y', '-i', temp_wav, '-codec:a', 'libmp3lame', '-b:a', '192k', mp3_file]
                try:
                    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"Guardado MP3: {mp3_file}")
                    os.remove(temp_wav)  # clean up
                except subprocess.CalledProcessError:
                    print(f"Error al convertir a MP3: {temp_wav}")
                    if os.path.exists(temp_wav):
                        os.remove(temp_wav)
            else:
                print("ffmpeg no encontrado; omitiendo conversión a MP3.")


def main():
    """
    Función principal para buscar archivos de audio y procesarlos.
    Borra el contenido de la carpeta rsamples antes de empezar.
    """
    parser = argparse.ArgumentParser(description="Procesar archivos de audio y guardar segmentos.")
    parser.add_argument('--mp3', action='store_true', help='Guardar archivos MP3')
    parser.add_argument('--stereo', action='store_true', help='Usar versión estéreo para MP3')
    args = parser.parse_args()

    home_dir = os.path.expanduser("~")
    rsamples_dir = os.path.join(home_dir, "rsamples")

    # Borrar carpeta rsamples si existe
    if os.path.exists(rsamples_dir):
        shutil.rmtree(rsamples_dir)
    os.makedirs(rsamples_dir, exist_ok=True)

    # Parámetros configurables
    vad_aggressiveness = 3  # 0-3, 3 es más agresivo
    trim_db = 30  # dB para recorte de silencio
    gain_factor = 2.0  # Más volumen (aprox +4 dB)
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
                mp3=args.mp3,
                stereo=args.stereo,
            )

if __name__ == "__main__":
    main()
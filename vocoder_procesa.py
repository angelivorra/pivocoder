import os
import argparse
import numpy as np
import soundfile as sf
import librosa

def split_wav_by_silence(input_file, output_dir="out/", min_silence_len=0.5, silence_thresh=-40, min_duration=0.5):
    """
    Split a WAV file into separate files based on detected silence.
    
    Parameters:
    - input_file: Path to the input WAV file
    - output_dir: Directory to save output files
    - min_silence_len: Minimum silence length in seconds
    - silence_thresh: Threshold (in dB) below which is considered silence
    - min_duration: Minimum duration for a segment to be saved
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    
    print(f"Loading audio file: {input_file}")
    # Load the audio file
    y, sr = librosa.load(input_file, sr=None, mono=True)
    
    # Convert silence threshold from dB to amplitude
    silence_thresh = librosa.db_to_amplitude(silence_thresh)
    
    # Find non-silent segments
    print("Detecting non-silent segments...")
    intervals = librosa.effects.split(y, top_db=-silence_thresh, frame_length=512, hop_length=128)
    
    print(f"Found {len(intervals)} segments")
    
    # Process each segment
    for i, (start, end) in enumerate(intervals):
        # Convert frame indices to seconds
        start_time = start / sr
        end_time = end / sr
        duration = end_time - start_time
        
        # Skip segments that are too short
        if duration < min_duration:
            continue
        
        # Extract the segment
        segment = y[start:end]
        
        # Create output filename
        filename = os.path.splitext(os.path.basename(input_file))[0]
        output_path = os.path.join(output_dir, f"{filename}_segment_{i+1}.wav")
        
        # Save the segment
        sf.write(output_path, segment, sr)
        print(f"Saved segment {i+1} ({duration:.2f}s) to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split WAV file by silence")
    parser.add_argument("input", help="Input WAV file")
    parser.add_argument("-o", "--output-dir", default="out/", help="Output directory (default: out/)")
    parser.add_argument("-s", "--silence-threshold", type=float, default=-40, 
                        help="Silence threshold in dB (default: -40)")
    parser.add_argument("-m", "--min-silence", type=float, default=0.5, 
                        help="Minimum silence length in seconds (default: 0.5)")
    parser.add_argument("-d", "--min-duration", type=float, default=0.5,
                        help="Minimum duration for a segment in seconds (default: 0.5)")
    
    args = parser.parse_args()
    
    split_wav_by_silence(
        args.input,
        args.output_dir,
        args.min_silence,
        args.silence_threshold,
        args.min_duration
    )
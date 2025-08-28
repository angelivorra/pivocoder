#!/usr/bin/env python3
"""Simple converter: input.wav -> output.mp3 using ffmpeg (libmp3lame).
Usage: convert_to_mp3.py INPUT_WAV [OUTPUT_MP3] [BITRATE]
"""
import os
import shutil
import subprocess
import sys


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def main(argv):
    if len(argv) < 2:
        eprint("Usage: convert_to_mp3.py INPUT_WAV [OUTPUT_MP3] [BITRATE]")
        return 2

    inp = argv[1]
    if not os.path.exists(inp):
        eprint(f"Input file not found: {inp}")
        return 2

    out = argv[2] if len(argv) >= 3 else os.path.splitext(inp)[0] + '.mp3'
    bitrate = argv[3] if len(argv) >= 4 else '192k'

    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        eprint('ffmpeg not found in PATH. Please install ffmpeg and try again.')
        return 3

    cmd = [ffmpeg, '-y', '-i', inp, '-codec:a', 'libmp3lame', '-b:a', bitrate, out]
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as exc:
        eprint('ffmpeg failed with exit code', exc.returncode)
        return exc.returncode
    except Exception as exc:
        eprint('Unexpected error while running ffmpeg:', exc)
        return 4

    print(f'Wrote: {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))

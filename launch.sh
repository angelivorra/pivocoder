#!/bin/bash

# Set necessary environment variables
export JACK_NO_AUDIO_RESERVATION=1
export DISPLAY=:0
export XAUTHORITY=/home/patch/.Xauthority
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus

# Add the path to the virtual environment's Python executable
export PATH=/home/patch/venv/bin:$PATH

# Log environment variables
echo "Environment Variables:"
printenv

# Log available MIDI ports
echo "Available MIDI Ports:"
aconnect -l

# Wait for the MIDI device to be ready
echo "Waiting for MIDI device to initialize..."
sleep 5

# Launch the vocoder script
exec /home/patch/venv/bin/python3 /home/patch/pivocoder/vocoder.py
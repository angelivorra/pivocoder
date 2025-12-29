## Ver estado

'''
systemctl --user status sonido
'''

'''
systemctl --user status carla
'''

## Parar servicios

'''
systemctl --user stop sonido
'''

'''
systemctl --user stop carla
'''

## Grabar audio

'''
jack_capture -f wav
'''


## Comandos

python3 pivocoder/vocoder.py

python3 pivocoder/vocoder.py graba

mpv --ao=jack --loop=inf mi_grabacion.wav


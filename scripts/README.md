# scripts/

Utilidades de arranque para pivocoder.

## carla-vnc.sh — Editar el patch con interfaz, sin monitor

La Pi corre Carla **headless** (servicio `carla`). Cuando necesitas la interfaz
gráfica para tocar el patch, este script levanta un servidor VNC **efímero** y
abre Carla dentro. Al cerrar Carla (o cortar la conexión) **apaga y limpia
todo**: no deja ningún VNC corriendo.

Qué hace, en orden:

1. Si el servicio headless `carla` está activo, lo **para** (para no doblar
   audio/MIDI con dos instancias) y recuerda reanudarlo.
2. Arranca `Xvnc` en el display `:1`, escuchando **solo en `127.0.0.1:5901`**
   (sin autenticación, porque solo es accesible por el túnel SSH).
3. Lanza `openbox` (para mover/redimensionar ventanas) y Carla con la GUI,
   cargando por defecto `prod/template01.carxp`.
4. Al cerrar Carla: mata Xvnc/openbox y, si paró el servicio, lo **reanuda**.

### Uso

Desde VS Code (Remote-SSH en la Pi): tarea **«Carla · GUI en VNC (editar
prod/template01)»**. O en terminal:

```bash
scripts/carla-vnc.sh                      # carga prod/template01.carxp
scripts/carla-vnc.sh produccion/fase1.carxp   # otro preset
```

### Conectarse desde el portátil

El VNC solo escucha en localhost de la Pi, así que se accede por túnel:

```bash
ssh -L 5901:localhost:5901 patch@192.168.0.10
```

(o reenvía el puerto **5901** desde el panel **«Ports»** de VS Code Remote-SSH).
Luego abre tu visor VNC en **`localhost:5901`**.

### Variables opcionales

| Variable        | Por defecto | Qué hace                 |
|-----------------|-------------|--------------------------|
| `VNC_DISPLAY`   | `1`         | número de display (puerto = 5900+N) |
| `VNC_GEOMETRY`  | `1366x768`  | resolución               |
| `VNC_DEPTH`     | `24`        | profundidad de color     |

### Si algo se queda colgado

Tarea **«Carla · Limpiar sesión VNC (forzar)»**, o:

```bash
pkill -f 'Xvnc.*:1'; pkill -f 'Xvnc -rootHelper'; pkill vncserverui; pkill openbox
```

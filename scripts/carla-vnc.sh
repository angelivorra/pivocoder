#!/usr/bin/env bash
#
# carla-vnc.sh — Lanza Carla CON interfaz gráfica en un servidor VNC EFÍMERO,
# para editar el patch sin monitor en la Pi. Al cerrar Carla (o cortar la
# conexión SSH) se apaga y limpia TODO: no deja ningún servidor VNC corriendo.
#
# Uso:
#   scripts/carla-vnc.sh [archivo.carxp]
#   (por defecto carga el mismo preset que el servicio headless)
#
# Conexión desde tu portátil (el VNC solo escucha en 127.0.0.1 de la Pi):
#   1) Túnel:  ssh -L 5901:localhost:5901 patch@192.168.0.10
#      (o reenvía el puerto 5901 desde el panel «Ports» de VS Code Remote-SSH)
#   2) Abre tu visor VNC en:  localhost:5901
#
set -u

# --- Configuración (sobreescribible por entorno) ---------------------------
DISP="${VNC_DISPLAY:-1}"
GEOMETRY="${VNC_GEOMETRY:-1366x768}"
DEPTH="${VNC_DEPTH:-24}"
PORT=$((5900 + DISP))
CARXP="${1:-}"
LOG="/tmp/carla-vnc.log"
ME="$(id -u)"
RESTART_SERVICE=0
_CLEANED=0

cleanup() {
  [ "$_CLEANED" = "1" ] && return
  _CLEANED=1
  echo
  echo "[carla-vnc] cerrando…"
  kill "${CARLA_PID:-0}" 2>/dev/null
  kill "${OB_PID:-0}"    2>/dev/null
  kill "${XVNC_PID:-0}"  2>/dev/null
  pkill -u "$ME" -f "Xvnc.*:$DISP"     2>/dev/null
  pkill -u "$ME" -f "Xvnc -rootHelper" 2>/dev/null
  pkill -u "$ME" vncserverui           2>/dev/null
  # Si paramos el servicio headless al empezar, lo devolvemos a su estado.
  if [ "$RESTART_SERVICE" = "1" ]; then
    echo "[carla-vnc] reanudando servicio headless 'carla'…"
    systemctl --user start carla 2>/dev/null
  fi
  echo "[carla-vnc] display :$DISP y VNC apagados. Limpio."
}
trap cleanup EXIT INT TERM HUP

# --- Comprobaciones --------------------------------------------------------
command -v Xvnc  >/dev/null || { echo "ERROR: Xvnc no está instalado"; exit 1; }
command -v carla >/dev/null || { echo "ERROR: carla no está en PATH"; exit 1; }
[ -z "$CARXP" ] || [ -f "$CARXP" ] || echo "AVISO: no existe '$CARXP' — Carla abrirá vacío."

# --- Evitar choque con el servicio headless --------------------------------
# Dos instancias de Carla doblarían audio/MIDI. Si el servicio está activo lo
# paramos mientras editas y lo reanudamos al cerrar.
if systemctl --user is-active --quiet carla; then
  echo "[carla-vnc] parando servicio headless 'carla' mientras editas…"
  systemctl --user stop carla
  RESTART_SERVICE=1
fi

# --- Limpiar restos de una sesión previa en este display -------------------
pkill -u "$ME" -f "Xvnc.*:$DISP" 2>/dev/null && sleep 1

# --- Arrancar display virtual (solo localhost, sin auth) -------------------
export DISPLAY=":$DISP"
Xvnc ":$DISP" -geometry "$GEOMETRY" -depth "$DEPTH" \
     SecurityTypes=None Localhost=1 rfbport="$PORT" >"$LOG" 2>&1 &
XVNC_PID=$!
sleep 2
if ! kill -0 "$XVNC_PID" 2>/dev/null; then
  echo "ERROR: Xvnc no arrancó. Log:"; tail -n 20 "$LOG"; exit 1
fi

# --- Gestor de ventanas (mover/redimensionar) ------------------------------
if command -v openbox >/dev/null; then openbox 2>/dev/null & OB_PID=$!; sleep 1; fi

cat <<INFO
================================================================
 Carla GUI en VNC efímero  ·  display :$DISP
 Escucha SOLO en 127.0.0.1:$PORT  (usa túnel SSH)

   1) En tu portátil:  ssh -L $PORT:localhost:$PORT patch@192.168.0.10
      (o reenvía el puerto $PORT desde el panel «Ports» de VS Code)
   2) Visor VNC ->  localhost:$PORT

 Preset: ${CARXP:-(ninguno — Carla abrirá vacío)}
 Al CERRAR Carla se apaga y limpia todo solo.
================================================================
INFO

# --- Lanzar Carla con GUI sobre el display virtual -------------------------
# Xvnc no tiene GLX, DRI3, XRandr ni XInput2. Estas variables evitan que Qt y
# Mesa los busquen, eliminando todos los warnings y el segfault al cerrar.
export LIBGL_ALWAYS_SOFTWARE=1
export MESA_LOADER_DRIVER_OVERRIDE=swrast   # salta DRI3; va directo a software
export QT_OPENGL=software
export QT_XCB_NO_XI2=1                     # desactiva XInput2
export QT_XCB_NO_MITSHM=1
export QT_LOGGING_RULES="qt.qpa.xcb=false;qt.qpa.gl=false"
carla ${CARXP:+"$CARXP"} & CARLA_PID=$!
wait "$CARLA_PID"

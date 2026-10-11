#!/bin/sh
# /opt/mineos/start-minecraft.sh - Script de lançamento do Minecraft com Fabric Loader e Waylandcraft
set -e

USER_HOME="$HOME"
MINECRAFT_DIR="$USER_HOME/.minecraft"
LOG_DIR="$MINECRAFT_DIR/logs"
mkdir -p "$LOG_DIR"

echo "========================================="
echo "MineOS: Inicializando Minecraft Compositor"
echo "Horário: $(date)"
echo "Display Wayland do Cage: ${WAYLAND_DISPLAY:-wayland-0}"
echo "========================================="

# 1. Configurações de aceleração gráfica e Wayland Nativo
export __GL_THREADED_OPTIMIZATIONS=0
export RUST_BACKTRACE=1
export MESA_GL_VERSION_OVERRIDE=4.5
export MESA_GLSL_VERSION_OVERRIDE=450

# Força todos os toolkits e GLFW para Wayland puro (elimina dependência de X11/Xlib)
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export XDG_SESSION_TYPE="wayland"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export GLFW_PLATFORM="wayland"
export GDK_BACKEND="wayland"
export QT_QPA_PLATFORM="wayland"
export SDL_VIDEODRIVER="wayland"
export CLUTTER_BACKEND="wayland"
export XKB_CONFIG_ROOT="/usr/share/X11/xkb"
export WLR_SCENE_DISABLE_DIRECT_SCANOUT=1
export WLR_DRM_NO_ATOMIC=1
export WLR_NO_HARDWARE_CURSORS=1

# Caminho das bibliotecas nativas de Waylandcraft e GLFW
export LD_LIBRARY_PATH="/opt/mineos/native-libs:${LD_LIBRARY_PATH:-}"

# Executa diagnóstico Wayland / GLFW
if [ -x /usr/bin/check_wayland ]; then
    /usr/bin/check_wayland || true
fi

# 2. Runtime Java: Utiliza exclusivamente o Adoptium Temurin 25 (Software Livre)
JAVA_BIN=""
if [ -x "/opt/temurin-jre/bin/java" ]; then
    JAVA_BIN="/opt/temurin-jre/bin/java"
    echo "[INFO] Usando Adoptium Temurin 25 JRE (Software Livre): $JAVA_BIN"
elif [ -x "/usr/bin/java" ]; then
    JAVA_BIN="/usr/bin/java"
    echo "[INFO] Usando Java do sistema (/usr/bin/java): $JAVA_BIN"
elif command -v java >/dev/null 2>&1; then
    JAVA_BIN=$(which java)
    echo "[INFO] Usando Java encontrado no PATH: $JAVA_BIN"
else
    echo "[ERRO] Nenhum runtime Java livre (Adoptium Temurin 25) encontrado em /opt/temurin-jre!"
fi

if [ -n "$JAVA_BIN" ]; then
    echo "[INFO] Versão do Java detectada:"
    "$JAVA_BIN" -version 2>&1 | head -n 3
fi

# 3. Resolução do Classpath do Fabric Loader
CP_FILE="$MINECRAFT_DIR/versions/fabric-loader-0.19.5-26.1.2/classpath.txt"
CLASSPATH=""
if [ -f "$CP_FILE" ]; then
    echo "[INFO] Carregando classpath estruturado de $CP_FILE..."
    CLASSPATH=$(cat "$CP_FILE")
else
    FABRIC_JAR=$(find "$MINECRAFT_DIR/versions" -name "*fabric*.jar" 2>/dev/null | head -n 1 || true)
    if [ -n "$FABRIC_JAR" ]; then
        echo "[INFO] Classpath fallback usando $FABRIC_JAR..."
        CLASSPATH="$FABRIC_JAR:$MINECRAFT_DIR/libraries/*"
    fi
fi

# 4. Dimensionamento e otimização de memória e GC para a JVM
MEM_TOTAL_MB=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 2048)
if [ "$MEM_TOTAL_MB" -lt 2400 ]; then
    JVM_MAX="1024M"
    JVM_INIT="512M"
elif [ "$MEM_TOTAL_MB" -lt 3500 ]; then
    JVM_MAX="1200M"
    JVM_INIT="768M"
else
    JVM_MAX="2048M"
    JVM_INIT="1024M"
fi
echo "[INFO] Alocação JVM: Memória Total VM=${MEM_TOTAL_MB}MB | Max Heap=${JVM_MAX} | Init Heap=${JVM_INIT}"

# Ativa JDWP apenas se explicitamente solicitado via variável de ambiente
JDWP_ARG=""
if [ "${ENABLE_JDWP:-false}" = "true" ]; then
    echo "[INFO] JDWP Debugger habilitado na porta :5005"
    JDWP_ARG="-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005"
fi

# 5. Execução do Minecraft com flags G1GC otimizadas para baixa latência
if [ -n "$JAVA_BIN" ] && [ -n "$CLASSPATH" ]; then
    echo "[INFO] Lançando JVM do Minecraft com Fabric Loader (G1GC otimizado)..."
    exec "$JAVA_BIN" \
        -Xmx"$JVM_MAX" -Xms"$JVM_INIT" \
        -XX:+UnlockExperimentalVMOptions \
        -XX:+UseG1GC \
        -XX:MaxGCPauseMillis=30 \
        -XX:+ParallelRefProcEnabled \
        -DMC_DEBUG_ENABLED=true \
        -DMC_DEBUG_PREFER_WAYLAND=true \
        -DMC_DEBUG_PRINT_PROPERTIES=true \
        -Dorg.lwjgl.system.SharedLibraryExtractPath="/tmp" \
        -Djava.library.path="/opt/mineos/native-libs" \
        $JDWP_ARG \
        -cp "$CLASSPATH" \
        net.fabricmc.loader.impl.launch.knot.KnotClient \
        --gameDir "$MINECRAFT_DIR" \
        --assetsDir "$MINECRAFT_DIR/assets"
else
    echo "[AVISO] Minecraft ou Fabric Loader não localizados na partição persistente."
    echo "[INFO] Subindo terminal/diagnóstico de espera do MineOS..."
    
    if command -v foot >/dev/null 2>&1; then
        exec foot
    elif command -v alacritty >/dev/null 2>&1; then
        exec alacritty
    else
        while true; do
            echo "MineOS aguardando dados do Minecraft em $MINECRAFT_DIR..."
            sleep 5
        done
    fi
fi

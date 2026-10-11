#!/bin/sh
# board/mineos/post-build.sh - Ajustes finais no rootfs alvo do MineOS
TARGET_DIR="$1"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$(dirname "$0")")")")"

echo "[MineOS Post-Build] Ajustando permissões dos scripts de boot..."
chmod +x "$TARGET_DIR/etc/init.d/S99mineos" 2>/dev/null || true
chmod +x "$TARGET_DIR/opt/mineos/start-minecraft.sh" 2>/dev/null || true

# 1. Copia libwaylandcraft.so se compilado ou pré-existente
NATIVE_SO="$PROJECT_ROOT/waylandcraft-2.1.0/native/target/debug/libwaylandcraft.so"
if [ ! -f "$NATIVE_SO" ]; then
    NATIVE_SO="$PROJECT_ROOT/waylandcraft-2.1.0/native-libs/libwaylandcraft-linux-gnu-x86_64.so"
fi
if [ -f "$NATIVE_SO" ]; then
    echo "[MineOS Post-Build] Instalando libwaylandcraft.so ($NATIVE_SO) no rootfs..."
    mkdir -p "$TARGET_DIR/opt/mineos/native-libs"
    cp "$NATIVE_SO" "$TARGET_DIR/opt/mineos/native-libs/libwaylandcraft.so"
fi

# 2. Instala Adoptium Temurin 25 JRE no rootfs se o tarball estiver presente
JRE_TAR=$(ls "$PROJECT_ROOT"/OpenJDK25U-jre_*.tar.gz 2>/dev/null | head -n 1)
if [ -n "$JRE_TAR" ] && [ -f "$JRE_TAR" ]; then
    NEED_EXTRACT=0
    if [ ! -x "$TARGET_DIR/opt/temurin-jre/bin/java" ]; then
        NEED_EXTRACT=1
    elif ! grep -q "Temurin-25" "$TARGET_DIR/opt/temurin-jre/release" 2>/dev/null; then
        NEED_EXTRACT=1
    fi

    if [ "$NEED_EXTRACT" -eq 1 ]; then
        echo "[MineOS Post-Build] Extraindo Adoptium Temurin 25 JRE ($JRE_TAR) para /opt/temurin-jre..."
        rm -rf "$TARGET_DIR/opt/temurin-jre"
        mkdir -p "$TARGET_DIR/opt/temurin-jre"
        tar -xzf "$JRE_TAR" -C "$TARGET_DIR/opt/temurin-jre" --strip-components=1
    fi
    ln -sf /opt/temurin-jre/bin/java "$TARGET_DIR/usr/bin/java"
fi

echo "[MineOS Post-Build] Concluído com sucesso."

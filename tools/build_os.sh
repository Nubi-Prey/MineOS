#!/usr/bin/env bash
# tools/build_os.sh - Orquestrador de compilação da imagem do MineOS com Buildroot
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILDROOT_DIR="$PROJECT_ROOT/buildroot"
EXTERNAL_DIR="$PROJECT_ROOT/buildroot-external"
BUILDROOT_VERSION="2025.02" # Versão LTS moderna

echo "========================================="
echo "MineOS: Orquestrador de Construção do SO"
echo "Buildroot Alvo: $BUILDROOT_VERSION"
echo "Árvore Externa: $EXTERNAL_DIR"
echo "========================================="

# 1. Garante presença das dependências externas (ex: Adoptium Temurin 25 JRE)
if [ -x "$SCRIPT_DIR/download_deps.sh" ]; then
    "$SCRIPT_DIR/download_deps.sh"
fi

# 2. Garante presença do código-fonte do Buildroot
if [ ! -d "$BUILDROOT_DIR" ]; then
    echo "[INFO] Baixando Buildroot $BUILDROOT_VERSION LTS..."
    mkdir -p "$BUILDROOT_DIR"
    curl -fsSL "https://buildroot.org/downloads/buildroot-${BUILDROOT_VERSION}.tar.gz" | tar -xz -C "$PROJECT_ROOT"
    mv "$PROJECT_ROOT/buildroot-${BUILDROOT_VERSION}"/* "$BUILDROOT_DIR/"
    rm -rf "$PROJECT_ROOT/buildroot-${BUILDROOT_VERSION}"
fi

ACTION="${1:---defconfig}"

case "$ACTION" in
    --defconfig)
        echo "[INFO] Aplicando mineos_defconfig..."
        make -C "$BUILDROOT_DIR" BR2_EXTERNAL="$EXTERNAL_DIR" mineos_defconfig
        echo "[OK] mineos_defconfig aplicado com sucesso!"
        echo "Para iniciar a compilação completa, execute: $0 --build"
        ;;
    --menuconfig)
        make -C "$BUILDROOT_DIR" BR2_EXTERNAL="$EXTERNAL_DIR" menuconfig
        ;;
    --savedefconfig)
        make -C "$BUILDROOT_DIR" BR2_EXTERNAL="$EXTERNAL_DIR" savedefconfig
        ;;
    --build)
        echo "[INFO] Iniciando compilação do sistema operacional..."
        make -C "$BUILDROOT_DIR" BR2_EXTERNAL="$EXTERNAL_DIR" -j"$(nproc)"
        echo "[SUCESSO] Imagens geradas em $BUILDROOT_DIR/output/images/!"
        ;;
    --clean)
        echo "[INFO] Limpando build..."
        make -C "$BUILDROOT_DIR" BR2_EXTERNAL="$EXTERNAL_DIR" clean
        ;;
    *)
        echo "Uso: $0 [--defconfig | --build | --menuconfig | --savedefconfig | --clean]"
        exit 1
        ;;
esac

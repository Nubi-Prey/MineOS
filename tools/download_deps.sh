#!/usr/bin/env bash
# tools/download_deps.sh - Download automatizado de dependências externas para o MineOS
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Eclipse Adoptium Temurin 25 JRE (Livre / GPLv2+CE)
JRE_VERSION="25.0.4.1+1"
JRE_FILE="OpenJDK25U-jre_x64_linux_hotspot_25.0.4.1_1.tar.gz"
JRE_SHA256="1731a34baadec5479258ea0202e4d5d865d2efeee60cb0c7d7eb056fe96ca219"
JRE_URL="https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.4.1%2B1/${JRE_FILE}"

TARGET_FILE="$PROJECT_ROOT/$JRE_FILE"

echo "================================================="
echo "MineOS: Verificador de Dependências Externas"
echo "================================================="

verify_checksum() {
    local file="$1"
    local expected="$2"
    echo "$expected  $file" | sha256sum --check --status 2>/dev/null
}

if [ -f "$TARGET_FILE" ]; then
    echo "[INFO] Verificando integridade de $JRE_FILE..."
    if verify_checksum "$TARGET_FILE" "$JRE_SHA256"; then
        echo "[OK] $JRE_FILE já presente e íntegro (SHA-256 verificado)."
        exit 0
    else
        echo "[AVISO] Checksum incorreto para $JRE_FILE existente. Baixando novamente..."
        rm -f "$TARGET_FILE"
    fi
fi

echo "[INFO] Baixando Eclipse Adoptium Temurin 25 JRE (~59 MB)..."
echo "       URL: $JRE_URL"
TMP_DOWNLOAD="${TARGET_FILE}.tmp"
curl -fL --progress-bar "$JRE_URL" -o "$TMP_DOWNLOAD"

echo "[INFO] Validando SHA-256..."
if verify_checksum "$TMP_DOWNLOAD" "$JRE_SHA256"; then
    mv "$TMP_DOWNLOAD" "$TARGET_FILE"
    echo "[SUCESSO] $JRE_FILE baixado e verificado com sucesso!"
else
    echo "[ERRO] Falha na validação SHA-256 do arquivo baixado!" >&2
    rm -f "$TMP_DOWNLOAD"
    exit 1
fi

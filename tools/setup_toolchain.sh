#!/usr/bin/env bash
# tools/setup_toolchain.sh - Instalação e verificação da toolchain Rust no espaço de usuário
set -euo pipefail

echo "========================================="
echo "MineOS: Configuração da Toolchain Rust"
echo "========================================="

CARGO_BIN="$HOME/.cargo/bin"
export PATH="$CARGO_BIN:$PATH"

if command -v cargo >/dev/null 2>&1 && command -v rustc >/dev/null 2>&1; then
    echo "[OK] Rust e Cargo já estão disponíveis no PATH:"
    rustc --version
    cargo --version
else
    echo "[INFO] Rust não encontrado no PATH. Instalando via rustup em espaço de usuário..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
    
    # Atualiza PATH na sessão atual
    export PATH="$CARGO_BIN:$PATH"
fi

echo "[INFO] Verificando compatibilidade com target x86_64-unknown-linux-gnu..."
rustup target add x86_64-unknown-linux-gnu 2>/dev/null || true

# Configura symlink de desenvolvimento local para xkbcommon se necessário
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LIB_DIR="$PROJECT_ROOT/tools/lib"
mkdir -p "$LIB_DIR"

if [[ ! -e "$LIB_DIR/libxkbcommon.so" && -e "/usr/lib/x86_64-linux-gnu/libxkbcommon.so.0" ]]; then
    echo "[INFO] Criando symlink de desenvolvimento para libxkbcommon.so em $LIB_DIR..."
    ln -sf /usr/lib/x86_64-linux-gnu/libxkbcommon.so.0 "$LIB_DIR/libxkbcommon.so"
fi

export LIBRARY_PATH="$LIB_DIR:${LIBRARY_PATH:-}"

echo "========================================="
echo "[SUCESSO] Toolchain Rust configurada!"
rustc --version
cargo --version
echo "========================================="

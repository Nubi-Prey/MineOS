#!/usr/bin/env bash
# tools/gdb_native.sh - Depuração GDB para código nativo Smithay/Rust (libwaylandcraft.so)
set -euo pipefail

TARGET_SO="/home/nubi/Documents/MineOS/waylandcraft-2.1.0/native/target/debug/libwaylandcraft.so"
CORE_OR_PID="${1:-}"

echo "========================================="
echo "MineOS Native Rust GDB Debugger"
echo "Biblioteca: $TARGET_SO"
echo "========================================="

GDB_BIN="rust-gdb"
if ! command -v rust-gdb >/dev/null 2>&1; then
    if [[ -x "$HOME/.cargo/bin/rust-gdb" ]]; then
        GDB_BIN="$HOME/.cargo/bin/rust-gdb"
    else
        GDB_BIN="gdb"
    fi
fi

if [[ -z "$CORE_OR_PID" ]]; then
    echo "Uso: $0 <PID_DO_PROCESSO_JAVA | ARQUIVO_CORE_DUMP>"
    echo "Exemplo: $0 12345"
    echo "Exemplo: $0 /tmp/core.dump"
    exit 1
fi

if [[ -f "$CORE_OR_PID" ]]; then
    echo "[INFO] Analisando core dump: $CORE_OR_PID"
    exec "$GDB_BIN" -ex "set pagination off" "$TARGET_SO" "$CORE_OR_PID"
else
    echo "[INFO] Anexando ao processo PID: $CORE_OR_PID"
    exec "$GDB_BIN" -ex "set pagination off" -p "$CORE_OR_PID"
fi

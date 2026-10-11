#!/usr/bin/env bash
# tools/gdb_kernel.sh - Conexão GDB ao stub do QEMU para depuração de Kernel Linux
set -euo pipefail

PORT="${1:-1234}"
VMLINUX="${2:-}"

echo "========================================="
echo "MineOS Kernel GDB Debugger"
echo "Conectando ao QEMU em localhost:$PORT"
echo "========================================="

GDB_ARGS=(
    -ex "set pagination off"
    -ex "set architecture i386:x86-64"
    -ex "target remote localhost:$PORT"
)

if [[ -n "$VMLINUX" && -f "$VMLINUX" ]]; then
    echo "[INFO] Carregando símbolos de kernel de: $VMLINUX"
    GDB_ARGS=(-ex "file $VMLINUX" "${GDB_ARGS[@]}")
fi

exec gdb "${GDB_ARGS[@]}"

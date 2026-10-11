#!/usr/bin/env bash
# tools/qemu_run.sh - Runner do QEMU com suporte a KVM, VirGL, QMP e Serial Logging
set -euo pipefail

HEADLESS=false
ISO_PATH=""
KERNEL_PATH=""
INITRD_PATH=""
ROOTFS_PATH=""
CUSTOM_APPEND=""
# Ajustado para 2560M (2.5G) para suportar JVM 1536M + Mesa VirGL + Cage sem swap
MEMORY="2560M"
CPUS="4"
QMP_SOCK="/tmp/mineos-qmp.sock"
SERIAL_LOG="/tmp/mineos-serial.log"
ENABLE_GDB=false
MC_DIR="/home/nubi/.minecraft"
EXTRA_ARGS=()

print_usage() {
    echo "Uso: $0 [opções]"
    echo "Opções:"
    echo "  --headless            Executa em modo sem janela gráfica (egl-headless / vnc)"
    echo "  --iso <caminho>       Arquivo de imagem ISO para boot"
    echo "  --kernel <caminho>    Kernel bzImage para direct kernel boot"
    echo "  --initrd <caminho>    Initramfs para direct kernel boot"
    echo "  --rootfs <caminho>    Disco rootfs.ext4 para VirtIO block"
    echo "  --append <args>       Linha de comando do kernel"
    echo "  --memory <tamanho>    Memória RAM alocada (padrão: 2560M)"
    echo "  --cpus <qtd>          Número de núcleos de CPU (padrão: 4)"
    echo "  --qmp-sock <caminho>  Caminho do socket Unix para controle QMP (padrão: /tmp/mineos-qmp.sock)"
    echo "  --serial-log <caminho>Arquivo de saída do console serial (padrão: /tmp/mineos-serial.log)"
    echo "  --display <sdl|gtk>   Backend de exibição interativo (padrão: sdl para trava de mouse Wayland)"
    echo "  --pointer <mouse|tablet> Dispositivo apontador (padrão: mouse para giro 360°)"
    echo "  --mc-dir <caminho>    Diretório .minecraft no host para montagem 9P (padrão: /home/nubi/.minecraft)"
    echo "  --gdb                 Habilita GDB stub do QEMU na porta :1234 (-s -S)"
    echo "  --help                Exibe esta ajuda"
}

DISPLAY_BACKEND="sdl"
POINTER_TYPE="mouse"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --headless) HEADLESS=true; shift ;;
        --iso) ISO_PATH="$2"; shift 2 ;;
        --kernel) KERNEL_PATH="$2"; shift 2 ;;
        --initrd) INITRD_PATH="$2"; shift 2 ;;
        --rootfs) ROOTFS_PATH="$2"; shift 2 ;;
        --append) CUSTOM_APPEND="$2"; shift 2 ;;
        --memory) MEMORY="$2"; shift 2 ;;
        --cpus) CPUS="$2"; shift 2 ;;
        --qmp-sock) QMP_SOCK="$2"; shift 2 ;;
        --serial-log) SERIAL_LOG="$2"; shift 2 ;;
        --display) DISPLAY_BACKEND="$2"; shift 2 ;;
        --pointer) POINTER_TYPE="$2"; shift 2 ;;
        --relative-mouse) POINTER_TYPE="mouse"; shift ;;
        --mc-dir) MC_DIR="$2"; shift 2 ;;
        --gdb) ENABLE_GDB=true; shift ;;
        --help) print_usage; exit 0 ;;
        *) EXTRA_ARGS+=("$1"); shift ;;
    esac
done

# Autodetecção de imagens padrão geradas pelo Buildroot se não especificadas
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEFAULT_KERNEL="$PROJECT_ROOT/buildroot/output/images/bzImage"
DEFAULT_ROOTFS="$PROJECT_ROOT/buildroot/output/images/rootfs.ext4"

if [[ -z "$ISO_PATH" && -z "$KERNEL_PATH" && -f "$DEFAULT_KERNEL" ]]; then
    KERNEL_PATH="$DEFAULT_KERNEL"
fi
if [[ -z "$ISO_PATH" && -z "$ROOTFS_PATH" && -f "$DEFAULT_ROOTFS" ]]; then
    ROOTFS_PATH="$DEFAULT_ROOTFS"
fi

# Define APPEND_ARGS baseado no tipo de boot
if [[ -n "$CUSTOM_APPEND" ]]; then
    APPEND_ARGS="$CUSTOM_APPEND"
elif [[ -n "$ROOTFS_PATH" ]]; then
    APPEND_ARGS="console=ttyS0,115200 root=/dev/vda rw earlyprintk=serial,ttyS0,115200"
else
    APPEND_ARGS="console=ttyS0,115200 root=/dev/ram0 rw earlyprintk=serial,ttyS0,115200"
fi

# Remove socket antigo se existir
rm -f "$QMP_SOCK"
# Prepara arquivo de log serial
touch "$SERIAL_LOG"

QEMU_CMD=(qemu-system-x86_64)

# Aceleração KVM
if [[ -r /dev/kvm && -w /dev/kvm ]]; then
    QEMU_CMD+=(-enable-kvm -cpu host)
else
    echo "[AVISO] /dev/kvm não acessível. Rodando com emulação de CPU TCG (mais lento)."
    QEMU_CMD+=(-cpu max)
fi

QEMU_CMD+=(
    -m "$MEMORY"
    -smp "$CPUS"
    -device virtio-keyboard-pci
)

# Dispositivo apontador: VirtIO Mouse (relativo) por padrão para rotação 360° fluida com pointer lock no SDL2
if [[ "$POINTER_TYPE" == "mouse" ]]; then
    QEMU_CMD+=(-device virtio-mouse-pci)
    echo "[INFO] Dispositivo apontador: VirtIO Mouse relativo (-device virtio-mouse-pci)."
else
    QEMU_CMD+=(-device virtio-tablet-pci)
    echo "[INFO] Dispositivo apontador: VirtIO Tablet absoluto (-device virtio-tablet-pci)."
fi

QEMU_CMD+=(
    # Rede em modo usuário com redirecionamento de portas (SSH: 2222, JDWP: 5005)
    -net nic,model=virtio
    -net user,hostfwd=tcp::2222-:22,hostfwd=tcp::5005-:5005
    # Socket de controle QMP para o Agente de IA
    -chardev "socket,id=qmp,path=$QMP_SOCK,server=on,wait=off"
    -mon chardev=qmp,mode=control
    # Console serial direcionado para arquivo monitorável
    -serial "file:$SERIAL_LOG"
)

# Configuração de Áudio (Intel HDA + PipeWire/ALSA)
if [[ "$HEADLESS" == true ]]; then
    QEMU_CMD+=(
        -audiodev none,id=snd0
        -device intel-hda
        -device hda-duplex,audiodev=snd0
    )
elif [[ "$DISPLAY_BACKEND" == "sdl" ]]; then
    QEMU_CMD+=(
        -audiodev sdl,id=snd0
        -device intel-hda
        -device hda-duplex,audiodev=snd0
    )
else
    QEMU_CMD+=(
        -audiodev pa,id=snd0
        -device intel-hda
        -device hda-duplex,audiodev=snd0
    )
fi

# Configuração gráfica
if [[ "$HEADLESS" == true ]]; then
    # Modo Headless com virgl e suporte a screendump via QMP
    QEMU_CMD+=(
        -device virtio-vga-gl,id=video0,xres=854,yres=480,max_hostmem=1073741824
        -display egl-headless
        -vnc :1
    )
    echo "[INFO] QEMU configurado em modo HEADLESS (VNC na porta :1, screendump ativo)."
else
    if [[ "$DISPLAY_BACKEND" == "sdl" ]]; then
        # Modo Interativo com SDL2 e OpenGL acelerado (suporte nativo a pointer lock no Wayland)
        QEMU_CMD+=(
            -device virtio-vga-gl,xres=854,yres=480,max_hostmem=1073741824
            -display sdl,gl=on,show-cursor=off
        )
        echo "[INFO] QEMU configurado em modo INTERATIVO com SDL2 (aceleração GL ativa, suporte a Wayland pointer lock). Pressione Ctrl+Alt+G para liberar o mouse."
    else
        # Modo Interativo com janela GTK e OpenGL acelerado
        QEMU_CMD+=(
            -device virtio-vga-gl,xres=854,yres=480,max_hostmem=1073741824
            -display gtk,gl=on,show-cursor=off,zoom-to-fit=on
        )
        echo "[INFO] QEMU configurado em modo INTERATIVO com GTK (GL ativo, cursor do host oculto e zoom ajustado)."
    fi
fi

# Mídia de Boot
if [[ -n "$ISO_PATH" ]]; then
    QEMU_CMD+=(-cdrom "$ISO_PATH" -boot d)
elif [[ -n "$KERNEL_PATH" ]]; then
    QEMU_CMD+=(-kernel "$KERNEL_PATH" -append "$APPEND_ARGS")
    if [[ -n "$INITRD_PATH" ]]; then
        QEMU_CMD+=(-initrd "$INITRD_PATH")
    fi
    if [[ -n "$ROOTFS_PATH" ]]; then
        QEMU_CMD+=(-drive "file=$ROOTFS_PATH,format=raw,if=virtio")
    fi
fi

# VirtFS 9P para compartilhamento sem cópia dos dados do Minecraft do Host
if [[ -n "$MC_DIR" && -d "$MC_DIR" ]]; then
    QEMU_CMD+=(-virtfs "local,path=$MC_DIR,mount_tag=mc_data,security_model=none")
    echo "[INFO] VirtFS 9P habilitado: $MC_DIR -> mount_tag 'mc_data'"
fi

# GDB Stub
if [[ "$ENABLE_GDB" == true ]]; then
    echo "[INFO] GDB stub ativo na porta :1234 (-s)."
    QEMU_CMD+=(-s)
fi

# Argumentos adicionais
QEMU_CMD+=("${EXTRA_ARGS[@]}")

echo "========================================="
echo "MineOS QEMU Runner"
echo "QMP Socket: $QMP_SOCK"
echo "Serial Log: $SERIAL_LOG"
echo "Executando: ${QEMU_CMD[*]}"
echo "========================================="

exec "${QEMU_CMD[@]}"

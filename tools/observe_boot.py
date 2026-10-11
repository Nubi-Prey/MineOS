#!/usr/bin/env python3
"""tools/observe_boot.py - Inicializa a imagem do MineOS no QEMU e transmite todos os logs em tempo real.

Monitora marcos:
- Kernel Linux 6.6.21
- Reconhecimento da GPU virtio-gpu DRM/KMS
- Montagem do rootfs ext4 (/dev/vda)
- Execução do BusyBox PID 1
- Serviço S99mineos (usuário, XDG_RUNTIME_DIR, Cage kiosk)
- Captura de screenshot do framebuffer via QMP
"""

import os
import sys
import time
import subprocess
import shutil

MINEOS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(MINEOS_ROOT, "tools"))
from qemu_qmp import QMPClient

SERIAL_LOG = "/tmp/mineos-serial.log"
QMP_SOCK = "/tmp/mineos-qmp.sock"
SCREENSHOT_PNG = "/tmp/mineos_boot_screen.png"
OUTPUT_LOG_FILE = os.path.join(MINEOS_ROOT, "boot_log.txt")
ARTIFACT_DIR = os.environ.get("ARTIFACT_DIR", "/home/nubi/.gemini/antigravity-cli/brain/154a0523-39a8-4358-8bbf-eb2e94bb61db")

# Cores ANSI para saída rica no terminal
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_BLUE = "\033[34m"
C_CYAN = "\033[36m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_MAGENTA = "\033[35m"

def categorize_line(line: str) -> str:
    line_lower = line.lower()
    if "panic" in line_lower or "oops" in line_lower or "call trace" in line_lower:
        badge = f"{C_BOLD}{C_RED}[KERNEL PANIC]{C_RESET}"
    elif "mineos" in line_lower or "cage" in line_lower or "wayland" in line_lower:
        badge = f"{C_BOLD}{C_GREEN}[MINEOS/UI]{C_RESET}"
    elif "init started" in line_lower or "busybox" in line_lower or "sysinit" in line_lower or "rcs" in line_lower:
        badge = f"{C_BOLD}{C_MAGENTA}[INIT/PID1]{C_RESET}"
    elif "drm" in line_lower or "virtio-gpu" in line_lower or "virtio_gpu" in line_lower or "fbcon" in line_lower or "framebuffer" in line_lower:
        badge = f"{C_BOLD}{C_CYAN}[DRM/GPU]{C_RESET}"
    elif "ext4" in line_lower or "vda" in line_lower or "mounted filesystem" in line_lower or "blk" in line_lower:
        badge = f"{C_BOLD}{C_YELLOW}[STORAGE]{C_RESET}"
    else:
        badge = f"{C_BLUE}[KERNEL]{C_RESET}"
    return f"{badge} {line.rstrip()}"

def main():
    print(f"{C_BOLD}{C_GREEN}======================================================{C_RESET}")
    print(f"{C_BOLD}{C_GREEN}MineOS: Boot da Imagem do SO & Observabilidade de Logs{C_RESET}")
    print(f"{C_BOLD}{C_GREEN}======================================================{C_RESET}")

    bzimage = os.path.join(MINEOS_ROOT, "buildroot", "output", "images", "bzImage")
    rootfs_ext4 = os.path.join(MINEOS_ROOT, "buildroot", "output", "images", "rootfs.ext4")
    rootfs_cpio = os.path.join(MINEOS_ROOT, "buildroot", "output", "images", "rootfs.cpio")

    if not os.path.isfile(bzimage):
        print(f"{C_RED}[ERRO] bzImage não encontrada em: {bzimage}{C_RESET}")
        sys.exit(1)

    use_rootfs = None
    use_initrd = None
    if os.path.isfile(rootfs_ext4):
        use_rootfs = rootfs_ext4
        print(f"[INFO] Disco RootFS (VirtIO Ext4): {rootfs_ext4}")
    elif os.path.isfile(rootfs_cpio):
        use_initrd = rootfs_cpio
        print(f"[INFO] Initramfs (CPIO): {rootfs_cpio}")
    else:
        print(f"{C_RED}[ERRO] Nenhuma imagem de rootfs encontrada em buildroot/output/images/{C_RESET}")
        sys.exit(1)

    # Limpa resíduos anteriores
    for p in [SERIAL_LOG, QMP_SOCK, SCREENSHOT_PNG]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass

    # Garante arquivo de log serial
    with open(SERIAL_LOG, "w") as f:
        f.write("")

    cmd = [
        os.path.join(MINEOS_ROOT, "tools", "qemu_run.sh"),
        "--headless",
        "--memory", "2G",
        "--cpus", "4",
        "--kernel", bzimage,
        "--qmp-sock", QMP_SOCK,
        "--serial-log", SERIAL_LOG,
    ]
    if use_rootfs:
        cmd.extend(["--rootfs", use_rootfs])
    elif use_initrd:
        cmd.extend(["--initrd", use_initrd])

    print(f"[INFO] Disparando QEMU: {' '.join(cmd)}")
    qemu_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    milestones_reached = {
        "kernel_started": False,
        "drm_virtio_gpu": False,
        "rootfs_mounted": False,
        "init_started": False,
        "mineos_script": False,
        "minecraft_launched": False,
    }

    start_time = time.time()
    max_duration = 110.0 # Timeout expandido para permitir carregamento completo dos mods e assets
    qmp_client = QMPClient(socket_path=QMP_SOCK, timeout=5.0)
    qmp_connected = False

    log_file_handle = open(SERIAL_LOG, "r", encoding="utf-8", errors="replace")
    all_captured_lines = []

    try:
        print(f"{C_BOLD}[LOGS EM TEMPO REAL INICIADOS - Pressione Ctrl+C para encerrar]{C_RESET}\n" + "-"*60)
        while time.time() - start_time < max_duration:
            line = log_file_handle.readline()
            if line:
                all_captured_lines.append(line)
                formatted = categorize_line(line)
                print(formatted)
                sys.stdout.flush()

                # Checagem de marcos
                if "Linux version 6.6" in line:
                    milestones_reached["kernel_started"] = True
                if "virtio_gpu" in line.lower() or "virtio-gpu" in line.lower():
                    milestones_reached["drm_virtio_gpu"] = True
                if "mounted filesystem" in line.lower() or "ext4-fs (vda)" in line.lower():
                    milestones_reached["rootfs_mounted"] = True
                if "init started" in line.lower() or "busybox" in line.lower():
                    milestones_reached["init_started"] = True
                if "mineos" in line.lower() or "cage" in line.lower():
                    milestones_reached["mineos_script"] = True
                if "lançando jvm" in line.lower() or "knotclient" in line.lower() or "minecraft compositor" in line.lower():
                    milestones_reached["minecraft_launched"] = True

                # Conecta ao QMP assim que o socket estiver disponível
                if not qmp_connected and os.path.exists(QMP_SOCK):
                    try:
                        qmp_client.connect()
                        qmp_connected = True
                    except Exception:
                        pass
            else:
                if qemu_proc.poll() is not None:
                    print(f"\n{C_YELLOW}[AVISO] O processo QEMU encerrou com código {qemu_proc.poll()}{C_RESET}")
                    break
                time.sleep(0.1)

            # Se o Minecraft já foi lançado, aguarda criação dos atlas de textura ou timeout de 85s
            atlases_done = any("gui.png-atlas" in l or "shulker_boxes.png-atlas" in l for l in all_captured_lines[-15:])
            if milestones_reached["minecraft_launched"] and (atlases_done or (time.time() - start_time > 85.0)):
                time.sleep(6.0)
                while True:
                    rem = log_file_handle.readline()
                    if not rem:
                        break
                    all_captured_lines.append(rem)
                    print(categorize_line(rem))
                break

        print("-" * 60)
        print(f"{C_BOLD}{C_GREEN}Observação de boot concluída após {time.time() - start_time:.1f}s{C_RESET}")

        # Conecta QMP para screendump caso não tenha conectado ainda
        if not qmp_connected and os.path.exists(QMP_SOCK):
            try:
                qmp_client.connect()
                qmp_connected = True
            except Exception as e:
                print(f"[AVISO] Falha ao conectar QMP: {e}")

        screenshot_ok = False
        if qmp_connected:
            try:
                print("[INFO] Capturando screenshot do framebuffer via QMP...")
                qmp_client.screenshot(SCREENSHOT_PNG)
                screenshot_ok = True
            except Exception as e:
                print(f"[AVISO] Screendump QMP indisponível ({e}). Tentando VNC fallback...")

        if not screenshot_ok:
            try:
                import importlib.util
                vnc_spec = importlib.util.spec_from_file_location("vnc_screenshot", os.path.join(MINEOS_ROOT, "tools", "vnc_screenshot.py"))
                vnc_mod = importlib.util.module_from_spec(vnc_spec)
                vnc_spec.loader.exec_module(vnc_mod)
                screenshot_ok = vnc_mod.grab_vnc(output_png=SCREENSHOT_PNG)
            except Exception as e:
                print(f"[AVISO] Falha no VNC screenshot fallback: {e}")

        if screenshot_ok and os.path.exists(SCREENSHOT_PNG):
            size = os.path.getsize(SCREENSHOT_PNG)
            print(f"{C_BOLD}{C_GREEN}[SUCESSO] Screenshot capturado ({size} bytes): {SCREENSHOT_PNG}{C_RESET}")
            if os.path.isdir(ARTIFACT_DIR):
                art_path = os.path.join(ARTIFACT_DIR, "mineos_live_boot.png")
                shutil.copyfile(SCREENSHOT_PNG, art_path)
                print(f"[INFO] Screenshot salvo no diretório de artefatos: {art_path}")

        # Executa teste de interação com o mouse via VNC / virtio-tablet
        try:
            print("[INFO] Testando interação com o mouse (movimento e clique no botão Singleplayer)...")
            mouse_spec = importlib.util.spec_from_file_location("test_mouse_interaction", os.path.join(MINEOS_ROOT, "tools", "test_mouse_interaction.py"))
            mouse_mod = importlib.util.module_from_spec(mouse_spec)
            mouse_spec.loader.exec_module(mouse_mod)
            mouse_mod.run_vnc_click_test()
        except Exception as e:
            print(f"[AVISO] Teste de clique de mouse falhou: {e}")
    finally:
        log_file_handle.close()
        # Salva o arquivo de log completo (incluindo o teste de interação)
        if os.path.exists(SERIAL_LOG):
            shutil.copyfile(SERIAL_LOG, OUTPUT_LOG_FILE)
        else:
            with open(OUTPUT_LOG_FILE, "w", encoding="utf-8") as out_f:
                out_f.writelines(all_captured_lines)
        print(f"[INFO] Log completo salvo em: {OUTPUT_LOG_FILE}")

        # Desliga a VM
        if qmp_connected:
            try:
                qmp_client.quit()
            except Exception:
                pass
            qmp_client.close()

        if qemu_proc.poll() is None:
            qemu_proc.terminate()
            try:
                qemu_proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                qemu_proc.kill()

    print(f"\n{C_BOLD}Resumo dos Marcos Atingidos:{C_RESET}")
    for k, v in milestones_reached.items():
        status_text = f"{C_GREEN}SIM{C_RESET}" if v else f"{C_RED}NÃO{C_RESET}"
        print(f"  - {k}: {status_text}")

if __name__ == "__main__":
    main()

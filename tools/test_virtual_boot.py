#!/usr/bin/env python3
"""tools/test_virtual_boot.py - Dispara e inspeciona o ambiente virtualizado do MineOS."""

import os
import sys
import time

MINEOS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(MINEOS_ROOT, "tools"))
sys.path.insert(0, os.path.join(MINEOS_ROOT, "tests", "harness"))

from vm_runner import VMRunner

def main():
    print("=========================================")
    print("MineOS: Inicializando Ambiente Virtualizado")
    print("=========================================")

    screenshot_file = "/tmp/mineos_virtual_display.png"
    runner = VMRunner(memory="1G", cpus="2")

    try:
        print("[1/4] Disparando QEMU com KVM e VirGL...")
        runner.start(timeout=10.0)

        print("[2/4] Consultando telemetria e status via QMP...")
        status = runner.get_status()
        print(f"Status da Máquina Virtual: {status.get('return', {}).get('status', 'desconhecido')}")

        print("[3/4] Aguardando inicialização do display gráfico (2 segundos)...")
        time.sleep(2)

        print(f"[4/4] Capturando frame atual da tela virtual para: {screenshot_file}")
        saved_img = runner.screenshot(screenshot_file)
        size = os.path.getsize(saved_img)
        print(f"[SUCESSO] Frame da tela capturado ({size} bytes): {saved_img}")

    finally:
        print("[INFO] Encerrando sessão de teste da VM de forma limpa...")
        runner.stop()
        print("[OK] VM finalizada.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""tests/harness/vm_runner.py - Gerenciador automatizado do ciclo de vida da VM para testes de IA."""

import os
import sys
import time
import subprocess
from typing import Optional, List, Dict, Any

MINEOS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(MINEOS_ROOT, "tools"))
from qemu_qmp import QMPClient

class VMRunner:
    def __init__(
        self,
        qmp_sock: str = "/tmp/mineos-test-qmp.sock",
        serial_log: str = "/tmp/mineos-test-serial.log",
        memory: str = "1G",
        cpus: str = "2"
    ):
        self.qmp_sock = qmp_sock
        self.serial_log = serial_log
        self.memory = memory
        self.cpus = cpus
        self.proc: Optional[subprocess.Popen] = None
        self.qmp: Optional[QMPClient] = None

    def start(self, extra_args: Optional[List[str]] = None, timeout: float = 15.0) -> None:
        """Inicia a VM em segundo plano com timeout para subida do socket QMP."""
        # Limpa resíduos anteriores
        if os.path.exists(self.qmp_sock):
            try:
                os.remove(self.qmp_sock)
            except OSError:
                pass
        if os.path.exists(self.serial_log):
            try:
                os.remove(self.serial_log)
            except OSError:
                pass

        cmd = [
            os.path.join(MINEOS_ROOT, "tools", "qemu_run.sh"),
            "--headless",
            "--memory", self.memory,
            "--cpus", self.cpus,
            "--qmp-sock", self.qmp_sock,
            "--serial-log", self.serial_log,
        ]
        
        bzimage = os.path.join(MINEOS_ROOT, "buildroot", "output", "images", "bzImage")
        initrd = os.path.join(MINEOS_ROOT, "buildroot", "output", "images", "rootfs.cpio")
        if os.path.isfile(bzimage):
            cmd.extend(["--kernel", bzimage])
            if os.path.isfile(initrd):
                cmd.extend(["--initrd", initrd])

        if extra_args:
            cmd.extend(extra_args)

        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Aguarda criação e resposta do socket QMP
        start_time = time.time()
        self.qmp = QMPClient(socket_path=self.qmp_sock, timeout=5.0)
        connected = False
        while time.time() - start_time < timeout:
            if os.path.exists(self.qmp_sock):
                try:
                    self.qmp.connect()
                    connected = True
                    break
                except Exception:
                    time.sleep(0.3)
            time.sleep(0.3)

        if not connected:
            self.stop()
            raise TimeoutError(f"QEMU não iniciou ou socket QMP não respondeu em {timeout}s.")

    def screenshot(self, output_path: str) -> str:
        """Captura o framebuffer atual do QEMU."""
        if not self.qmp:
            raise RuntimeError("VM não conectada via QMP.")
        return self.qmp.screenshot(output_path)

    def send_keys(self, keys: List[str]) -> Dict[str, Any]:
        if not self.qmp:
            raise RuntimeError("VM não conectada via QMP.")
        return self.qmp.send_keys(keys)

    def get_status(self) -> Dict[str, Any]:
        if not self.qmp:
            raise RuntimeError("VM não conectada via QMP.")
        return self.qmp.get_status()

    def read_serial_log(self) -> str:
        if not os.path.exists(self.serial_log):
            return ""
        with open(self.serial_log, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def stop(self) -> None:
        """Finalização limpa com fallback para SIGTERM/SIGKILL."""
        if self.qmp:
            try:
                self.qmp.quit()
            except Exception:
                pass
            self.qmp.close()
            self.qmp = None

        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3.0)
            except Exception:
                try:
                    self.proc.kill()
                    self.proc.wait(timeout=2.0)
                except Exception:
                    pass
        self.proc = None

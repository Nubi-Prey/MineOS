#!/usr/bin/env python3
"""tests/test_qemu_infrastructure.py - Teste de integração do QEMU com QMP, VirGL e Screendump."""

import unittest
import os
import sys

MINEOS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(MINEOS_ROOT, "tests", "harness"))
from vm_runner import VMRunner

class TestQEMUInfrastructure(unittest.TestCase):
    def setUp(self):
        self.screenshot_out = "/tmp/test_mineos_boot_frame.png"
        if os.path.exists(self.screenshot_out):
            try:
                os.remove(self.screenshot_out)
            except OSError:
                pass
        self.runner = VMRunner(memory="512M", cpus="2")

    def tearDown(self):
        self.runner.stop()
        if os.path.exists(self.screenshot_out):
            try:
                os.remove(self.screenshot_out)
            except OSError:
                pass

    def test_qemu_headless_boot_and_screenshot(self):
        """Valida se o QEMU sobe em modo headless, responde ao QMP e tira screenshot com sucesso."""
        # Inicia a VM (sem mídia para testar o BIOS inicial e tela de boot)
        self.runner.start(timeout=10.0)

        # 1. Valida status
        st = self.runner.get_status()
        self.assertIn("return", st)
        status_info = st["return"]
        self.assertEqual(status_info.get("status"), "running")

        # 2. Testa screendump via QMP
        saved_path = self.runner.screenshot(self.screenshot_out)
        self.assertTrue(os.path.isfile(saved_path), "Screenshot não foi gerado no sistema de arquivos.")
        size_bytes = os.path.getsize(saved_path)
        self.assertGreater(size_bytes, 100, f"Arquivo de screenshot vazio ou corrompido: {size_bytes} bytes.")

        # 3. Testa envio de tecla
        res_key = self.runner.send_keys(["ret"])
        self.assertIn("return", res_key)

if __name__ == "__main__":
    unittest.main()

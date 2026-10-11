#!/usr/bin/env python3
"""tests/test_rust_unit.py - Validação da compilação e integridade da biblioteca Rust."""

import unittest
import os
import subprocess
import shutil

MINEOS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NATIVE_DIR = os.path.join(MINEOS_ROOT, "waylandcraft-2.1.0", "native")
LIB_PATH = os.path.join(NATIVE_DIR, "target", "debug", "libwaylandcraft.so")
if not os.path.isfile(LIB_PATH):
    LIB_PATH = os.path.join(MINEOS_ROOT, "waylandcraft-2.1.0", "native-libs", "libwaylandcraft-linux-gnu-x86_64.so")

class TestRustNative(unittest.TestCase):
    def setUp(self):
        self.env = os.environ.copy()
        self.env["PATH"] = f"{os.path.expanduser('~/.cargo/bin')}:{self.env.get('PATH', '')}"
        self.env["LIBRARY_PATH"] = f"{os.path.join(MINEOS_ROOT, 'tools', 'lib')}:{self.env.get('LIBRARY_PATH', '')}"

    def test_cargo_and_rustc_available(self):
        """Verifica se rustc e cargo estão disponíveis e funcionais."""
        res_rustc = subprocess.run(["rustc", "--version"], env=self.env, capture_output=True, text=True)
        self.assertEqual(res_rustc.returncode, 0)
        self.assertIn("rustc", res_rustc.stdout)

        res_cargo = subprocess.run(["cargo", "--version"], env=self.env, capture_output=True, text=True)
        self.assertEqual(res_cargo.returncode, 0)
        self.assertIn("cargo", res_cargo.stdout)

    def test_native_so_exists_and_is_elf(self):
        """Verifica se a biblioteca compartilhada libwaylandcraft.so é um binário ELF x86-64 válido."""
        self.assertTrue(os.path.isfile(LIB_PATH), f"libwaylandcraft.so não encontrado em: {LIB_PATH}")
        size_bytes = os.path.getsize(LIB_PATH)
        self.assertGreater(size_bytes, 1024 * 1024, "Tamanho de libwaylandcraft.so menor que 1MB")

        # Valida header ELF (magic 0x7F 'E' 'L' 'F')
        with open(LIB_PATH, "rb") as f:
            magic = f.read(4)
        self.assertEqual(magic, b"\x7fELF", "Arquivo compilado não possui assinatura ELF válida")

    def test_jni_symbols_exported(self):
        """Verifica se os símbolos essenciais JNI do Waylandcraft estão expostos para o Java."""
        res = subprocess.run(
            ["nm", "-D", LIB_PATH],
            capture_output=True, text=True
        )
        self.assertEqual(res.returncode, 0)
        output = res.stdout

        required_symbols = [
            "Java_dev_evvie_waylandcraft_bridge_WaylandCraftBridge_checkDndActive",
            "Java_dev_evvie_waylandcraft_bridge_WaylandCraftBridge_checkImportDmabuf",
            "Java_dev_evvie_waylandcraft_bridge_WaylandCraftBridge_dispatchClients",
            "Java_dev_evvie_waylandcraft_bridge_WaylandCraftBridge_dmabufs",
            "Java_dev_evvie_waylandcraft_bridge_WaylandCraftBridge_drmDeviceByPath",
            "Java_dev_evvie_waylandcraft_bridge_WaylandCraftBridge_execApp"
        ]
        for sym in required_symbols:
            self.assertIn(sym, output, f"Símbolo JNI obrigatório {sym} não encontrado no binário nativo!")

if __name__ == "__main__":
    unittest.main()

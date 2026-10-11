#!/usr/bin/env python3
"""tests/test_buildroot_config.py - Validação da árvore externa do Buildroot e do rootfs overlay."""

import unittest
import os

MINEOS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTERNAL_DIR = os.path.join(MINEOS_ROOT, "buildroot-external")

class TestBuildrootConfig(unittest.TestCase):
    def test_external_tree_descriptors(self):
        """Valida se external.desc, external.mk e Config.in estão presentes e corretos."""
        desc_path = os.path.join(EXTERNAL_DIR, "external.desc")
        self.assertTrue(os.path.isfile(desc_path))
        with open(desc_path, "r") as f:
            content = f.read()
        self.assertIn("name: MINEOS", content)

        mk_path = os.path.join(EXTERNAL_DIR, "external.mk")
        self.assertTrue(os.path.isfile(mk_path))
        with open(mk_path, "r") as f:
            self.assertIn("BR2_EXTERNAL_MINEOS_PATH", f.read())

    def test_cage_package_available_and_selected(self):
        """Valida que o pacote Cage oficial existe no Buildroot e está selecionado no defconfig."""
        built_in_cage = os.path.join(MINEOS_ROOT, "buildroot", "package", "cage", "Config.in")
        self.assertTrue(os.path.isfile(built_in_cage), "Pacote oficial cage não encontrado no Buildroot")

        defconfig = os.path.join(EXTERNAL_DIR, "configs", "mineos_defconfig")
        with open(defconfig, "r") as f:
            self.assertIn("BR2_PACKAGE_CAGE=y", f.read())

    def test_rootfs_overlay_scripts(self):
        """Valida a existência dos scripts de inicialização e console serial no overlay."""
        inittab = os.path.join(EXTERNAL_DIR, "board", "mineos", "rootfs-overlay", "etc", "inittab")
        self.assertTrue(os.path.isfile(inittab))
        with open(inittab, "r") as f:
            content = f.read()
        self.assertIn("ttyS0", content, "Console serial ttyS0 para depuração da IA ausente no inittab")

        s99 = os.path.join(EXTERNAL_DIR, "board", "mineos", "rootfs-overlay", "etc", "init.d", "S99mineos")
        self.assertTrue(os.path.isfile(s99))
        with open(s99, "r") as f:
            content = f.read()
        self.assertIn("cage", content)
        self.assertIn("XDG_RUNTIME_DIR", content)

        mc_start = os.path.join(EXTERNAL_DIR, "board", "mineos", "rootfs-overlay", "opt", "mineos", "start-minecraft.sh")
        self.assertTrue(os.path.isfile(mc_start))
        with open(mc_start, "r") as f:
            content = f.read()
        self.assertIn("KnotClient", content)
        self.assertIn("jdwp", content)

    def test_defconfig_and_kernel_fragment(self):
        """Valida se o defconfig e o fragmento de kernel contêm os drivers e opções corretas."""
        defconfig = os.path.join(EXTERNAL_DIR, "configs", "mineos_defconfig")
        self.assertTrue(os.path.isfile(defconfig))
        with open(defconfig, "r") as f:
            content = f.read()
        self.assertIn("BR2_PACKAGE_CAGE=y", content)
        self.assertIn("BR2_PACKAGE_MESA3D=y", content)

        fragment = os.path.join(EXTERNAL_DIR, "board", "mineos", "linux.fragment")
        self.assertTrue(os.path.isfile(fragment))
        with open(fragment, "r") as f:
            content = f.read()
        self.assertIn("CONFIG_DRM_VIRTIO_GPU=y", content)
        self.assertIn("CONFIG_SERIAL_8250=y", content)

if __name__ == "__main__":
    unittest.main()

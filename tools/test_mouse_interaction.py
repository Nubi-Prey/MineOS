#!/usr/bin/env python3
"""tools/test_mouse_interaction.py - Teste automatizado de interação com o mouse via VNC / virtio-tablet."""

import os
import sys
import time
import socket
import struct
import subprocess
from PIL import Image

MINEOS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACT_DIR = os.environ.get("ARTIFACT_DIR", "/home/nubi/.gemini/antigravity-cli/brain/154a0523-39a8-4358-8bbf-eb2e94bb61db")

def run_vnc_click_test(host="127.0.0.1", port=5901):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10.0)
    s.connect((host, port))

    # 1. Handshake versão do protocolo
    version = s.recv(12)
    s.sendall(b"RFB 003.008\n")

    # 2. Tipos de autenticação
    data = s.recv(1)
    num_types = data[0]
    types = s.recv(num_types)
    if 1 not in types:
        s.close()
        raise RuntimeError(f"Autenticação sem suporte a 'None': {list(types)}")
    s.sendall(bytes([1]))

    # 3. Resultado de segurança
    sec_result = struct.unpack(">I", s.recv(4))[0]
    if sec_result != 0:
        s.close()
        raise RuntimeError(f"Falha de segurança RFB: {sec_result}")

    # 4. ClientInit (shared = 1)
    s.sendall(bytes([1]))

    # 5. ServerInit
    buf = s.recv(24)
    width, height = struct.unpack(">HH", buf[:4])
    name_len = struct.unpack(">I", buf[20:24])[0]
    name = s.recv(name_len).decode(errors="ignore")
    print(f"[VNC Client] Conectado: Desktop '{name}', Resolução: {width}x{height}")

    # SetEncodings: Raw (0)
    s.sendall(struct.pack(">BxH I", 2, 1, 0))

    # Helper para capturar frame atual
    def capture_frame(filename):
        s.sendall(struct.pack(">BBHHHH", 3, 0, 0, 0, width, height))
        msg_type = s.recv(1)[0]
        if msg_type != 0:
            return None
        s.recv(1)
        num_rects = struct.unpack(">H", s.recv(2))[0]
        pixels = bytearray(width * height * 4)
        for _ in range(num_rects):
            rect_hdr = s.recv(12)
            rx, ry, rw, rh, enc = struct.unpack(">HHHHi", rect_hdr)
            expected_bytes = rw * rh * 4
            received = bytearray()
            while len(received) < expected_bytes:
                chunk = s.recv(min(8192, expected_bytes - len(received)))
                if not chunk:
                    break
                received.extend(chunk)
            for row in range(rh):
                src_start = row * rw * 4
                src_end = src_start + rw * 4
                dest_start = ((ry + row) * width + rx) * 4
                dest_end = dest_start + rw * 4
                pixels[dest_start:dest_end] = received[src_start:src_end]

        # BGRA -> RGBA
        for i in range(0, len(pixels), 4):
            b, g, r, a = pixels[i], pixels[i+1], pixels[i+2], pixels[i+3]
            pixels[i] = r
            pixels[i+1] = g
            pixels[i+2] = b
            pixels[i+3] = 255
        img = Image.frombytes("RGBA", (width, height), bytes(pixels))
        img.save(filename)
        return img

    print("[VNC Client] Capturando tela inicial antes do clique...")
    before_img = capture_frame("/tmp/before_click.png")

    def click_mouse(x, y, hold=0.15):
        print(f"[VNC Client] Clicando em ({x}, {y})...")
        s.sendall(struct.pack(">BBHH", 5, 0, x, y))
        time.sleep(0.1)
        s.sendall(struct.pack(">BBHH", 5, 1, x, y))
        time.sleep(hold)
        s.sendall(struct.pack(">BBHH", 5, 0, x, y))
        time.sleep(0.2)

    # 1. Clica no botão Singleplayer (X=640, Y=365)
    click_mouse(640, 365)
    time.sleep(1.5)

    print("[VNC Client] Capturando tela 'Select World'...")
    after_path = os.path.join(ARTIFACT_DIR, "mineos_mouse_clicked.png")
    after_img = capture_frame(after_path)

    # 2. Seleciona o primeiro mundo da lista (X=640, Y=190)
    click_mouse(640, 190)
    time.sleep(0.5)

    # 3. Clica no botão 'Play Selected World' (X=398, Y=665)
    click_mouse(398, 665)

    print("[VNC Client] Aguardando 18s para geração de terreno, login e renderização do mundo...")
    time.sleep(18.0)

    world_path = os.path.join(ARTIFACT_DIR, "mineos_world_loaded.png")
    world_img = capture_frame(world_path)

    s.close()
    print(f"[SUCESSO] Screenshots salvas em: {after_path} e {world_path}")
    return True

if __name__ == "__main__":
    run_vnc_click_test()

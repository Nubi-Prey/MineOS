#!/usr/bin/env python3
"""tools/vnc_screenshot.py - Captura screenshot do display via VNC (RFB 3.8)."""

import socket
import struct
import sys
from PIL import Image

def grab_vnc(host="127.0.0.1", port=5901, output_png="vnc_screenshot.png"):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    try:
        s.connect((host, port))
    except Exception as e:
        print(f"[VNC] Não foi possível conectar a {host}:{port}: {e}")
        return False

    # 1. Handshake versão do protocolo
    version = s.recv(12)
    s.sendall(b"RFB 003.008\n")

    # 2. Tipos de autenticação
    data = s.recv(1)
    num_types = data[0]
    types = s.recv(num_types)
    if 1 not in types: # 1 = None (sem senha)
        print(f"[VNC] Autenticação necessária ou sem tipo 'None': {list(types)}")
        s.close()
        return False
    s.sendall(bytes([1])) # Seleciona tipo 'None'

    # 3. Resultado de segurança
    sec_result = struct.unpack(">I", s.recv(4))[0]
    if sec_result != 0:
        print(f"[VNC] Falha de segurança: {sec_result}")
        s.close()
        return False

    # 4. ClientInit (shared = 1)
    s.sendall(bytes([1]))

    # 5. ServerInit
    buf = s.recv(24)
    width, height = struct.unpack(">HH", buf[:4])
    name_len = struct.unpack(">I", buf[20:24])[0]
    name = s.recv(name_len).decode(errors="ignore")
    print(f"[VNC] Conectado: Desktop '{name}', Resolução: {width}x{height}")

    # SetEncodings: Raw (0)
    s.sendall(struct.pack(">BxH I", 2, 1, 0))

    # FramebufferUpdateRequest (incremental = 0)
    s.sendall(struct.pack(">BBHHHH", 3, 0, 0, 0, width, height))

    # Recebe FramebufferUpdate
    msg_type = s.recv(1)[0]
    if msg_type != 0:
        print(f"[VNC] Mensagem inesperada: {msg_type}")
        s.close()
        return False

    s.recv(1) # pad
    num_rects = struct.unpack(">H", s.recv(2))[0]
    
    img = Image.new("RGBA", (width, height))
    pixels = bytearray(width * height * 4)

    for _ in range(num_rects):
        rect_hdr = s.recv(12)
        rx, ry, rw, rh, enc = struct.unpack(">HHHHi", rect_hdr)
        if enc != 0: # Raw
            print(f"[VNC] Encoding não suportado: {enc}")
            continue
        expected_bytes = rw * rh * 4
        received = bytearray()
        while len(received) < expected_bytes:
            chunk = s.recv(min(4096, expected_bytes - len(received)))
            if not chunk:
                break
            received.extend(chunk)

        # Copia dados para a imagem (VNC normalmente é BGRX ou RGBX)
        for row in range(rh):
            src_start = row * rw * 4
            src_end = src_start + rw * 4
            dest_start = ((ry + row) * width + rx) * 4
            dest_end = dest_start + rw * 4
            pixels[dest_start:dest_end] = received[src_start:src_end]

    s.close()

    # VNC pixel format padrão QEMU: 32bpp, BGRA -> RGBA
    for i in range(0, len(pixels), 4):
        b, g, r, a = pixels[i], pixels[i+1], pixels[i+2], pixels[i+3]
        pixels[i] = r
        pixels[i+1] = g
        pixels[i+2] = b
        pixels[i+3] = 255

    img = Image.frombytes("RGBA", (width, height), bytes(pixels))
    img.save(output_png)
    print(f"[VNC] Screenshot salvo com sucesso em: {output_png}")
    return True

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "vnc_screenshot.png"
    grab_vnc(output_png=out)

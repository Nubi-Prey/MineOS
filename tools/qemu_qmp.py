#!/usr/bin/env python3
"""tools/qemu_qmp.py - Cliente QMP (QEMU Machine Protocol) para automação por Agentes de IA.

Permite:
- Captura de telas do framebuffer (screendump -> png via ffmpeg)
- Consulta de status da VM
- Envio de teclas simuladas
- Encerramento controlado da VM
"""

import sys
import os
import json
import socket
import subprocess
import argparse
from typing import Dict, Any, Optional

DEFAULT_QMP_SOCKET = "/tmp/mineos-qmp.sock"

class QMPClient:
    def __init__(self, socket_path: str = DEFAULT_QMP_SOCKET, timeout: float = 10.0):
        self.socket_path = socket_path
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None

    def connect(self) -> None:
        if not os.path.exists(self.socket_path):
            raise FileNotFoundError(f"Socket QMP não encontrado em: {self.socket_path}. A VM está em execução?")
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.socket_path)
        
        # Lê saudação do QMP
        initial = self._read_message()
        if "QMP" not in initial:
            raise RuntimeError(f"Resposta de saudação inválida do QMP: {initial}")
        
        # Envia qmp_capabilities para habilitar comandos
        self.execute("qmp_capabilities")

    def _read_message(self) -> Dict[str, Any]:
        assert self.sock is not None
        buffer = b""
        while b"\n" not in buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionResetError("Conexão com o socket QMP foi encerrada.")
            buffer += chunk
        line, _, _ = buffer.partition(b"\n")
        return json.loads(line.decode("utf-8"))

    def execute(self, command: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        assert self.sock is not None
        payload: Dict[str, Any] = {"execute": command}
        if arguments:
            payload["arguments"] = arguments
        self.sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        
        # Lê resposta ignorando eventos assíncronos
        while True:
            resp = self._read_message()
            if "return" in resp or "error" in resp:
                if "error" in resp:
                    raise RuntimeError(f"Erro no comando QMP '{command}': {resp['error']}")
                return resp

    def screenshot(self, output_png_path: str) -> str:
        """Tira screenshot do display via screendump e converte para PNG."""
        ppm_temp = output_png_path + ".tmp.ppm"
        try:
            try:
                self.execute("screendump", {"filename": ppm_temp, "device": "video0", "head": 0})
            except Exception:
                self.execute("screendump", {"filename": ppm_temp})
            # Converte ppm para png usando ffmpeg se disponível
            if os.path.exists("/usr/bin/ffmpeg"):
                cmd = ["ffmpeg", "-y", "-i", ppm_temp, output_png_path]
                res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if res.returncode == 0:
                    if os.path.exists(ppm_temp):
                        os.remove(ppm_temp)
                    return output_png_path
            # Fallback: mantém ppm
            if os.path.exists(ppm_temp):
                os.replace(ppm_temp, output_png_path)
            return output_png_path
        except Exception as e:
            if os.path.exists(ppm_temp):
                os.remove(ppm_temp)
            raise e

    def get_status(self) -> Dict[str, Any]:
        return self.execute("query-status")

    def send_keys(self, key_list: list) -> Dict[str, Any]:
        """Envia lista de teclas (ex: ['ctrl', 'alt', 'f1'] ou ['ret'])"""
        keys = [{"type": "qcode", "data": k} for k in key_list]
        return self.execute("send-key", {"keys": keys})

    def quit(self) -> Dict[str, Any]:
        return self.execute("quit")

    def close(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

def main():
    parser = argparse.ArgumentParser(description="Cliente QMP para QEMU MineOS")
    parser.add_argument("--sock", default=DEFAULT_QMP_SOCKET, help="Caminho do socket QMP")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # screenshot
    ss_parser = subparsers.add_parser("screenshot", help="Salva screenshot da VM")
    ss_parser.add_argument("output", help="Caminho do arquivo PNG de destino")

    # status
    subparsers.add_parser("status", help="Consulta status da VM")

    # send-keys
    keys_parser = subparsers.add_parser("send-keys", help="Envia teclas simuladas")
    keys_parser.add_argument("keys", nargs="+", help="Nomes das teclas QEMU (ex: ret, v, alt, q)")

    # quit
    subparsers.add_parser("quit", help="Fecha a VM de forma controlada")

    args = parser.parse_args()
    client = QMPClient(socket_path=args.sock)

    try:
        client.connect()
        if args.command == "screenshot":
            saved = client.screenshot(args.output)
            print(f"[OK] Screenshot salvo em: {saved}")
        elif args.command == "status":
            st = client.get_status()
            print(json.dumps(st, indent=2))
        elif args.command == "send-keys":
            res = client.send_keys(args.keys)
            print(f"[OK] Teclas enviadas: {args.keys}")
        elif args.command == "quit":
            client.quit()
            print("[OK] Comando de finalização enviado à VM.")
    finally:
        client.close()

if __name__ == "__main__":
    main()

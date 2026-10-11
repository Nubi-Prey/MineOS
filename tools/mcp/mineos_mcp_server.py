#!/usr/bin/env python3
"""tools/mcp/mineos_mcp_server.py - Servidor MCP (Model Context Protocol) do MineOS.

Implementa a especificação JSON-RPC 2.0 do MCP sobre stdio, expondo ferramentas
especializadas para o Agente de IA:
- qemu_start: Inicia a VM QEMU (headless ou interativa)
- qemu_screenshot: Captura o framebuffer via QMP e salva em PNG
- qemu_status: Consulta o estado da VM
- qemu_send_keys: Simula teclas no guest
- qemu_get_serial_logs: Lê os logs seriais mais recentes
- qemu_stop: Encerra a VM de forma controlada
- cargo_check: Roda cargo check e retorna diagnósticos estruturados
- cargo_test: Roda testes unitários do código nativo
- gdb_connect: Fornece instruções e status de conexão com o GDB
"""

import sys
import os
import json
import socket
import subprocess
from typing import Dict, Any, List, Optional

MINEOS_ROOT = os.environ.get("MINEOS_ROOT", "/home/nubi/Documents/MineOS")
DEFAULT_QMP_SOCKET = "/tmp/mineos-qmp.sock"
DEFAULT_SERIAL_LOG = "/tmp/mineos-serial.log"

# Importa cliente QMP
sys.path.insert(0, os.path.join(MINEOS_ROOT, "tools"))
from qemu_qmp import QMPClient

class MineOSMCPServer:
    def __init__(self):
        self.qmp_client = QMPClient(socket_path=DEFAULT_QMP_SOCKET)
        self.qemu_process: Optional[subprocess.Popen] = None

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "qemu_start",
                "description": "Inicia a máquina virtual QEMU do MineOS com aceleração KVM e instrumentação QMP.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "headless": {"type": "boolean", "description": "Se verdadeiro, roda em modo headless (egl-headless/vnc)", "default": True},
                        "iso_path": {"type": "string", "description": "Caminho da imagem ISO para boot"},
                        "memory": {"type": "string", "description": "Tamanho de memória RAM (ex: 4G)", "default": "4G"},
                        "enable_gdb": {"type": "boolean", "description": "Se verdadeiro, ativa gdb stub na porta :1234", "default": False}
                    }
                }
            },
            {
                "name": "qemu_screenshot",
                "description": "Captura uma imagem do framebuffer da tela virtual do MineOS via QMP (screendump) e converte para PNG.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "output_path": {"type": "string", "description": "Caminho completo do arquivo PNG de saída", "default": "/tmp/mineos_screenshot.png"}
                    },
                    "required": ["output_path"]
                }
            },
            {
                "name": "qemu_status",
                "description": "Consulta o estado atual da máquina virtual QEMU via QMP.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "qemu_send_keys",
                "description": "Envia teclas simuladas para o sistema operacional rodando na VM (ex: ['v'], ['alt', 'q'], ['ret']).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "keys": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Lista de teclas QEMU QCode"
                        }
                    },
                    "required": ["keys"]
                }
            },
            {
                "name": "qemu_get_serial_logs",
                "description": "Retorna as últimas linhas do console serial da VM (mensagens do Kernel Linux, init e JVM).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "lines": {"type": "integer", "description": "Número de linhas finais para retornar", "default": 50}
                    }
                }
            },
            {
                "name": "qemu_stop",
                "description": "Encerra a máquina virtual QEMU em execução.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "force": {"type": "boolean", "description": "Se verdadeiro, finaliza o processo imediatamente (SIGKILL)", "default": False}
                    }
                }
            },
            {
                "name": "cargo_check",
                "description": "Executa 'cargo check' no código nativo do Waylandcraft e retorna diagnósticos do compilador.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "cargo_test",
                "description": "Executa testes unitários do código Rust (Smithay / Waylandcraft).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "test_filter": {"type": "string", "description": "Filtro opcional de nome de teste", "default": ""}
                    }
                }
            }
        ]

    def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if name == "qemu_start":
                headless = arguments.get("headless", True)
                iso = arguments.get("iso_path")
                mem = arguments.get("memory", "4G")
                gdb = arguments.get("enable_gdb", False)
                cmd = [os.path.join(MINEOS_ROOT, "tools", "qemu_run.sh"), "--memory", mem]
                if headless:
                    cmd.append("--headless")
                if iso:
                    cmd.extend(["--iso", iso])
                if gdb:
                    cmd.append("--gdb")
                
                self.qemu_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return {"text": f"QEMU iniciado com PID {self.qemu_process.pid} (Headless: {headless})"}

            elif name == "qemu_screenshot":
                out_path = arguments.get("output_path", "/tmp/mineos_screenshot.png")
                self.qmp_client.connect()
                saved = self.qmp_client.screenshot(out_path)
                return {"text": f"Screenshot capturado com sucesso: {saved}"}

            elif name == "qemu_status":
                self.qmp_client.connect()
                st = self.qmp_client.get_status()
                return {"text": json.dumps(st, indent=2)}

            elif name == "qemu_send_keys":
                keys = arguments["keys"]
                self.qmp_client.connect()
                self.qmp_client.send_keys(keys)
                return {"text": f"Teclas enviadas com sucesso: {keys}"}

            elif name == "qemu_get_serial_logs":
                n_lines = arguments.get("lines", 50)
                if not os.path.exists(DEFAULT_SERIAL_LOG):
                    return {"text": "Arquivo de log serial ainda não existe."}
                with open(DEFAULT_SERIAL_LOG, "r", encoding="utf-8", errors="replace") as f:
                    all_lines = f.readlines()
                tail = "".join(all_lines[-n_lines:])
                return {"text": tail if tail else "(Log serial vazio)"}

            elif name == "qemu_stop":
                force = arguments.get("force", False)
                if not force:
                    try:
                        self.qmp_client.connect()
                        self.qmp_client.quit()
                        return {"text": "Comando QMP quit enviado com sucesso."}
                    except Exception:
                        pass
                if self.qemu_process and self.qemu_process.poll() is None:
                    self.qemu_process.terminate()
                    return {"text": "Processo QEMU finalizado."}
                return {"text": "Nenhum processo QEMU ativo para encerrar."}

            elif name == "cargo_check":
                native_dir = os.path.join(MINEOS_ROOT, "waylandcraft-2.1.0", "native")
                env = os.environ.copy()
                env["PATH"] = f"{os.path.expanduser('~/.cargo/bin')}:{env.get('PATH', '')}"
                env["LIBRARY_PATH"] = f"{os.path.join(MINEOS_ROOT, 'tools', 'lib')}:{env.get('LIBRARY_PATH', '')}"
                res = subprocess.run(
                    ["cargo", "check", "--message-format=short"],
                    cwd=native_dir, env=env, capture_output=True, text=True
                )
                output = (res.stdout + "\n" + res.stderr).strip()
                return {"text": output if output else "Cargo check OK sem avisos."}

            elif name == "cargo_test":
                native_dir = os.path.join(MINEOS_ROOT, "waylandcraft-2.1.0", "native")
                env = os.environ.copy()
                env["PATH"] = f"{os.path.expanduser('~/.cargo/bin')}:{env.get('PATH', '')}"
                env["LIBRARY_PATH"] = f"{os.path.join(MINEOS_ROOT, 'tools', 'lib')}:{env.get('LIBRARY_PATH', '')}"
                test_filter = arguments.get("test_filter", "")
                cmd = ["cargo", "test"]
                if test_filter:
                    cmd.append(test_filter)
                res = subprocess.run(cmd, cwd=native_dir, env=env, capture_output=True, text=True)
                output = (res.stdout + "\n" + res.stderr).strip()
                return {"text": output}

            else:
                return {"text": f"Ferramenta desconhecida: {name}", "isError": True}
        except Exception as e:
            return {"text": f"Erro ao executar {name}: {str(e)}", "isError": True}

    def run(self):
        """Loop de leitura do JSON-RPC no stdin e escrita no stdout."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_id = request.get("id")
            method = request.get("method")
            params = request.get("params", {})

            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "mineos-mcp-server", "version": "1.0.0"}
                    }
                }
                self._send(response)

            elif method == "notifications/initialized":
                pass  # Notificação do cliente, sem resposta esperada

            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"tools": self.get_tool_definitions()}
                }
                self._send(response)

            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                res = self.handle_tool_call(tool_name, tool_args)
                is_error = res.get("isError", False)
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": res.get("text", "")}],
                        "isError": is_error
                    }
                }
                self._send(response)

            elif msg_id is not None:
                # Método não suportado
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Método não encontrado: {method}"}
                }
                self._send(response)

    def _send(self, data: Dict[str, Any]) -> None:
        sys.stdout.write(json.dumps(data) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    server = MineOSMCPServer()
    server.run()

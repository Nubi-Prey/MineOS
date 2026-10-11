#!/usr/bin/env python3
"""tests/test_mcp_server.py - Teste de conformidade do protocolo MCP e das tools."""

import unittest
import subprocess
import json
import os
import sys

MINEOS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestMineOSMCPServer(unittest.TestCase):
    def setUp(self):
        server_path = os.path.join(MINEOS_ROOT, "tools", "mcp", "mineos_mcp_server.py")
        env = os.environ.copy()
        env["MINEOS_ROOT"] = MINEOS_ROOT
        env["PATH"] = f"{os.path.expanduser('~/.cargo/bin')}:{env.get('PATH', '')}"
        
        self.proc = subprocess.Popen(
            [sys.executable, server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )

    def tearDown(self):
        if self.proc:
            self.proc.terminate()
            self.proc.wait()

    def send_rpc(self, req: dict) -> dict:
        self.proc.stdin.write(json.dumps(req) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        return json.loads(line)

    def test_initialize_handshake(self):
        """Valida se o handshake initialize responde com capacidades e info do servidor."""
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-agent", "version": "1.0"}
            }
        }
        res = self.send_rpc(req)
        self.assertEqual(res.get("id"), 1)
        self.assertIn("result", res)
        self.assertEqual(res["result"]["serverInfo"]["name"], "mineos-mcp-server")
        self.assertIn("tools", res["result"]["capabilities"])

    def test_tools_list(self):
        """Valida se todas as ferramentas planejadas estão expostas no catálogo."""
        req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        res = self.send_rpc(req)
        self.assertIn("result", res)
        tools = res["result"].get("tools", [])
        tool_names = [t["name"] for t in tools]
        
        expected_tools = [
            "qemu_start", "qemu_screenshot", "qemu_status",
            "qemu_send_keys", "qemu_get_serial_logs", "qemu_stop",
            "cargo_check", "cargo_test"
        ]
        for expected in expected_tools:
            self.assertIn(expected, tool_names, f"Ferramenta {expected} ausente no MCP tools/list")

    def test_tool_call_cargo_check(self):
        """Valida execução da ferramenta cargo_check via chamada MCP."""
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "cargo_check",
                "arguments": {}
            }
        }
        res = self.send_rpc(req)
        self.assertIn("result", res)
        self.assertFalse(res["result"].get("isError", False))
        content = res["result"]["content"][0]["text"]
        self.assertIn("Finished", content)

if __name__ == "__main__":
    unittest.main()

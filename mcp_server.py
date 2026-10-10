#!/usr/bin/env python3
"""Fault-Keeper Sovereign MCP Server Launcher.

Provides stdio JSON-RPC 2.0 interface for AI Agents (Antigravity, Claude Desktop, Cursor).

Can be registered in MCP configuration (e.g. ~/.gemini/config/mcp_config.json):
{
  "fault-keeper": {
    "command": "L:\\.Python\\Python312\\python.exe",
    "args": ["L:\\.Tool\\Fault-Keeper\\mcp_server.py"],
    "env": {
      "PYTHONUNBUFFERED": "1",
      "PYTHONIOENCODING": "utf-8"
    }
  }
}
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure local src/ directory is at index 0 of sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = str((PROJECT_ROOT / "src").resolve())
if SRC_DIR in sys.path:
    sys.path.remove(SRC_DIR)
sys.path.insert(0, SRC_DIR)

if "fault_keeper" in sys.modules and not hasattr(sys.modules["fault_keeper"], "__path__"):
    del sys.modules["fault_keeper"]

from fault_keeper.core.mcp.server import MCPDispatcher


def main() -> None:
    """Run Fault-Keeper MCP 2.0 stdio dispatcher daemon."""
    dispatcher = MCPDispatcher()
    dispatcher.run_stdio_server()


if __name__ == "__main__":
    main()

"""Fault-Keeper MCP Omni-Facade — Cognitive Router & Adaptive Capability Arbiter.

Collapses ~51 fragmented system capabilities into exactly 4 Omni-Tools + 1 discovery tool,
adds in-memory JSON-RPC resource virtualization, and provides a compliant JSON-RPC 2.0
protocol dispatcher for AI Agent communication.

Operational Postures:
    CLI Engine      — `cli.py audit <path>` runs U-FSR / WPA-HIS / Tx-DLO / CDC-ABS
    MCP 2.0 Daemon   — stdio-based JSON-RPC server exposing fk_audit / fk_diagnose /
                       fk_patch / fk_verify / fk_discover Omni-Tools + resource URIs
    Library Facade   — `from fault_keeper.mcp import MCPOmniFacade` for direct invocation
"""

from __future__ import annotations

from fault_keeper.mcp.omni_facade import (
    estimate_token_count,
    get_omni_tools_schema,
    MCPOmniFacade,
    OmniToolDefinition,
    VirtualResourceProvider,
)

__all__ = [
    "estimate_token_count",
    "get_omni_tools_schema",
    "MCPOmniFacade",
    "OmniToolDefinition",
    "VirtualResourceProvider",
]
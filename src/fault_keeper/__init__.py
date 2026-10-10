"""Fault-Keeper: Sovereign Standalone Engine & MCP 2.0 Daemon (v1.0 Flagship Release)."""

from fault_keeper import (
    armor,
    audit,
    daily,
    distributed,
    formal,
    geo,
    mcp,
    num,
    sla,
    systems,
    timetravel,
    typing,
    workflow,
)
from fault_keeper.core.armor import ArmorViolationError, armored, guard, protect
from fault_keeper.core.facade import FaultKeeper
from fault_keeper.core.mcp.server import MCPDispatcher

__version__ = "1.0.0"

__all__ = [
    # Core Facade & Daemons
    "FaultKeeper",
    "MCPDispatcher",
    "guard",
    "protect",
    "armored",
    "ArmorViolationError",
    # Subpackages & Domains
    "num",
    "sla",
    "geo",
    "audit",
    "typing",
    "workflow",
    "daily",
    "systems",
    "armor",
    "mcp",
    "distributed",
    "timetravel",
    "formal",
]
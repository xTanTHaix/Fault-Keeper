"""Fault-Keeper Armor Package — Phase 4 Group 1.

AI Agent Synthesis Armor & Speculative Execution:
- ASP-HG: Agent Speculative Patch & Anti-Hallucination Guard
- ACT-LO: Agent Convergence & Thrashing-Loop Oracle
- SC-PVE: Speculative Candidate Parallel Verification & Invariant-Pruned Arbiter
"""

from __future__ import annotations

from fault_keeper.armor.asphg import (
    ASPHGEngine,
    PatchSentry,
    CandidatePatch,
    StructuredEdit,
    LazyTruncationViolationError,
    ParseGuardError,
    atomic_splice,
    detect_lazy_truncation,
    structural_anchor_score,
)
from fault_keeper.armor.actlo import (
    ACTLOEngine,
    MucSteeringAdvisor,
    DefectState,
    Observation,
    TurnResult,
    ConstraintClause,
    defect_entropy,
    minimal_unsatisfiable_core,
    state_similarity,
)
from fault_keeper.armor.scpve import (
    SCPVEEngine,
    CoWWorkerPool,
    ASTArbiter,
    CoWVFS,
    VfsEntry,
    SpeculativeRunResult,
    enable_virtual_time,
    disable_virtual_time,
    advance_virtual_time,
    virtual_time,
)

__version__ = "1.0.0"

__all__ = [
    # ASP-HG
    "ASPHGEngine",
    "PatchSentry",
    "CandidatePatch",
    "StructuredEdit",
    "LazyTruncationViolationError",
    "ParseGuardError",
    "atomic_splice",
    "detect_lazy_truncation",
    "structural_anchor_score",
    # ACT-LO
    "ACTLOEngine",
    "MucSteeringAdvisor",
    "DefectState",
    "Observation",
    "TurnResult",
    "ConstraintClause",
    "defect_entropy",
    "minimal_unsatisfiable_core",
    "state_similarity",
    # SC-PVE
    "SCPVEEngine",
    "CoWWorkerPool",
    "ASTArbiter",
    "CoWVFS",
    "VfsEntry",
    "SpeculativeRunResult",
    "enable_virtual_time",
    "disable_virtual_time",
    "advance_virtual_time",
    "virtual_time",
]

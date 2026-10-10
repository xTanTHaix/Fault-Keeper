"""CAM-RO Engine: Cross-Architecture Memory Reordering & Atomic Fence Synthesizer.

Evaluates formal memory model litmus tests (Store Buffering, Message Passing,
Load Buffering, IRIW) across x86-64 TSO, ARMv8, and RISC-V weak memory models,
synthesizing minimal fence barriers and atomic instructions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from .config import CAMROConfig


class ArchitectureModel(str, Enum):
    """Target hardware memory consistency architecture models."""

    X86_TSO = "x86_tso"
    ARMV8_WEAK = "armv8_weak"
    RISCV_WEAK = "riscv_weak"


class MemoryOrder(str, Enum):
    """C++11 / LLVM-style atomic memory order levels."""

    RELAXED = "relaxed"
    CONSUME = "consume"
    ACQUIRE = "acquire"
    RELEASE = "release"
    ACQ_REL = "acq_rel"
    SEQ_CST = "seq_cst"


@dataclass
class MemoryOperation:
    """Represents a single memory access within a concurrent execution thread."""

    thread_id: int
    op_type: str  # "read" or "write"
    address: int
    value: int = 0
    order: MemoryOrder = MemoryOrder.RELAXED


@dataclass
class LitmusTest:
    """Represents a microarchitectural litmus test pattern."""

    name: str
    operations: List[MemoryOperation]
    forbidden_outcome: Dict[int, int]
    description: str = ""

    def is_outcome_allowed(self, arch: ArchitectureModel) -> bool:
        """Determine whether the forbidden outcome is architecturally observable."""
        name_upper = self.name.upper()
        if "SB" in name_upper or "STORE_BUFFERING" in name_upper:
            # Store-load reordering allowed in both TSO and weak architectures
            return True
        if "MP" in name_upper or "MESSAGE_PASSING" in name_upper:
            # Weak memory allows load-load and store-store reordering without fences
            return arch in (ArchitectureModel.ARMV8_WEAK, ArchitectureModel.RISCV_WEAK)
        if "LB" in name_upper or "LOAD_BUFFERING" in name_upper:
            # Load buffering reordering only observable in weak memory
            return arch in (ArchitectureModel.ARMV8_WEAK, ArchitectureModel.RISCV_WEAK)
        if "IRIW" in name_upper:
            # Independent Reads of Independent Writes observable in non-multi-copy-atomic weak memory
            return arch in (ArchitectureModel.ARMV8_WEAK, ArchitectureModel.RISCV_WEAK)
        return False


class FenceSynthesizer:
    """Synthesizes optimal architecture-specific memory fences and atomic barriers."""

    def __init__(self, target_architecture: ArchitectureModel = ArchitectureModel.ARMV8_WEAK) -> None:
        self.target_architecture = target_architecture

    def synthesize_fences(self, operations: List[MemoryOperation]) -> List[str]:
        """Analyze memory access trace per thread and synthesize minimal required barriers.

        Returns list of assembly fence mnemonics.
        """
        if not operations:
            return []

        fences: List[str] = []
        # Group operations by thread_id preserving program order
        by_thread: Dict[int, List[MemoryOperation]] = {}
        for op in operations:
            by_thread.setdefault(op.thread_id, []).append(op)

        for thread_id, thread_ops in by_thread.items():
            for i in range(len(thread_ops) - 1):
                first = thread_ops[i]
                second = thread_ops[i + 1]

                op_pair = (first.op_type.lower(), second.op_type.lower())
                orders = (first.order, second.order)

                barrier = self._resolve_barrier_for_pair(op_pair, orders)
                if barrier and barrier not in fences:
                    fences.append(barrier)

        return fences

    def _resolve_barrier_for_pair(
        self,
        op_pair: Tuple[str, str],
        orders: Tuple[MemoryOrder, MemoryOrder],
    ) -> Optional[str]:
        """Resolve the minimal required barrier for an (op1, op2) sequence."""
        first_type, second_type = op_pair
        first_order, second_order = orders

        # If already strongly ordered via SeqCst or proper Acquire/Release, no raw fence needed
        if first_order == MemoryOrder.SEQ_CST and second_order == MemoryOrder.SEQ_CST:
            return None
        if first_order in (MemoryOrder.RELEASE, MemoryOrder.ACQ_REL) and first_type == "write":
            if second_type == "read" and self.target_architecture == ArchitectureModel.X86_TSO:
                pass  # Store-Load still requires fence even with release
            else:
                return None
        if second_order in (MemoryOrder.ACQUIRE, MemoryOrder.ACQ_REL) and second_type == "read":
            return None

        # Architecture-specific barrier synthesis
        if self.target_architecture == ArchitectureModel.X86_TSO:
            # x86-TSO preserves Write->Write, Read->Read, Read->Write.
            # Only Write->Read (Store Buffering) reorders!
            if first_type == "write" and second_type == "read":
                return "mfence"
            return None

        elif self.target_architecture == ArchitectureModel.ARMV8_WEAK:
            # ARMv8 weak memory relaxes all pairs under relaxed order
            if first_type == "write" and second_type == "read":
                return "dmb ish"
            elif first_type == "write" and second_type == "write":
                return "dmb ishst"
            elif first_type == "read" and second_type == "read":
                return "dmb ishld"
            elif first_type == "read" and second_type == "write":
                return "dmb ish"
            return "dmb ish"

        elif self.target_architecture == ArchitectureModel.RISCV_WEAK:
            if first_type == "write" and second_type == "read":
                return "fence w,r"
            elif first_type == "write" and second_type == "write":
                return "fence w,w"
            elif first_type == "read" and second_type == "read":
                return "fence r,r"
            elif first_type == "read" and second_type == "write":
                return "fence r,w"
            return "fence rw,rw"

        return None

    def promote_to_atomic_instructions(self, op: MemoryOperation) -> str:
        """Promote raw memory operation to load-acquire or store-release instruction."""
        if self.target_architecture == ArchitectureModel.ARMV8_WEAK:
            if op.op_type == "read":
                return f"ldar x0, [x1, #{op.address}]"
            else:
                return f"stlr x0, [x1, #{op.address}]"
        elif self.target_architecture == ArchitectureModel.X86_TSO:
            if op.op_type == "read":
                return f"mov rax, [rsi + {op.address}]"
            else:
                return f"mov [rsi + {op.address}], rax"
        else:
            if op.op_type == "read":
                return f"lr.d.aq a0, (a1)"
            else:
                return f"sc.d.rl a0, a2, (a1)"


__all__ = [
    "ArchitectureModel",
    "MemoryOrder",
    "MemoryOperation",
    "LitmusTest",
    "FenceSynthesizer",
]

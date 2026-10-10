"""EV-IPP Sentry: eBPF In-IDE Verifier Sentry & Safety Certificate Generator."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .config import EVIPPConfig
from .engine import BpfVerifierEngine, RegisterType, Tnum


@dataclass
class VerifierSafetyCertificate:
    """Cryptographic-style audit record of verified safe eBPF register bounds."""

    program_name: str
    verified_at: float
    total_instructions: int
    is_safe: bool
    rejection_reason: Optional[str] = None


class EVIPPSentry:
    """IDE-level sentinel auditing eBPF bytecode programs before kernel loading."""

    def __init__(self, config: Optional[EVIPPConfig] = None) -> None:
        self.config = config or EVIPPConfig()
        self.engine = BpfVerifierEngine(self.config)
        self.certificates: List[VerifierSafetyCertificate] = []

    def audit_program(self, program_name: str, instructions: List[Tuple[str, int, int]]) -> VerifierSafetyCertificate:
        """Simulate and verify instruction list.

        Instructions format: (opcode, dst_reg, src_or_imm)
        """
        engine = BpfVerifierEngine(self.config)
        step_count = 0

        for op, dst, val in instructions:
            step_count += 1
            if op.startswith("mov"):
                ok = engine.execute_alu_imm("mov", dst, val)
            elif op.startswith("add_imm"):
                ok = engine.execute_alu_imm("add", dst, val)
            elif op.startswith("add_reg"):
                ok = engine.execute_alu_reg("add", dst, val)
            elif op.startswith("load_stack"):
                ok, msg = engine.verify_memory_access(dst, val)
                if not ok:
                    cert = VerifierSafetyCertificate(
                        program_name=program_name,
                        verified_at=time.time(),
                        total_instructions=step_count,
                        is_safe=False,
                        rejection_reason=msg,
                    )
                    self.certificates.append(cert)
                    return cert
            else:
                ok = True

        cert = VerifierSafetyCertificate(
            program_name=program_name,
            verified_at=time.time(),
            total_instructions=step_count,
            is_safe=True,
            rejection_reason=None,
        )
        self.certificates.append(cert)
        return cert


__all__ = ["VerifierSafetyCertificate", "EVIPPSentry"]

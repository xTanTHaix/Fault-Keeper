"""Unit and invariant tests for EV-IPP Engine."""

import pytest

try:
    from fault_keeper.systems.kernel_ev_ipp.config import EVIPPConfig
    from fault_keeper.systems.kernel_ev_ipp.engine import (
        BpfRegister,
        BpfVerifierEngine,
        RegisterType,
        Tnum,
    )
except ImportError:
    from kernel_ev_ipp.config import EVIPPConfig
    from kernel_ev_ipp.engine import (
        BpfRegister,
        BpfVerifierEngine,
        RegisterType,
        Tnum,
    )


class TestTnumLattice:
    """Tests for Truncated Number arithmetic and lattice invariants."""

    def test_invariant_value_mask_disjoint(self) -> None:
        t = Tnum(value=0b1010, mask=0b0110)
        # Value must not have 1s where mask has 1s
        assert (t.value & t.mask) == 0

    def test_tnum_const_and_unknown(self) -> None:
        c = Tnum.const(42)
        assert c.is_const() is True
        assert c.value == 42
        assert c.mask == 0

        u = Tnum.unknown()
        assert u.is_const() is False
        assert u.mask == 0xFFFFFFFFFFFFFFFF

    def test_tnum_add_known_values(self) -> None:
        a = Tnum.const(15)
        b = Tnum.const(25)
        c = a.add(b)
        assert c.is_const() is True
        assert c.value == 40
        assert (c.value & c.mask) == 0

    def test_tnum_add_with_unknown_bits(self) -> None:
        # a is either 0 or 1 (mask 1)
        a = Tnum(value=0, mask=1)
        # b is exactly 4
        b = Tnum.const(4)
        c = a.add(b)
        assert c.value == 4
        assert c.mask == 1
        assert (c.value & c.mask) == 0


class TestBpfVerifierEngine:
    """Tests for simulated eBPF verifier bounds."""

    def test_register_alu_imm(self) -> None:
        engine = BpfVerifierEngine()
        engine.execute_alu_imm("mov", dst=2, imm=100)
        assert engine.registers[2].reg_type == RegisterType.SCALAR_VALUE
        assert engine.registers[2].var_off.value == 100

        engine.execute_alu_imm("add", dst=2, imm=50)
        assert engine.registers[2].var_off.value == 150

    def test_stack_access_verification(self) -> None:
        engine = BpfVerifierEngine()
        # R10 is frame pointer at 512
        # Accessing offset 500, size 4 is inside 512 bytes stack
        engine.registers[10].var_off = Tnum.const(500)
        ok, msg = engine.verify_memory_access(10, size=4)
        assert ok is True

        # Accessing offset 510, size 8 exceeds 512
        engine.registers[10].var_off = Tnum.const(510)
        ok, msg = engine.verify_memory_access(10, size=8)
        assert ok is False

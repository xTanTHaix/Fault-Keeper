"""Unit and invariant tests for CAM-RO Engine."""

import pytest

try:
    from fault_keeper.systems.ordering_cam_ro.config import CAMROConfig
    from fault_keeper.systems.ordering_cam_ro.engine import (
        ArchitectureModel,
        FenceSynthesizer,
        LitmusTest,
        MemoryOperation,
        MemoryOrder,
    )
except ImportError:
    from ordering_cam_ro.config import CAMROConfig
    from ordering_cam_ro.engine import (
        ArchitectureModel,
        FenceSynthesizer,
        LitmusTest,
        MemoryOperation,
        MemoryOrder,
    )


class TestLitmusTest:
    """Tests for architectural litmus test models."""

    def test_store_buffering_observable_on_all_models(self) -> None:
        lt = LitmusTest(
            name="SB_Litmus",
            operations=[
                MemoryOperation(0, "write", 0x10, 1),
                MemoryOperation(0, "read", 0x20, 0),
            ],
            forbidden_outcome={0: 0, 1: 0},
        )
        assert lt.is_outcome_allowed(ArchitectureModel.X86_TSO) is True
        assert lt.is_outcome_allowed(ArchitectureModel.ARMV8_WEAK) is True

    def test_message_passing_disallowed_on_tso(self) -> None:
        lt = LitmusTest(
            name="MP_Litmus",
            operations=[
                MemoryOperation(0, "write", 0x10, 1),
                MemoryOperation(0, "write", 0x20, 1),
            ],
            forbidden_outcome={0: 1, 1: 0},
        )
        assert lt.is_outcome_allowed(ArchitectureModel.X86_TSO) is False
        assert lt.is_outcome_allowed(ArchitectureModel.ARMV8_WEAK) is True


class TestFenceSynthesizer:
    """Tests for fence barrier synthesis across architectures."""

    def test_x86_tso_store_load_fence(self) -> None:
        synth = FenceSynthesizer(ArchitectureModel.X86_TSO)
        ops = [
            MemoryOperation(0, "write", 0x10, 1),
            MemoryOperation(0, "read", 0x20, 0),
        ]
        fences = synth.synthesize_fences(ops)
        assert "mfence" in fences

    def test_x86_tso_store_store_no_fence_needed(self) -> None:
        synth = FenceSynthesizer(ArchitectureModel.X86_TSO)
        ops = [
            MemoryOperation(0, "write", 0x10, 1),
            MemoryOperation(0, "write", 0x20, 2),
        ]
        fences = synth.synthesize_fences(ops)
        assert len(fences) == 0

    def test_armv8_store_buffering_dmb_ish(self) -> None:
        synth = FenceSynthesizer(ArchitectureModel.ARMV8_WEAK)
        ops = [
            MemoryOperation(0, "write", 0x10, 1),
            MemoryOperation(0, "read", 0x20, 0),
        ]
        fences = synth.synthesize_fences(ops)
        assert "dmb ish" in fences

    def test_seq_cst_requires_no_extra_fence(self) -> None:
        synth = FenceSynthesizer(ArchitectureModel.ARMV8_WEAK)
        ops = [
            MemoryOperation(0, "write", 0x10, 1, order=MemoryOrder.SEQ_CST),
            MemoryOperation(0, "read", 0x20, 0, order=MemoryOrder.SEQ_CST),
        ]
        fences = synth.synthesize_fences(ops)
        assert len(fences) == 0

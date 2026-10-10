"""Unit and invariant tests for MD-BBE Engine."""

import pytest

try:
    from fault_keeper.systems.binary_md_bbe.config import MDBBEConfig
    from fault_keeper.systems.binary_md_bbe.engine import (
        ABITypeDescriptor,
        GenericInstance,
        PolymorphicThunkDeduplicator,
        StructuralABIEquivalenceScanner,
    )
except ImportError:
    from binary_md_bbe.config import MDBBEConfig
    from binary_md_bbe.engine import (
        ABITypeDescriptor,
        GenericInstance,
        PolymorphicThunkDeduplicator,
        StructuralABIEquivalenceScanner,
    )


class TestStructuralABIEquivalenceScanner:
    """Tests for structural ABI equivalence detection."""

    def test_equivalent_pointer_types(self) -> None:
        scanner = StructuralABIEquivalenceScanner()
        # Vec<*const u8> vs Vec<*const f64> both pass 8-byte pointer arguments
        func_u8 = GenericInstance(
            symbol_name="vec_push_u8_ptr",
            arg_abis=[ABITypeDescriptor(name="*const u8", size=8, align=8)],
            ret_abi=ABITypeDescriptor(name="void", size=0, align=1),
        )
        func_f64 = GenericInstance(
            symbol_name="vec_push_f64_ptr",
            arg_abis=[ABITypeDescriptor(name="*const f64", size=8, align=8)],
            ret_abi=ABITypeDescriptor(name="void", size=0, align=1),
        )
        assert scanner.are_equivalent(func_u8, func_f64) is True

    def test_distinct_size_types_not_equivalent(self) -> None:
        scanner = StructuralABIEquivalenceScanner()
        func_u32 = GenericInstance(
            symbol_name="sort_u32",
            arg_abis=[ABITypeDescriptor(name="u32", size=4, align=4)],
            ret_abi=ABITypeDescriptor(name="void", size=0, align=1),
        )
        func_u64 = GenericInstance(
            symbol_name="sort_u64",
            arg_abis=[ABITypeDescriptor(name="u64", size=8, align=8)],
            ret_abi=ABITypeDescriptor(name="void", size=0, align=1),
        )
        assert scanner.are_equivalent(func_u32, func_u64) is False


class TestPolymorphicThunkDeduplicator:
    """Tests for folding instances into thunks and calculating reduction ratio."""

    def test_deduplication_savings(self) -> None:
        cfg = MDBBEConfig(thunk_overhead_bytes=16)
        deduplicator = PolymorphicThunkDeduplicator(cfg)

        # 4 identical pointer functions, 1000 bytes each
        instances = [
            GenericInstance(
                symbol_name=f"ptr_worker_{i}",
                arg_abis=[ABITypeDescriptor(name="ptr", size=8, align=8)],
                ret_abi=ABITypeDescriptor(name="ptr", size=8, align=8),
                code_size_bytes=1000,
            )
            for i in range(4)
        ]

        deduped, ratio = deduplicator.deduplicate(instances)
        # Original: 4000 bytes. Deduped: 1000 + 3 * 16 = 1048 bytes. Savings: ~73.8%
        assert ratio >= 0.70
        assert len(deduped) == 4

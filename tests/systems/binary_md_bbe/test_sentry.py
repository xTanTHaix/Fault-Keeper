"""Unit tests for MD-BBE Sentry."""

import pytest

try:
    from fault_keeper.systems.binary_md_bbe.config import MDBBEConfig
    from fault_keeper.systems.binary_md_bbe.engine import ABITypeDescriptor, GenericInstance
    from fault_keeper.systems.binary_md_bbe.sentry import MDBBESentry
except ImportError:
    from binary_md_bbe.config import MDBBEConfig
    from binary_md_bbe.engine import ABITypeDescriptor, GenericInstance
    from binary_md_bbe.sentry import MDBBESentry


class TestMDBBESentry:
    """Tests for MDBBESentry bloat auditing."""

    def test_sentry_audit_and_optimize(self) -> None:
        sentry = MDBBESentry()
        instances = [
            GenericInstance(
                symbol_name=f"sort_fn_{i}",
                arg_abis=[ABITypeDescriptor("pointer", 8, 8)],
                ret_abi=ABITypeDescriptor("int", 4, 4),
                code_size_bytes=500,
            )
            for i in range(5)
        ]

        report = sentry.audit_and_optimize(instances)
        assert report.total_generic_instances == 5
        assert report.unique_abi_clusters == 1
        assert report.bytes_saved > 1500
        assert report.reduction_percentage >= 70.0

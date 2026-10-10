"""Unit tests for EV-IPP Sentry."""

import pytest

try:
    from fault_keeper.systems.kernel_ev_ipp.config import EVIPPConfig
    from fault_keeper.systems.kernel_ev_ipp.sentry import EVIPPSentry
except ImportError:
    from kernel_ev_ipp.config import EVIPPConfig
    from kernel_ev_ipp.sentry import EVIPPSentry


class TestEVIPPSentry:
    """Tests for EVIPPSentry program auditing."""

    def test_safe_program_verification(self) -> None:
        sentry = EVIPPSentry()
        instructions = [
            ("mov", 2, 10),
            ("add_imm", 2, 20),
            ("load_stack", 10, 4),
        ]
        cert = sentry.audit_program("test_prog_safe", instructions)
        assert cert.is_safe is True
        assert cert.total_instructions == 3
        assert len(sentry.certificates) == 1

    def test_out_of_bounds_stack_program_rejection(self) -> None:
        sentry = EVIPPSentry()
        instructions = [
            ("load_stack", 10, 600),  # 600 exceeds 512!
        ]
        cert = sentry.audit_program("test_prog_oob", instructions)
        assert cert.is_safe is False
        assert "Stack out of bounds" in str(cert.rejection_reason)

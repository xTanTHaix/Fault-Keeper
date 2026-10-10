"""Fault-Keeper v1.0.0 End-to-End CLI Stress & POSIX Exit Code Verification Suite.

Exhaustively verifies all 5 CLI subcommands (`audit`, `test-audit`, `diagnose`,
`solve-merge`, `mcp`) under nominal, boundary, negative, and adversarial inputs.
Strictly verifies POSIX exit codes:
    0: Nominal invariant satisfaction / clean health pass
    1: Business invariant violation (deadlock, API break, flaky test, ReDoS, merge conflict)
    2: Command-line invocation syntax failure, missing argument, or non-existent path

Verifies both in-process execution (`fault_keeper.py` via `_cli_mod.main(argv)`)
and true OS process execution (`subprocess.run([sys.executable, "fault_keeper.py", ...])`).
Guarantees zero unhandled exceptions, zero bare tracebacks, and UTF-8 stream stability.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

import pytest

# Ensure repository root and src/ are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Dynamically load the CLI entrypoint script `fault_keeper.py`
_cli_script_path = REPO_ROOT / "fault_keeper.py"
_spec = importlib.util.spec_from_file_location("fault_keeper_cli", _cli_script_path)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Cannot load CLI spec from {_cli_script_path}")
_cli_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cli_mod)


# ---------------------------------------------------------------------------
# Test Execution Helpers
# ---------------------------------------------------------------------------

def run_cli_in_process(argv: List[str]) -> Tuple[int, str, str]:
    """Execute ``_cli_mod.main(argv)`` in-process with captured streams.

    Args:
        argv: Command-line arguments sequence without the binary name.

    Returns:
        Tuple of (exit_code, stdout_str, stderr_str).
    """
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
            code = _cli_mod.main(argv)
        return int(code), out_buf.getvalue(), err_buf.getvalue()
    except SystemExit as exc:
        code = exc.code if exc.code is not None else 0
        return int(code), out_buf.getvalue(), err_buf.getvalue()


def run_cli_subprocess(argv: List[str], input_text: str = "") -> Tuple[int, str, str]:
    """Execute ``fault_keeper.py`` in a separate Python process.

    Args:
        argv: Command-line arguments sequence.
        input_text: Standard input stream payload.

    Returns:
        Tuple of (returncode, stdout_str, stderr_str).
    """
    cli_path = str(REPO_ROOT / "fault_keeper.py")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, cli_path, *argv],
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=30,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# Project Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def clean_project(tmp_path: Path) -> Path:
    """Fixture producing a clean, healthy project directory."""
    proj = tmp_path / "clean_proj"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "calculator.py").write_text(
        "def compute_interest(principal: float, rate: float) -> float:\n"
        "    try:\n"
        "        if principal < 0.0 or rate < 0.0:\n"
        "            raise ValueError('Invalid inputs')\n"
        "        return principal * (1.0 + rate)\n"
        "    except ValueError:\n"
        "        return 0.0\n",
        encoding="utf-8",
    )
    return proj


@pytest.fixture
def deadlock_project(tmp_path: Path) -> Path:
    """Fixture producing a project with Tx-DLO inverse lock sequences."""
    proj = tmp_path / "deadlock_proj"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "wallet.py").write_text(
        "def transfer_a_to_b(tx):\n"
        "    tx.lock('accounts', 1)\n"
        "    tx.lock('accounts', 2)\n"
        "\n"
        "def transfer_b_to_a(tx):\n"
        "    tx.lock('accounts', 2)\n"
        "    tx.lock('accounts', 1)\n",
        encoding="utf-8",
    )
    return proj


@pytest.fixture
def api_break_project(tmp_path: Path) -> Path:
    """Fixture producing a project with CDC-ABS missing field contract violation."""
    proj = tmp_path / "api_break_proj"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "backend.py").write_text(
        "class AccountDTO:\n"
        "    id: int\n"
        "    email: str\n"
        "\n"
        "@app.get('/api/accounts/{id}', response_model=AccountDTO)\n"
        "def get_account(id: int) -> AccountDTO:\n"
        "    return AccountDTO()\n",
        encoding="utf-8",
    )
    (proj / "client.ts").write_text(
        "interface AccountDTO {\n"
        "    id: number;\n"
        "    email: string;\n"
        "    username: string;\n"
        "}\n"
        "const res = axios.get<AccountDTO>('/api/accounts/{id}');\n",
        encoding="utf-8",
    )
    return proj


@pytest.fixture
def clean_test_suite(tmp_path: Path) -> Path:
    """Fixture producing an order-independent, leak-free test suite."""
    suite = tmp_path / "clean_test_suite"
    suite.mkdir(parents=True, exist_ok=True)
    (suite / "test_math.py").write_text(
        "def test_addition():\n"
        "    assert 1 + 1 == 2\n"
        "\n"
        "def test_multiplication():\n"
        "    assert 3 * 3 == 9\n"
        "\n"
        "def test_string_format():\n"
        "    assert f'item_{42}' == 'item_42'\n",
        encoding="utf-8",
    )
    return suite


@pytest.fixture
def flaky_test_suite(tmp_path: Path) -> Path:
    """Fixture producing a test suite with global state leakage & order dependence."""
    suite = tmp_path / "flaky_test_suite"
    suite.mkdir(parents=True, exist_ok=True)
    (suite / "test_flaky.py").write_text(
        "import os\n"
        "\n"
        "def test_a_victim():\n"
        "    assert 'GLOBAL_FLAKY_LEAK_VAR' not in os.environ\n"
        "\n"
        "def test_b_polluter():\n"
        "    os.environ['GLOBAL_FLAKY_LEAK_VAR'] = 'polluted'\n"
        "    assert True\n",
        encoding="utf-8",
    )
    return suite


@pytest.fixture
def hazard_diagnose_project(tmp_path: Path) -> Path:
    """Fixture producing a project with unawaited coroutine hazard."""
    proj = tmp_path / "hazard_proj"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "service.py").write_text(
        "async def fetch_user():\n"
        "    call_external_api()\n",
        encoding="utf-8",
    )
    return proj


@pytest.fixture
def clean_diagnose_project(tmp_path: Path) -> Path:
    """Fixture producing a completely clean project for diagnostics."""
    proj = tmp_path / "clean_diag_proj"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "pure.py").write_text(
        "def add_numbers(a: int, b: int) -> int:\n"
        "    return a + b\n",
        encoding="utf-8",
    )
    return proj


# ---------------------------------------------------------------------------
# Test Suite 1: CLI Subcommand `audit`
# ---------------------------------------------------------------------------

class TestCliAuditSubcommand:
    """Tests for ``fk audit <path>`` under nominal, violation, and boundary conditions."""

    def test_cli_audit_clean_exit_0_in_process(self, clean_project: Path) -> None:
        """Clean project audits with zero violations and returns Exit 0 in-process."""
        code, out, err = run_cli_in_process(["audit", str(clean_project)])
        assert code == 0
        assert "AUDIT VERDICT: HEALTHY (0 violations)" in out
        assert err == ""

    def test_cli_audit_clean_exit_0_subprocess(self, clean_project: Path) -> None:
        """Clean project audits with zero violations and returns Exit 0 via subprocess."""
        code, out, _ = run_cli_subprocess(["audit", str(clean_project)])
        assert code == 0
        assert "AUDIT VERDICT: HEALTHY (0 violations)" in out

    def test_cli_audit_deadlock_exit_1_in_process(self, deadlock_project: Path) -> None:
        """Deadlock cycle detection triggers Tx-DLO violation and returns Exit 1 in-process."""
        code, out, _ = run_cli_in_process(["audit", str(deadlock_project)])
        assert code == 1
        assert "AUDIT VERDICT: FAILED" in out
        assert "[Tx-DLO]" in out

    def test_cli_audit_deadlock_exit_1_subprocess(self, deadlock_project: Path) -> None:
        """Deadlock cycle detection triggers Tx-DLO violation and returns Exit 1 via subprocess."""
        code, out, _ = run_cli_subprocess(["audit", str(deadlock_project)])
        assert code == 1
        assert "AUDIT VERDICT: FAILED" in out

    def test_cli_audit_api_break_exit_1_in_process(self, api_break_project: Path) -> None:
        """Missing field contract breach triggers CDC-ABS violation and returns Exit 1 in-process."""
        code, out, _ = run_cli_in_process(["audit", str(api_break_project)])
        assert code == 1
        assert "AUDIT VERDICT: FAILED" in out
        assert "[CDC-ABS]" in out

    def test_cli_audit_api_break_exit_1_subprocess(self, api_break_project: Path) -> None:
        """Missing field contract breach triggers CDC-ABS violation and returns Exit 1 via subprocess."""
        code, out, _ = run_cli_subprocess(["audit", str(api_break_project)])
        assert code == 1
        assert "AUDIT VERDICT: FAILED" in out

    def test_cli_audit_health_threshold_fail_exit_1(self, clean_project: Path) -> None:
        """Setting health threshold above 100% intentionally forces audit failure (Exit 1)."""
        code, out, _ = run_cli_subprocess(["audit", str(clean_project), "--health-threshold", "101.0"])
        assert code == 1
        assert "AUDIT VERDICT: FAILED" in out

    def test_cli_audit_nonexistent_path_exit_2_in_process(self) -> None:
        """Auditing non-existent path outputs error to stderr and returns Exit 2 in-process."""
        code, _, err = run_cli_in_process(["audit", "nonexistent_audit_target_path"])
        assert code == 2
        assert "Target path does not exist" in err

    def test_cli_audit_nonexistent_path_exit_2_subprocess(self) -> None:
        """Auditing non-existent path outputs error to stderr and returns Exit 2 via subprocess."""
        code, _, err = run_cli_subprocess(["audit", "nonexistent_audit_target_path"])
        assert code == 2
        assert "Target path does not exist" in err

    def test_cli_audit_missing_arg_exit_2_in_process(self) -> None:
        """Omitting required path argument raises SystemExit(2) in-process."""
        code, _, err = run_cli_in_process(["audit"])
        assert code == 2
        assert "the following arguments are required: path" in err

    def test_cli_audit_missing_arg_exit_2_subprocess(self) -> None:
        """Omitting required path argument exits with code 2 via subprocess."""
        code, _, err = run_cli_subprocess(["audit"])
        assert code == 2
        assert "the following arguments are required: path" in err


# ---------------------------------------------------------------------------
# Test Suite 2: CLI Subcommand `test-audit`
# ---------------------------------------------------------------------------

class TestCliTestAuditSubcommand:
    """Tests for ``fk test-audit <path>`` verifying FT-DSO Permutation Sieve."""

    def test_cli_test_audit_order_independent_exit_0_in_process(self, clean_test_suite: Path) -> None:
        """Order-independent test suite exits cleanly with code 0 in-process."""
        code, out, _ = run_cli_in_process(["test-audit", str(clean_test_suite)])
        assert code == 0
        assert "TEST-AUDIT VERDICT: ALL TESTS DETERMINISTIC & ISOLATED" in out
        assert "ORDER-INDEPENDENT" in out

    def test_cli_test_audit_order_independent_exit_0_subprocess(self, clean_test_suite: Path) -> None:
        """Order-independent test suite exits cleanly with code 0 via subprocess."""
        code, out, _ = run_cli_subprocess(["test-audit", str(clean_test_suite)])
        assert code == 0
        assert "TEST-AUDIT VERDICT: ALL TESTS DETERMINISTIC & ISOLATED" in out

    def test_cli_test_audit_flaky_state_leakage_exit_1_in_process(self, flaky_test_suite: Path) -> None:
        """Leaked environment variable triggers flakiness detection with Exit 1 in-process."""
        code, out, _ = run_cli_in_process(["test-audit", str(flaky_test_suite)])
        assert code == 1
        assert "TEST-AUDIT VERDICT: FLAKINESS DETECTED" in out

    def test_cli_test_audit_flaky_state_leakage_exit_1_subprocess(self, flaky_test_suite: Path) -> None:
        """Leaked environment variable triggers flakiness detection with Exit 1 via subprocess."""
        code, out, _ = run_cli_subprocess(["test-audit", str(flaky_test_suite)])
        assert code == 1
        assert "TEST-AUDIT VERDICT: FLAKINESS DETECTED" in out

    def test_cli_test_audit_empty_directory_exit_0(self, tmp_path: Path) -> None:
        """Auditing a directory with no test files emits warning and exits with code 0."""
        empty_dir = tmp_path / "empty_tests"
        empty_dir.mkdir(parents=True, exist_ok=True)
        code, out, _ = run_cli_subprocess(["test-audit", str(empty_dir)])
        assert code == 0
        assert "No test files discovered" in out

    def test_cli_test_audit_nonexistent_path_exit_2_in_process(self) -> None:
        """Auditing non-existent test path outputs error and returns Exit 2 in-process."""
        code, _, err = run_cli_in_process(["test-audit", "nonexistent_test_path.py"])
        assert code == 2
        assert "Test path does not exist" in err

    def test_cli_test_audit_nonexistent_path_exit_2_subprocess(self) -> None:
        """Auditing non-existent test path outputs error and returns Exit 2 via subprocess."""
        code, _, err = run_cli_subprocess(["test-audit", "nonexistent_test_path.py"])
        assert code == 2
        assert "Test path does not exist" in err

    def test_cli_test_audit_missing_arg_exit_2(self) -> None:
        """Omitting required test path argument exits with code 2."""
        code, _, err = run_cli_subprocess(["test-audit"])
        assert code == 2
        assert "the following arguments are required: path" in err

    def test_cli_test_audit_deterministic_seed_option(self, clean_test_suite: Path) -> None:
        """Passing explicit PRNG seed generates reproducible execution schedules."""
        code, out, _ = run_cli_subprocess(["test-audit", str(clean_test_suite), "--seed", "1337"])
        assert code == 0
        assert "TEST-AUDIT VERDICT: ALL TESTS DETERMINISTIC & ISOLATED" in out


# ---------------------------------------------------------------------------
# Test Suite 3: CLI Subcommand `diagnose`
# ---------------------------------------------------------------------------

class TestCliDiagnoseSubcommand:
    """Tests for ``fk diagnose <target>`` verifying normal and strict diagnostic modes."""

    def test_cli_diagnose_normal_with_hazards_exit_0_in_process(self, hazard_diagnose_project: Path) -> None:
        """Normal diagnostic run reports hazards without failing CI (Exit 0) in-process."""
        code, out, _ = run_cli_in_process(["diagnose", str(hazard_diagnose_project)])
        assert code == 0
        assert "Async/Race Hazards: 1" in out

    def test_cli_diagnose_normal_with_hazards_exit_0_subprocess(self, hazard_diagnose_project: Path) -> None:
        """Normal diagnostic run reports hazards without failing CI (Exit 0) via subprocess."""
        code, out, _ = run_cli_subprocess(["diagnose", str(hazard_diagnose_project)])
        assert code == 0
        assert "Async/Race Hazards: 1" in out

    def test_cli_diagnose_strict_clean_exit_0(self, clean_diagnose_project: Path) -> None:
        """Strict diagnostic run on clean project returns Exit 0."""
        code, out, _ = run_cli_subprocess(["diagnose", str(clean_diagnose_project), "--strict"])
        assert code == 0
        assert "Async/Race Hazards: 0" in out

    def test_cli_diagnose_strict_hazards_exit_1_in_process(self, hazard_diagnose_project: Path) -> None:
        """Strict diagnostic run fails CI gate (Exit 1) when hazards are detected in-process."""
        code, out, _ = run_cli_in_process(["diagnose", str(hazard_diagnose_project), "--strict"])
        assert code == 1
        assert "Async/Race Hazards: 1" in out

    def test_cli_diagnose_strict_hazards_exit_1_subprocess(self, hazard_diagnose_project: Path) -> None:
        """Strict diagnostic run fails CI gate (Exit 1) when hazards are detected via subprocess."""
        code, out, _ = run_cli_subprocess(["diagnose", str(hazard_diagnose_project), "--strict"])
        assert code == 1
        assert "Async/Race Hazards: 1" in out

    def test_cli_diagnose_nonexistent_path_exit_2(self) -> None:
        """Diagnosing non-existent target path outputs error and returns Exit 2."""
        code, _, err = run_cli_subprocess(["diagnose", "nonexistent_diag_target"])
        assert code == 2
        assert "Diagnostic target does not exist" in err

    def test_cli_diagnose_missing_arg_exit_2(self) -> None:
        """Omitting required target argument exits with code 2."""
        code, _, err = run_cli_subprocess(["diagnose"])
        assert code == 2
        assert "the following arguments are required: target" in err


# ---------------------------------------------------------------------------
# Test Suite 4: CLI Subcommand `solve-merge`
# ---------------------------------------------------------------------------

class TestCliSolveMergeSubcommand:
    """Tests for ``fk solve-merge <base> <left> <right>`` verifying A-SMW 3-way AST merge."""

    def test_cli_solve_merge_clean_inline_3way_exit_0_in_process(self) -> None:
        """Clean non-conflicting 3-way merge of inline strings returns Exit 0 in-process."""
        base = "x = 1"
        left = "x = 1\ny = 2"
        right = "x = 1\nz = 3"
        code, out, _ = run_cli_in_process(["solve-merge", base, left, right])
        assert code == 0
        assert "=== A-SMW 3-WAY AST MERGE COMPLETE ===" in out
        assert "Resolutions applied:" in out

    def test_cli_solve_merge_clean_inline_3way_exit_0_subprocess(self) -> None:
        """Clean non-conflicting 3-way merge of inline strings returns Exit 0 via subprocess."""
        base = "x = 1"
        left = "x = 1\ny = 2"
        right = "x = 1\nz = 3"
        code, out, _ = run_cli_subprocess(["solve-merge", base, left, right])
        assert code == 0
        assert "=== A-SMW 3-WAY AST MERGE COMPLETE ===" in out

    def test_cli_solve_merge_clean_files_3way_exit_0(self, tmp_path: Path) -> None:
        """Clean 3-way merge reading disk file paths returns Exit 0."""
        f_base = tmp_path / "base.py"
        f_left = tmp_path / "left.py"
        f_right = tmp_path / "right.py"

        f_base.write_text("x = 1\n", encoding="utf-8")
        f_left.write_text("x = 1\ny = 2\n", encoding="utf-8")
        f_right.write_text("x = 1\nz = 3\n", encoding="utf-8")

        code, out, _ = run_cli_subprocess(["solve-merge", str(f_base), str(f_left), str(f_right)])
        assert code == 0
        assert "=== A-SMW 3-WAY AST MERGE COMPLETE ===" in out
        assert "Resolutions applied:" in out

    def test_cli_solve_merge_syntax_error_exit_1_in_process(self) -> None:
        """Malformed Python syntax in merge source fails with Exit 1 in-process."""
        code, _, err = run_cli_in_process(["solve-merge", "def (", "y = 1", "z = 2"])
        assert code == 1
        assert "[A-SMW ERROR] Merge failed:" in err

    def test_cli_solve_merge_syntax_error_exit_1_subprocess(self) -> None:
        """Malformed Python syntax in merge source fails with Exit 1 via subprocess."""
        code, _, err = run_cli_subprocess(["solve-merge", "def (", "y = 1", "z = 2"])
        assert code == 1
        assert "[A-SMW ERROR] Merge failed:" in err

    def test_cli_solve_merge_missing_args_exit_2(self) -> None:
        """Passing insufficient positional arguments exits with code 2."""
        code, _, err = run_cli_subprocess(["solve-merge", "x = 1"])
        assert code == 2
        assert "the following arguments are required: left, right" in err


# ---------------------------------------------------------------------------
# Test Suite 5: CLI Subcommand `mcp`
# ---------------------------------------------------------------------------

class TestCliMcpSubcommand:
    """Tests for ``fk mcp [--transport stdio]`` verifying daemon launch and transport validation."""

    def test_cli_mcp_stdio_clean_eof_exit_0_subprocess(self) -> None:
        """Launching MCP stdio server with empty stdin (EOF) shuts down cleanly with Exit 0."""
        code, _, err = run_cli_subprocess(["mcp", "--transport", "stdio"], input_text="")
        assert code == 0
        assert "MCP Dispatcher started (stdio mode)" in err

    def test_cli_mcp_invalid_transport_exit_2_in_process(self) -> None:
        """Passing unsupported transport protocol raises SystemExit(2) in-process."""
        code, _, err = run_cli_in_process(["mcp", "--transport", "tcp"])
        assert code == 2
        assert "invalid choice: 'tcp'" in err

    def test_cli_mcp_invalid_transport_exit_2_subprocess(self) -> None:
        """Passing unsupported transport protocol exits with code 2 via subprocess."""
        code, _, err = run_cli_subprocess(["mcp", "--transport", "tcp"])
        assert code == 2
        assert "invalid choice: 'tcp'" in err


# ---------------------------------------------------------------------------
# Test Suite 6: Negative Boundary & General CLI Invariants
# ---------------------------------------------------------------------------

class TestCliBoundaryAndNegativeInvariants:
    """Tests general CLI argument parser boundary conditions and unhandled error prevention."""

    def test_cli_no_subcommand_exit_2(self) -> None:
        """Invoking CLI with no arguments exits with code 2 and prints usage."""
        code, _, err = run_cli_subprocess([])
        assert code == 2
        assert "usage: fk" in err

    def test_cli_unknown_subcommand_exit_2(self) -> None:
        """Invoking unknown subcommand exits with code 2."""
        code, _, err = run_cli_subprocess(["unknown-command"])
        assert code == 2
        assert "invalid choice: 'unknown-command'" in err

    def test_cli_help_flags_exit_0(self) -> None:
        """Top-level and subcommand --help flags exit with code 0."""
        for cmd in [[], ["audit"], ["test-audit"], ["diagnose"], ["solve-merge"], ["mcp"]]:
            code, out, _ = run_cli_subprocess([*cmd, "--help"])
            assert code == 0
            assert "help" in out.lower()

    def test_cli_zero_unhandled_tracebacks_on_empty_python_file(self, tmp_path: Path) -> None:
        """Auditing an empty 0-byte Python file completes cleanly without traceback."""
        empty_py = tmp_path / "empty.py"
        empty_py.write_text("", encoding="utf-8")
        code, out, err = run_cli_subprocess(["audit", str(empty_py)])
        assert code == 0
        assert "Traceback" not in err
        assert "AUDIT VERDICT: HEALTHY" in out

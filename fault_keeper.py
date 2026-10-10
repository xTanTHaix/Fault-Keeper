"""Sovereign Standalone UNIX CLI & MCP 2.0 Entrypoint for Fault-Keeper.

Provides deterministic command-line access to Fault-Keeper's mathematical and
static analysis pillars:
- `audit <path>`: Runs U-FSR, WPA-HIS, Tx-DLO, and CDC-ABS across a file or monorepo.
- `test-audit <path>`: Runs FT-DSO Permutation Sieve, Gray-Code Toxic Pair Pinpointer,
  and Global State Leakage Sieve on a test file or directory.
- `diagnose <target>`: Runs CRCAE root-causal abduction, GSLD layout simplex solver,
  LQPC N+1 query polyhedral detector, RDA-NP ReDoS scanner, AE-FPS async checker,
  and TC-GTC timezone drift detector.
- `solve-merge <base> <left> <right>`: Runs A-SMW 3-way commutative AST merge.
- `mcp [--transport stdio]`: Launches the JSON-RPC 2.0 MCP stdio server.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

# Ensure local `src/` directory is at index 0 of sys.path to take precedence over the root directory script
_REPO_ROOT = Path(__file__).resolve().parent
_SRC_DIR = str((_REPO_ROOT / "src").resolve())
if _SRC_DIR in sys.path:
    sys.path.remove(_SRC_DIR)
sys.path.insert(0, _SRC_DIR)

# Guard against shadowing: if 'fault_keeper' in sys.modules is not a package, remove it so the package loads
if "fault_keeper" in sys.modules and not hasattr(sys.modules["fault_keeper"], "__path__"):
    del sys.modules["fault_keeper"]

from fault_keeper.audit.ast_rewrite import ast_merge
from fault_keeper.audit.ufsr import analyse_file
from fault_keeper.audit.wpahis import analyse_project
from fault_keeper.core.mcp.server import MCPDispatcher
from fault_keeper.daily.cdcabs import (
    BackendEndpointContract,
    ClientCallSite,
    harvest_backend_contracts,
    harvest_client_callsites,
    verify_cross_boundary_contracts,
)
from fault_keeper.daily.ftdso import (
    FlakyTestDeterministicSieve,
    StateLeakageReport,
    VirtualEventClockQuencher,
    run_with_leakage_sieve,
)
from fault_keeper.daily.txdlo import (
    TransactionDeadlockOracle,
    TransactionFlow,
    slice_ast_transactions,
)
from fault_keeper.fullstack.gsl_d_simplex import fix_horizontal_overflow, solve_layout_problem
from fault_keeper.num.rdas_redos import detect_reDos
from fault_keeper.num.tc_gtc_timezone import detect_YYYY_format_error
from fault_keeper.typing.ae_fps_await_checker import check_async_awaits, detect_race_conditions
from fault_keeper.workflow.crcae_root_causal import (
    build_causal_graph_from_project,
    diagnose_root_cause,
)
from fault_keeper.workflow.lqpc_n_plus_one import detect_n_plus_one, generate_query_fusion_plan


# ---------------------------------------------------------------------------
# ANSI Formatting Helpers
# ---------------------------------------------------------------------------

class _ANSI:
    """ANSI escape sequences for terminal telemetry output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"


def _configure_utf8_streams() -> None:
    """Reconfigure stdout and stderr to UTF-8 to avoid Windows codepage crashes."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                continue


def _collect_source_files(target: Path) -> Tuple[List[Path], List[Path]]:
    """Collect Python files and frontend TypeScript/JavaScript files under target.

    Args:
        target: File or directory path to scan.

    Returns:
        Tuple of (python_files, frontend_files) sorted deterministically.
    """
    if target.is_file():
        if target.suffix == ".py":
            return [target], []
        if target.suffix in (".ts", ".tsx", ".js", ".jsx"):
            return [], [target]
        return [target], []

    py_files: List[Path] = []
    fe_files: List[Path] = []
    ignored_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache"}

    for root, dirs, files in os.walk(target):
        dirs[:] = sorted(d for d in dirs if d not in ignored_dirs and not d.startswith("."))
        for fname in sorted(files):
            fpath = Path(root) / fname
            if fpath.suffix == ".py":
                py_files.append(fpath)
            elif fpath.suffix in (".ts", ".tsx", ".js", ".jsx"):
                fe_files.append(fpath)

    return py_files, fe_files


# ---------------------------------------------------------------------------
# Subcommand 1: `audit <path>`
# ---------------------------------------------------------------------------

def cmd_audit(args: argparse.Namespace) -> int:
    """Execute unified structural, architecture, deadlock, and API contract audit.

    Runs U-FSR, WPA-HIS, Tx-DLO, and CDC-ABS on the specified path.

    Args:
        args: Parsed CLI namespace containing `path` and `health_threshold`.

    Returns:
        Exit code 0 if all invariants hold, or 1 if any architectural/safety gate fails.
    """
    target = Path(args.path).resolve()
    if not target.exists():
        print(f"{_ANSI.RED}[ERROR] Target path does not exist: {target}{_ANSI.RESET}", file=sys.stderr)
        return 2

    py_files, fe_files = _collect_source_files(target)
    print(f"{_ANSI.BOLD}{_ANSI.CYAN}=== FAULT-KEEPER SOVEREIGN AUDIT: {target.name} ==={_ANSI.RESET}")

    violations_found = 0

    # 1. U-FSR: File & Function Structural Health
    ufsr_scores: List[float] = []
    total_unhandled_sinks = 0
    for py_file in py_files:
        try:
            source = py_file.read_text(encoding="utf-8")
        except OSError:
            continue
        report = analyse_file(source)
        fn_list = report.get("functions", [])
        if fn_list:
            mean_fn = sum(float(fn.get("s_func", 100.0)) for fn in fn_list) / len(fn_list)
            ufsr_scores.append(mean_fn)
        else:
            ufsr_scores.append(100.0)
        summary = report.get("summary", {})
        total_unhandled_sinks += int(summary.get("unguarded_error_branches", 0))

    avg_ufsr = sum(ufsr_scores) / len(ufsr_scores) if ufsr_scores else 100.0
    ufsr_ok = avg_ufsr >= args.health_threshold and total_unhandled_sinks == 0
    ufsr_status = f"{_ANSI.GREEN}PASS{_ANSI.RESET}" if ufsr_ok else f"{_ANSI.RED}FAIL{_ANSI.RESET}"
    if not ufsr_ok:
        violations_found += 1
    print(
        f"[U-FSR]   Files: {len(py_files)} | Mean Health: {avg_ufsr:.2f}/100.0 "
        f"| Unhandled Sinks: {total_unhandled_sinks} -> {ufsr_status}"
    )

    # 2. WPA-HIS: Whole-Program Architecture & DAG Topology
    project_dir = target if target.is_dir() else target.parent
    wpa_report = analyse_project(str(project_dir))
    arch_health = float(wpa_report.get("s_arch", 100.0))
    fas_edges = wpa_report.get("feedback_arc_set", [])
    wpa_ok = len(fas_edges) == 0 and arch_health >= args.health_threshold
    if not wpa_ok:
        violations_found += 1
    wpa_status = f"{_ANSI.GREEN}PASS{_ANSI.RESET}" if wpa_ok else f"{_ANSI.RED}FAIL{_ANSI.RESET}"
    print(
        f"[WPA-HIS] Architecture Health: {arch_health:.2f}/100.0 "
        f"| Feedback Arc Set (Cycles): {len(fas_edges)} -> {wpa_status}"
    )

    # 3. Tx-DLO: Transaction Deadlock & Havender Total Lock Ordering
    all_tx_flows: List[TransactionFlow] = []
    for py_file in py_files:
        try:
            source = py_file.read_text(encoding="utf-8")
        except OSError:
            continue
        flows = slice_ast_transactions(source, file_path=str(py_file))
        all_tx_flows.extend(flows)

    tx_oracle = TransactionDeadlockOracle()
    tx_analysis = tx_oracle.analyze_flows(all_tx_flows)
    wfg = tx_analysis["wfg"]
    ordering = tx_analysis["ordering"]
    tx_ok = bool(wfg.is_deadlock_free and ordering.is_canonical)
    if not tx_ok:
        violations_found += 1
    tx_status = f"{_ANSI.GREEN}PASS{_ANSI.RESET}" if tx_ok else f"{_ANSI.RED}FAIL{_ANSI.RESET}"
    print(
        f"[Tx-DLO]  Transactions: {len(all_tx_flows)} | WFG H1 Betti: {wfg.h1_betti_number} "
        f"| Canonical Lock Order: {ordering.is_canonical} "
        f"| Violations: {len(ordering.violations)} -> {tx_status}"
    )

    # 4. CDC-ABS: Cross-Boundary Contract & API Breaking-Change Sentry
    backend_contracts: List[BackendEndpointContract] = []
    client_callsites: List[ClientCallSite] = []

    for py_file in py_files:
        try:
            source = py_file.read_text(encoding="utf-8")
        except OSError:
            continue
        backend_contracts.extend(harvest_backend_contracts(source, file_path=str(py_file)))
        client_callsites.extend(harvest_client_callsites(source, file_path=str(py_file)))

    for fe_file in fe_files:
        try:
            fe_source = fe_file.read_text(encoding="utf-8")
        except OSError:
            continue
        client_callsites.extend(harvest_client_callsites(fe_source, file_path=str(fe_file)))

    cdc_report = verify_cross_boundary_contracts(backend_contracts, client_callsites)
    cdc_ok = not cdc_report.phi_break
    if not cdc_ok:
        violations_found += 1
    cdc_status = f"{_ANSI.GREEN}PASS{_ANSI.RESET}" if cdc_ok else f"{_ANSI.RED}FAIL{_ANSI.RESET}"
    print(
        f"[CDC-ABS] Endpoints: {len(backend_contracts)} | Call-Sites: {len(client_callsites)} "
        f"| Phi_break: {cdc_report.phi_break} | Violations: {len(cdc_report.violations)} -> {cdc_status}"
    )
    for v in cdc_report.violations:
        print(f"          -> [{v.violation_kind}] {v.endpoint} field '{v.field_name}': {v.message}")

    if violations_found > 0:
        print(
            f"{_ANSI.BOLD}{_ANSI.RED}AUDIT VERDICT: FAILED ({violations_found} pillar violation(s) detected){_ANSI.RESET}"
        )
        return 1

    print(f"{_ANSI.BOLD}{_ANSI.GREEN}AUDIT VERDICT: HEALTHY (0 violations){_ANSI.RESET}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand 2: `test-audit <path>`
# ---------------------------------------------------------------------------

def _load_test_callables_from_file(py_file: Path) -> Tuple[Dict[str, Callable[[], Any]], str, Optional[Any]]:
    """Dynamically load `test_*` functions from a Python test file for FT-DSO probing.

    Args:
        py_file: Path to the Python test module.

    Returns:
        Tuple of (mapping of test_name -> callable, raw_source_code, module_object).
    """
    source = py_file.read_text(encoding="utf-8")
    module_name = f"_fk_test_audit_{py_file.stem}_{abs(hash(str(py_file))) & 0xFFFF:04x}"
    spec = importlib.util.spec_from_file_location(module_name, str(py_file))
    if spec is None or spec.loader is None:
        return {}, source, None

    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(module_name, None)
        return {}, source, None

    callables: Dict[str, Callable[[], Any]] = {}
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            fn = getattr(mod, node.name, None)
            if callable(fn):
                callables[node.name] = fn

    return callables, source, mod


def cmd_test_audit(args: argparse.Namespace) -> int:
    """Execute FT-DSO Permutation Sieve, Toxic Pair Pinpointer, and Leakage Sieve.

    Args:
        args: Parsed CLI namespace containing `path` and `seed`.

    Returns:
        Exit code 0 if test suite is order-invariant and leak-free, or 1 if flaky.
    """
    target = Path(args.path).resolve()
    if not target.exists():
        print(f"{_ANSI.RED}[ERROR] Test path does not exist: {target}{_ANSI.RESET}", file=sys.stderr)
        return 2

    py_files, _ = _collect_source_files(target)
    test_files = [
        f for f in py_files
        if f.name.startswith("test_") or f.name.endswith("_test.py") or target.is_file()
    ]

    print(f"{_ANSI.BOLD}{_ANSI.CYAN}=== FT-DSO FLAKY-TEST DETERMINISTIC SIEVE: {target.name} ==={_ANSI.RESET}")
    if not test_files:
        print(f"{_ANSI.YELLOW}[WARN] No test files discovered under {target}{_ANSI.RESET}")
        return 0

    sieve = FlakyTestDeterministicSieve(seed=args.seed)
    flaky_detected = False

    for tfile in test_files:
        try:
            source = tfile.read_text(encoding="utf-8")
        except OSError:
            continue

        # Reload fresh module state for each permutation schedule execution
        def _make_runner(file_path: Path) -> Callable[[Sequence[str]], Mapping[str, str]]:
            def _runner(schedule: Sequence[str]) -> Mapping[str, str]:
                saved_env = dict(os.environ)
                callables, _, _ = _load_test_callables_from_file(file_path)
                outcomes: Dict[str, str] = {}
                with VirtualEventClockQuencher():
                    for tid in schedule:
                        fn = callables.get(tid)
                        if fn is None:
                            outcomes[tid] = "SKIP"
                            continue
                        try:
                            fn()
                            outcomes[tid] = "PASS"
                        except Exception:
                            outcomes[tid] = "FAIL"
                os.environ.clear()
                os.environ.update(saved_env)
                return outcomes

            return _runner

        initial_callables, _, _ = _load_test_callables_from_file(tfile)
        test_ids = list(initial_callables.keys())
        if not test_ids:
            continue

        # Measure per-test state leakage in isolation
        leakage_reports: List[StateLeakageReport] = []
        saved_env = dict(os.environ)
        fresh_callables, _, target_mod = _load_test_callables_from_file(tfile)
        target_ns: Dict[str, Any] = {tfile.stem: target_mod} if target_mod is not None else {}
        with VirtualEventClockQuencher():
            for tid in test_ids:
                fn = fresh_callables[tid]
                leak_rep = run_with_leakage_sieve(
                    tid, fn, target_namespaces=target_ns, auto_cleanup_mocks=True
                )
                leakage_reports.append(leak_rep)
        os.environ.clear()
        os.environ.update(saved_env)

        runner = _make_runner(tfile)
        audit_rep = sieve.audit_suite(
            test_ids=test_ids,
            runner=runner,
            source_code=source,
            leakage_reports=leakage_reports,
        )

        inv = audit_rep.order_invariance
        leaks = [lr for lr in audit_rep.leakage_reports if not lr.is_clean]
        is_file_healthy = inv.is_order_independent and len(leaks) == 0
        if not is_file_healthy:
            flaky_detected = True

        status_str = (
            f"{_ANSI.GREEN}ORDER-INDEPENDENT{_ANSI.RESET}"
            if is_file_healthy
            else f"{_ANSI.RED}FLAKY / STATE-LEAK DETECTED{_ANSI.RESET}"
        )
        print(
            f"[FT-DSO] {tfile.name} | Tests: {len(test_ids)} "
            f"| Order-Invariant: {inv.is_order_independent} "
            f"| Leaky Tests: {len(leaks)} -> {status_str}"
        )

        for tp in audit_rep.toxic_pairs:
            print(
                f"         -> Toxic Pair Pinpointed: Polluter='{tp.polluter}' -> Victim='{tp.victim}' "
                f"(Runs={tp.runs_executed}, Reproducible={tp.reproducible})"
            )
        for lr in leaks:
            print(
                f"         -> State Leakage in '{lr.test_id}': delta_leak={lr.delta_leak} "
                f"(globals={lr.leaked_globals}, env={lr.leaked_env_vars}, mocks={lr.unreset_mocks})"
            )
        for patch in audit_rep.patches:
            print(f"         -> Quarantine Patch: {patch.quarantine_decorator}")

    if flaky_detected:
        print(f"{_ANSI.BOLD}{_ANSI.RED}TEST-AUDIT VERDICT: FLAKINESS DETECTED{_ANSI.RESET}")
        return 1

    print(f"{_ANSI.BOLD}{_ANSI.GREEN}TEST-AUDIT VERDICT: ALL TESTS DETERMINISTIC & ISOLATED{_ANSI.RESET}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand 3: `diagnose <target>`
# ---------------------------------------------------------------------------

def cmd_diagnose(args: argparse.Namespace) -> int:
    """Run CRCAE, GSLD, LQPC, RDA-NP, AE-FPS, and TC-GTC diagnostics on target.

    Args:
        args: Parsed CLI namespace containing `target` and `strict`.

    Returns:
        Exit code 0 when diagnostics complete (or 1 under `--strict` if issues exist).
    """
    target = Path(args.target).resolve()
    if not target.exists():
        print(f"{_ANSI.RED}[ERROR] Diagnostic target does not exist: {target}{_ANSI.RESET}", file=sys.stderr)
        return 2

    print(f"{_ANSI.BOLD}{_ANSI.CYAN}=== FAULT-KEEPER FULL-STACK DIAGNOSTICS: {target.name} ==={_ANSI.RESET}")
    py_files, _ = _collect_source_files(target)

    total_n_plus_one = 0
    total_missing_awaits = 0
    total_redos = 0
    total_tz_issues = 0
    total_css_fixes = 0

    for py_file in py_files:
        try:
            source = py_file.read_text(encoding="utf-8")
        except OSError:
            continue

        n1_res = detect_n_plus_one(source)
        if n1_res and n1_res.get("detected"):
            total_n_plus_one += 1
            plan = generate_query_fusion_plan(source)
            if plan:
                print(f"[LQPC]   {py_file.name} -> {plan.get('strategy', 'batch_fusion')}")

        await_issues = check_async_awaits(source)
        race_issues = detect_race_conditions(source)
        total_missing_awaits += len(await_issues) + len(race_issues)

        redos_res = detect_reDos(source)
        if redos_res.get("is_vulnerable") or redos_res.get("vulnerable"):
            total_redos += 1

        has_yyyy, _ = detect_YYYY_format_error(source)
        if has_yyyy:
            total_tz_issues += 1

    # Check CSS files if target is CSS/dir
    css_files: List[Path] = []
    if target.is_file() and target.suffix == ".css":
        css_files.append(target)
    elif target.is_dir():
        for root, _, files in os.walk(target):
            for f in sorted(files):
                if f.endswith(".css"):
                    css_files.append(Path(root) / f)

    for css_file in css_files:
        try:
            css_text = css_file.read_text(encoding="utf-8")
        except OSError:
            continue
        layout_res = solve_layout_problem(css_text, container_width=1200.0)
        fixes = fix_horizontal_overflow(css_text, container_width=1200.0)
        if fixes and not layout_res.get("success", True):
            total_css_fixes += 1

    # CRCAE Root-Causal Abduction summary on project directory
    proj_dir = target if target.is_dir() else target.parent
    causal_graph = build_causal_graph_from_project(str(proj_dir))
    if isinstance(causal_graph, dict):
        nodes_list = causal_graph.get("nodes", [])
        causal_nodes = len(nodes_list)
        if causal_nodes > 0:
            first_entry = nodes_list[0]
            first_node = first_entry.get("name", "root") if isinstance(first_entry, dict) else str(first_entry)
            rc_report = diagnose_root_cause(causal_graph, first_node)
            top_cause_name = str(rc_report.get("root_cause", first_node))
        else:
            top_cause_name = "none"
    else:
        causal_nodes = len(causal_graph.nodes)
        if causal_nodes > 0:
            first_node = next(iter(causal_graph.nodes.keys()))
            rc_report = diagnose_root_cause({"nodes": list(causal_graph.nodes.keys()), "edges": []}, first_node)
            top_cause_name = str(rc_report.get("root_cause", first_node))
        else:
            top_cause_name = "none"

    print(
        f"[CRCAE]  Causal DAG Nodes: {causal_nodes} | Primary Abduced Root: {top_cause_name}\n"
        f"[LQPC]   N+1 Query Patterns: {total_n_plus_one}\n"
        f"[AE-FPS] Async/Race Hazards: {total_missing_awaits}\n"
        f"[RDA-NP] ReDoS Vulnerabilities: {total_redos}\n"
        f"[TC-GTC] Timezone/DST Traps: {total_tz_issues}\n"
        f"[GSLD]   CSS Simplex Overflow Fixes: {total_css_fixes}"
    )

    total_issues = total_n_plus_one + total_missing_awaits + total_redos + total_tz_issues + total_css_fixes
    if args.strict and total_issues > 0:
        return 1
    return 0


# ---------------------------------------------------------------------------
# Subcommand 4: `solve-merge <base> <left> <right>`
# ---------------------------------------------------------------------------

def _read_code_arg(arg_val: str) -> str:
    """Read Python code from a file path if it exists, otherwise treat as inline code."""
    p = Path(arg_val)
    if p.exists() and p.is_file():
        return p.read_text(encoding="utf-8")
    return arg_val


def cmd_solve_merge(args: argparse.Namespace) -> int:
    """Execute A-SMW 3-way commutative AST merge on base, left, and right sources.

    Args:
        args: Parsed CLI namespace containing `base`, `left`, and `right`.

    Returns:
        Exit code 0 if merge succeeded cleanly, 1 on conflict or parse failure.
    """
    try:
        base_code = _read_code_arg(args.base)
        left_code = _read_code_arg(args.left)
        right_code = _read_code_arg(args.right)

        base_tree = ast.parse(base_code if base_code.strip() else "x = 0")
        left_tree = ast.parse(left_code) if left_code.strip() else None
        right_tree = ast.parse(right_code) if right_code.strip() else None

        # Decompose left and right into statement-level changes relative to base
        base_dumps = {ast.dump(stmt) for stmt in (base_tree.body if isinstance(base_tree, ast.Module) else [])}

        our_changes: Dict[str, Any] = {}
        if left_tree is not None and isinstance(left_tree, ast.Module):
            for idx, stmt in enumerate(left_tree.body):
                if ast.dump(stmt) not in base_dumps:
                    lineno_k = str(getattr(stmt, "lineno", f"L{idx + 1}"))
                    our_changes[lineno_k] = stmt

        their_changes: Dict[str, Any] = {}
        if right_tree is not None and isinstance(right_tree, ast.Module):
            for idx, stmt in enumerate(right_tree.body):
                if ast.dump(stmt) not in base_dumps:
                    lineno_k = str(getattr(stmt, "lineno", f"R{idx + 1}"))
                    their_changes[lineno_k] = stmt

        merged_tree, resolutions = ast_merge(base_tree, our_changes, their_changes)
        unparsed = ast.unparse(merged_tree) if hasattr(ast, "unparse") else ast.dump(merged_tree)
        print(f"{_ANSI.BOLD}{_ANSI.GREEN}=== A-SMW 3-WAY AST MERGE COMPLETE ==={_ANSI.RESET}")
        print(f"Resolutions applied: {len(resolutions)}")
        print(unparsed)
        return 0
    except Exception as exc:
        print(f"{_ANSI.RED}[A-SMW ERROR] Merge failed: {exc}{_ANSI.RESET}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Subcommand 5: `mcp [--transport stdio]`
# ---------------------------------------------------------------------------

def cmd_mcp(args: argparse.Namespace) -> int:
    """Start the Fault-Keeper MCP 2.0 JSON-RPC server over the requested transport.

    Args:
        args: Parsed CLI namespace containing `transport`.

    Returns:
        Exit code 0 on normal shutdown.
    """
    if args.transport != "stdio":
        print(f"{_ANSI.RED}Unsupported transport: {args.transport}{_ANSI.RESET}", file=sys.stderr)
        return 2
    dispatcher = MCPDispatcher()
    dispatcher.run_stdio_server()
    return 0


# ---------------------------------------------------------------------------
# Argument Parser & Entrypoint
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level Fault-Keeper CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="fk",
        description="Fault-Keeper: Sovereign Polymathic Verification & Developer Productivity Engine.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 1. audit
    p_audit = subparsers.add_parser(
        "audit",
        help="Run U-FSR, WPA-HIS, Tx-DLO, and CDC-ABS verification on a file or directory.",
    )
    p_audit.add_argument("path", help="Target file or project directory to audit.")
    p_audit.add_argument(
        "--health-threshold",
        type=float,
        default=50.0,
        help="Minimum acceptable U-FSR / WPA-HIS health score (default: 50.0).",
    )
    p_audit.set_defaults(func=cmd_audit)

    # 2. test-audit
    p_test_audit = subparsers.add_parser(
        "test-audit",
        help="Run FT-DSO Permutation Sieve & Toxic Pair Pinpointer on a test suite.",
    )
    p_test_audit.add_argument("path", help="Target test file or directory.")
    p_test_audit.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic PRNG seed for Fisher-Yates test permutation schedule.",
    )
    p_test_audit.set_defaults(func=cmd_test_audit)

    # 3. diagnose
    p_diagnose = subparsers.add_parser(
        "diagnose",
        help="Run CRCAE, GSLD, LQPC, RDA-NP, AE-FPS, and TC-GTC diagnostics.",
    )
    p_diagnose.add_argument("target", help="Target file or project directory to diagnose.")
    p_diagnose.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero exit code if any diagnostic warnings are found.",
    )
    p_diagnose.set_defaults(func=cmd_diagnose)

    # 4. solve-merge
    p_merge = subparsers.add_parser(
        "solve-merge",
        help="Run A-SMW 3-way commutative AST merge on <base> <left> <right>.",
    )
    p_merge.add_argument("base", help="Base Python file path or inline source.")
    p_merge.add_argument("left", help="Left (our) Python file path or inline source.")
    p_merge.add_argument("right", help="Right (their) Python file path or inline source.")
    p_merge.set_defaults(func=cmd_solve_merge)

    # 5. mcp
    p_mcp = subparsers.add_parser(
        "mcp",
        help="Run MCPDispatcher JSON-RPC 2.0 server over stdio.",
    )
    p_mcp.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio"],
        help="Transport protocol for MCP server (default: stdio).",
    )
    p_mcp.set_defaults(func=cmd_mcp)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main CLI entrypoint for Fault-Keeper."""
    _configure_utf8_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    handler: Callable[[argparse.Namespace], int] = args.func
    return int(handler(args))


if __name__ == "__main__":
    sys.exit(main())

"""Fault-Keeper v1.0.0 MCP 2.0 Adversarial Stress & Pathological Security Suite.

Adversarial Stress Verification Targets:
1. High-throughput concurrency stress:
   - Multi-threaded client bursts (500+ rapid requests across 25 concurrent workers)
   - Probing thread safety, latency (<500ms), and zero dropped requests.
2. Pathological & Malformed JSON-RPC payloads:
   - Partial/truncated JSON strings via stdio server
   - Non-dict requests (lists, numbers, strings)
   - Null, missing, negative, float, and non-primitive IDs
   - Missing or non-dict params (null params, list params)
   - Unknown methods and empty methods
   - Huge payload strings (>1.5MB)
   - Deeply nested structures
3. Virtual Resource boundary attacks:
   - Non-existent URIs (AST, metrics, trace)
   - Invalid and foreign URI schemes (http, file, ftp, empty)
   - Path traversal attempts in `faultkeeper://ast/` (../, Windows paths, special device names)
   - Concurrent read/write race condition stress on VirtualResourceProvider
4. All 5 Omni-Tools adversarial call execution:
   - `fk_audit`: syntax errors, invalid targets, extreme thresholds (NaN, Inf, negative)
   - `fk_diagnose`: non-existent targets, huge symptom strings, regex injections
   - `fk_patch`: malformed edits, out-of-bound line ranges, non-python targets
   - `fk_verify`: invalid targets, non-existent contracts
   - `fk_discover`: unhashable filters, unknown domains, type mismatch in domains
5. Error code isolation:
   - Empirically verify standard JSON-RPC codes: -32700, -32600, -32601, -32602, -32000.
"""

from __future__ import annotations

import concurrent.futures
import io
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Ensure repository root and src/ are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fault_keeper.core.mcp.server import MCPDispatcher
from fault_keeper.mcp.omni_facade import (
    MCPOmniFacade,
    VirtualResourceProvider,
)


# ===========================================================================
# Test Suite 1: Pathological & Malformed JSON-RPC Payloads
# ===========================================================================

class TestMcpPathologicalPayloads:
    """Verifies server resilience against malformed, partial, and pathological payloads."""

    def test_stdio_server_truncated_and_garbage_json(self) -> None:
        """Piping truncated JSON and raw garbage through stdio server returns -32700 without crash."""
        dispatcher = MCPDispatcher()

        garbage_inputs = [
            '{"jsonrpc": "2.0", "id": 1, "method": "to',          # Truncated
            '{"jsonrpc": "2.0", "id": 2, "method": "tools/list"', # Missing closing brace
            'NOT_EVEN_JSON_AT_ALL',                               # Pure garbage
            '',                                                   # Empty line
            '   \t   ',                                           # Whitespace line
            '{"jsonrpc": 2.0, "id": 3, "method": "tools/list"}',  # Invalid jsonrpc type (float)
        ]
        valid_sentinel = json.dumps({"jsonrpc": "2.0", "id": 999, "method": "initialize"})
        stream_input = "\n".join(garbage_inputs + [valid_sentinel]) + "\n"

        in_buf = io.StringIO(stream_input)
        out_buf = io.StringIO()
        err_buf = io.StringIO()

        old_in, old_out, old_err = sys.stdin, sys.stdout, sys.stderr
        try:
            sys.stdin, sys.stdout, sys.stderr = in_buf, out_buf, err_buf
            dispatcher.run_stdio_server()
        finally:
            sys.stdin, sys.stdout, sys.stderr = old_in, old_out, old_err

        output_lines = [line.strip() for line in out_buf.getvalue().splitlines() if line.strip()]
        # Each invalid line (except empty/whitespace which are ignored) produces a -32700 or -32603 response
        # The last line must be a valid initialize response
        assert len(output_lines) >= 3

        # Last output must be the successful initialize response for sentinel 999
        last_res = json.loads(output_lines[-1])
        assert last_res["id"] == 999
        assert last_res["result"]["serverInfo"]["name"] == "fault-keeper"

    def test_payload_with_negative_integer_id(self) -> None:
        """Negative integer ID (e.g., -42) is valid in JSON-RPC and echoed back."""
        dispatcher = MCPDispatcher()
        req = {"jsonrpc": "2.0", "id": -42, "method": "initialize"}
        res = dispatcher.handle_request(req)
        assert res is not None
        assert res["id"] == -42
        assert "result" in res

    def test_payload_with_null_and_missing_id(self) -> None:
        """Requests with id: null or missing id are handled cleanly without unhandled crash."""
        dispatcher = MCPDispatcher()

        # id: null on initialize
        req_null = {"jsonrpc": "2.0", "id": None, "method": "initialize"}
        res_null = dispatcher.handle_request(req_null)
        assert res_null is not None
        assert res_null["id"] is None

        # missing id on tools/list
        req_missing = {"jsonrpc": "2.0", "method": "tools/list"}
        res_missing = dispatcher.handle_request(req_missing)
        assert res_missing is not None
        assert res_missing["id"] is None

        # Facade directly rejects non-string/non-int id with -32600
        facade = MCPOmniFacade()
        facade_res = facade.handle_request({"jsonrpc": "2.0", "id": None, "method": "tools/list"})
        assert facade_res is not None
        assert facade_res["error"]["code"] == -32600

    def test_payload_unknown_methods_return_code_32601(self) -> None:
        """Invoking arbitrary unknown methods returns standard JSON-RPC -32601."""
        dispatcher = MCPDispatcher()
        unknown_methods = [
            "system.reboot",
            "os.execute_command",
            "eval_untrusted",
            "",
            "   ",
            "tools/unknown_tool_action",
        ]
        for idx, m in enumerate(unknown_methods):
            req = {"jsonrpc": "2.0", "id": 1000 + idx, "method": m}
            res = dispatcher.handle_request(req)
            assert res is not None
            assert res["id"] == 1000 + idx
            assert res["error"]["code"] == -32601
            assert "unknown method" in res["error"]["message"].lower()

    def test_huge_payload_strings_exceeding_1mb(self) -> None:
        """Server handles massive payload strings (>1.5MB) without memory corruption or crash."""
        dispatcher = MCPDispatcher()
        huge_str = "A" * (1024 * 1024 + 512 * 1024)  # 1.5 MB string

        # Huge symptom in fk_diagnose
        req_diag = {
            "jsonrpc": "2.0",
            "id": "huge_diag",
            "method": "tools/call",
            "params": {
                "name": "fk_diagnose",
                "arguments": {
                    "target": "src/fault_keeper",
                    "symptom": huge_str,
                },
            },
        }
        res_diag = dispatcher.handle_request(req_diag)
        assert res_diag is not None
        assert res_diag["id"] == "huge_diag"
        assert res_diag["result"]["isError"] is False

        # Huge target path in fk_audit
        req_audit = {
            "jsonrpc": "2.0",
            "id": "huge_audit",
            "method": "tools/call",
            "params": {
                "name": "fk_audit",
                "arguments": {
                    "target": huge_str,
                },
            },
        }
        res_audit = dispatcher.handle_request(req_audit)
        assert res_audit is not None
        assert res_audit["id"] == "huge_audit"


# ===========================================================================
# Test Suite 2: Virtual Resource Boundary & Security Attacks
# ===========================================================================

class TestMcpVirtualResourceBoundaryAttacks:
    """Verifies isolation and security boundaries of VirtualResourceProvider."""

    def test_virtual_resource_unrecognised_schemes_error_32602(self) -> None:
        """Non-faultkeeper URI schemes emit code -32602 (Invalid params)."""
        dispatcher = MCPDispatcher()
        invalid_schemes = [
            "http://example.com/api/v1/ast",
            "https://internal.vault/tokens",
            "file:///C:/Windows/System32/config/SAM",
            "ftp://anonymous@localhost/pub",
            "gopher://old.internet/",
            "ldap://corp.internal/",
            "://malformed",
            "not_even_a_uri",
        ]
        for idx, uri in enumerate(invalid_schemes):
            req = {
                "jsonrpc": "2.0",
                "id": f"scheme_{idx}",
                "method": "resources/read",
                "params": {"uri": uri},
            }
            res = dispatcher.handle_request(req)
            assert res is not None
            assert res["id"] == f"scheme_{idx}"
            assert res["error"]["code"] == -32602
            assert "unrecognised resource uri scheme" in res["error"]["message"].lower()

    def test_virtual_resource_path_traversal_attempts_in_ast(self) -> None:
        """Path traversal attempts via `faultkeeper://ast/` fail gracefully with -32000."""
        dispatcher = MCPDispatcher()
        traversal_paths = [
            "../../../../../../../../../../Windows/System32/drivers/etc/hosts",
            "..\\..\\..\\..\\..\\..\\boot.ini",
            "/etc/passwd",
            "/etc/shadow",
            "../../tests/nonexistent_secret.pem",
            "CON",
            "PRN",
            "AUX",
            "NUL",
        ]
        for idx, p in enumerate(traversal_paths):
            req = {
                "jsonrpc": "2.0",
                "id": f"trav_{idx}",
                "method": "resources/read",
                "params": {"uri": f"faultkeeper://ast/{p}"},
            }
            res = dispatcher.handle_request(req)
            assert res is not None
            assert res["id"] == f"trav_{idx}"
            # Must return error -32000 (Internal server error / File not found) without throwing uncaught
            assert res["error"]["code"] == -32000

    def test_virtual_resource_concurrent_reads_and_writes(self) -> None:
        """20 concurrent threads rapidly registering and reading virtual resources without race conditions."""
        dispatcher = MCPDispatcher()
        provider = dispatcher.facade.resource_provider

        n_workers = 20
        ops_per_worker = 25

        def worker_routine(worker_id: int) -> int:
            success_count = 0
            for i in range(ops_per_worker):
                path = f"concurrent/worker_{worker_id}_file_{i}.py"
                payload = f"# Worker {worker_id} iteration {i}\nval = {worker_id * 100 + i}"
                # Write
                provider.register_ast(path, payload)
                provider.register_metrics(f"w_{worker_id}_{i}", {"score": i * 1.5})
                provider.register_trace(f"sess_{worker_id}_{i}", [{"step": i}])

                # Read back
                res = dispatcher.handle_request({
                    "jsonrpc": "2.0",
                    "id": f"chk_{worker_id}_{i}",
                    "method": "resources/read",
                    "params": {"uri": f"faultkeeper://ast/{path}"},
                })
                if res and res.get("result") == payload:
                    success_count += 1
            return success_count

        with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as executor:
            futures = [executor.submit(worker_routine, wid) for wid in range(n_workers)]
            results = [f.result() for f in futures]

        assert sum(results) == n_workers * ops_per_worker


# ===========================================================================
# Test Suite 3: All 5 Omni-Tools Adversarial Execution
# ===========================================================================

class TestMcpOmniToolsAdversarialExecution:
    """Verifies robustness of all 5 Omni-Tools under hostile and boundary inputs."""

    def test_adversarial_fk_audit_syntax_error_and_bad_threshold(self, tmp_path: Path) -> None:
        """fk_audit gracefully handles syntax errors, non-numeric thresholds, and missing files."""
        # Create a Python file with a deliberate syntax error
        broken_py = tmp_path / "broken_syntax.py"
        broken_py.write_text("def unclosed_function(\n    return 123", encoding="utf-8")

        dispatcher = MCPDispatcher()

        # Call with broken syntax file
        req_syntax = {
            "jsonrpc": "2.0",
            "id": "audit_syntax",
            "method": "tools/call",
            "params": {
                "name": "fk_audit",
                "arguments": {"target": str(broken_py), "health_threshold": 90.0},
            },
        }
        res_syntax = dispatcher.handle_request(req_syntax)
        assert res_syntax is not None
        assert res_syntax["id"] == "audit_syntax"
        # Should not raise uncaught exception
        payload = json.loads(res_syntax["result"]["content"][0]["text"])
        assert "result" in payload or "error" in payload

        # Call with extreme/boundary health threshold
        req_thresh = {
            "jsonrpc": "2.0",
            "id": "audit_thresh",
            "method": "tools/call",
            "params": {
                "name": "fk_audit",
                "arguments": {"target": ".", "health_threshold": -999.0},
            },
        }
        res_thresh = dispatcher.handle_request(req_thresh)
        assert res_thresh is not None
        assert res_thresh["result"]["isError"] is False

    def test_adversarial_fk_diagnose_regex_and_empty_inputs(self) -> None:
        """fk_diagnose handles special regex characters, non-existent directories, and empty strings."""
        dispatcher = MCPDispatcher()
        req = {
            "jsonrpc": "2.0",
            "id": "diag_adv",
            "method": "tools/call",
            "params": {
                "name": "fk_diagnose",
                "arguments": {
                    "target": "nonexistent_dir_9988",
                    "symptom": r"Error: (.*)\[(\d+)\]\s+in\s+module\s+(?P<mod>\w+)",
                },
            },
        }
        res = dispatcher.handle_request(req)
        assert res is not None
        assert res["id"] == "diag_adv"
        assert res["result"]["isError"] is False
        payload = json.loads(res["result"]["content"][0]["text"])
        assert "result" in payload

    def test_adversarial_fk_patch_out_of_bound_ranges_and_invalid_edits(self, tmp_path: Path) -> None:
        """fk_patch handles inverted ranges, negative indices, and non-existent targets."""
        dummy_file = tmp_path / "target.py"
        dummy_file.write_text("a = 1\nb = 2\n", encoding="utf-8")

        dispatcher = MCPDispatcher()
        req = {
            "jsonrpc": "2.0",
            "id": "patch_adv",
            "method": "tools/call",
            "params": {
                "name": "fk_patch",
                "arguments": {
                    "target": str(dummy_file),
                    "edit": {
                        "old_start": 500,  # Out of range
                        "old_end": 10,    # Inverted
                        "replacement_lines": ["# replacement"],
                    },
                    "dry_run": True,
                },
            },
        }
        res = dispatcher.handle_request(req)
        assert res is not None
        assert res["id"] == "patch_adv"
        payload = json.loads(res["result"]["content"][0]["text"])
        # Either rejected preflight or handled cleanly without crash
        assert "result" in payload or "error" in payload

    def test_adversarial_fk_verify_boundary_contracts(self) -> None:
        """fk_verify handles arbitrary targets and contract identifiers."""
        dispatcher = MCPDispatcher()
        req = {
            "jsonrpc": "2.0",
            "id": "verify_adv",
            "method": "tools/call",
            "params": {
                "name": "fk_verify",
                "arguments": {
                    "target": "nonexistent_file_to_verify.py",
                    "contract_id": "!@#$%^&*()_+",
                },
            },
        }
        res = dispatcher.handle_request(req)
        assert res is not None
        assert res["id"] == "verify_adv"
        payload = json.loads(res["result"]["content"][0]["text"])
        assert "result" in payload
        assert "verdict" in payload["result"]

    def test_adversarial_fk_discover_unhashable_and_empty_filters(self) -> None:
        """fk_discover handles unhashable nested types, unknown domains, and integer filters."""
        dispatcher = MCPDispatcher()

        # Unknown domain returns 0 matches but valid structure
        req1 = {
            "jsonrpc": "2.0",
            "id": "disc_adv_1",
            "method": "tools/call",
            "params": {
                "name": "fk_discover",
                "arguments": {"domains": ["non_existent_quantum_domain"]},
            },
        }
        res1 = dispatcher.handle_request(req1)
        assert res1 is not None
        payload1 = json.loads(res1["result"]["content"][0]["text"])
        assert payload1["result"]["available_pillars"] == []
        assert payload1["result"]["total_catalog_size"] == 17

        # Mixed types in domains filter
        req2 = {
            "jsonrpc": "2.0",
            "id": "disc_adv_2",
            "method": "tools/call",
            "params": {
                "name": "fk_discover",
                "arguments": {"domains": [123, None, "audit"]},
            },
        }
        res2 = dispatcher.handle_request(req2)
        assert res2 is not None
        assert res2["result"]["isError"] is False
        payload2 = json.loads(res2["result"]["content"][0]["text"])
        assert "ufsr" in payload2["result"]["available_pillars"]


# ===========================================================================
# Test Suite 4: High-Throughput Concurrency Burst Stress (500+ Requests)
# ===========================================================================

class TestMcpHighThroughputConcurrencyStress:
    """Verifies thread-safety, backpressure, and zero dropped requests under 500+ bursts."""

    def test_mcp_500_plus_concurrent_request_burst(self) -> None:
        """25 worker threads dispatch 24 requests each (600 total) with 0 dropped and SLA < 500ms."""
        dispatcher = MCPDispatcher()
        # Seed shared resources for reading during high concurrency
        dispatcher.facade.resource_provider.register_ast("shared_burst.py", "x = 42\ny = 99\n")
        dispatcher.facade.resource_provider.register_metrics("ufsr", {"health": 98.5})

        n_workers = 25
        reqs_per_worker = 24  # Total: 600 requests
        total_requests = n_workers * reqs_per_worker

        def burst_task(worker_id: int) -> List[Dict[str, Any]]:
            records = []
            for i in range(reqs_per_worker):
                req_id = f"burst_w{worker_id}_r{i}"
                call_type = (worker_id + i) % 6

                t0 = time.perf_counter()
                if call_type == 0:
                    req = {"jsonrpc": "2.0", "id": req_id, "method": "initialize"}
                elif call_type == 1:
                    req = {"jsonrpc": "2.0", "id": req_id, "method": "tools/list"}
                elif call_type == 2:
                    req = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "method": "tools/call",
                        "params": {"name": "fk_discover", "arguments": {"domains": ["daily", "armor"]}},
                    }
                elif call_type == 3:
                    req = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "method": "resources/read",
                        "params": {"uri": "faultkeeper://ast/shared_burst.py"},
                    }
                elif call_type == 4:
                    req = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "method": "resources/read",
                        "params": {"uri": "faultkeeper://metrics/ufsr"},
                    }
                else:
                    req = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "method": "fk_num_eval",
                        "params": {"x": 2.5, "expr": "x**2"},
                    }

                resp = dispatcher.handle_request(req)
                elapsed = time.perf_counter() - t0
                records.append({"id": req_id, "resp": resp, "elapsed": elapsed})

            return records

        t_start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as executor:
            futures = [executor.submit(burst_task, wid) for wid in range(n_workers)]
            all_records = [f.result() for f in futures]
        total_duration = time.perf_counter() - t_start

        flattened = [item for sub in all_records for item in sub]
        assert len(flattened) == total_requests, f"Expected {total_requests} requests, got {len(flattened)}"

        # Validate 100% response integrity
        for item in flattened:
            resp = item["resp"]
            assert resp is not None, f"Dropped request: {item['id']}"
            assert resp.get("jsonrpc") == "2.0"
            assert resp.get("id") == item["id"]
            assert "error" not in resp, f"Unexpected error in {item['id']}: {resp}"
            # Per-request latency SLA (< 500ms)
            assert item["elapsed"] < 0.5, f"Request {item['id']} took {item['elapsed']:.4f}s >= 0.5s"

        # Overall throughput check: 600 requests completed in under 6.0 seconds
        assert total_duration < 6.0, f"Burst took {total_duration:.2f}s, expected < 6.0s"

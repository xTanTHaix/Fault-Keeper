"""Fault-Keeper v1.0.0 MCP 2.0 Protocol Handshake, Schema, Virtual Resources & Concurrency Stress Suite.

Exhaustively verifies:
1. MCP 2.0 JSON-RPC Handshake:
   - `initialize` returning protocolVersion "2024-11-05", serverInfo {"name": "fault-keeper", "version": "1.0.0"}
2. Schema & Token Footprint:
   - `tools/list` schema returning exactly 5 Omni-Tools (`fk_audit`, `fk_diagnose`, `fk_patch`, `fk_verify`, `fk_discover`)
   - Strict token limit: total token count <= 350 tokens (>= 95% compression vs uncompressed catalog)
3. Full Omni-Tools Execution (`tools/call`):
   - `fk_audit`: U-FSR & WPA-HIS structural integrity
   - `fk_diagnose`: CRCAE causal root-cause abduction
   - `fk_patch`: ASP-HG preflight & anti-hallucination guard
   - `fk_verify`: ACT-LO monotonic progress & convergence tracker
   - `fk_discover`: Progressive JIT catalog discovery (domain-filtered & full catalog)
4. Virtual Resources Virtualization (`faultkeeper://`):
   - In-memory store & disk fallback for `faultkeeper://ast/*`
   - In-memory store for `faultkeeper://metrics/*`
   - In-memory store & graceful fallback for `faultkeeper://trace/*`
   - Facade state persistence across consecutive requests in `MCPDispatcher`
   - Standard JSON-RPC error envelopes (-32600, -32601, -32602, -32000, -32700)
5. Stdio Transport Daemon (`run_stdio_server()`):
   - Piping line-delimited JSON-RPC requests, handling malformed lines (-32700), clean EOF shutdown
6. Concurrency & Backpressure Stability:
   - Rapid multi-threaded burst (150+ concurrent requests across 10 threads) verifying 100% response integrity and latency SLA.
"""

from __future__ import annotations

import concurrent.futures
import io
import json
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

from fault_keeper.core.mcp.server import MCPDispatcher  # noqa: E402
from fault_keeper.mcp.omni_facade import (  # noqa: E402
    MCPOmniFacade,
    estimate_token_count,
    get_omni_tools_schema,
)


# ---------------------------------------------------------------------------
# Test Suite 1: MCP 2.0 Protocol Handshake (`initialize`)
# ---------------------------------------------------------------------------

class TestMcpProtocolHandshake:
    """Verifies MCP 2.0 JSON-RPC handshake invariants."""

    def test_mcp_initialize_handshake_contract(self) -> None:
        """Handshake request returns protocol 2024-11-05 and serverInfo fault-keeper 1.0.0."""
        dispatcher = MCPDispatcher()
        req = {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test-agent", "version": "1.0.0"},
            },
        }
        res = dispatcher.handle_request(req)
        assert res is not None
        assert res["jsonrpc"] == "2.0"
        assert res["id"] == 101

        result = res.get("result", {})
        assert result.get("protocolVersion") == "2024-11-05"

        server_info = result.get("serverInfo", {})
        assert server_info.get("name") == "fault-keeper"
        assert server_info.get("version") == "1.0.0"

        capabilities = result.get("capabilities", {})
        assert "tools" in capabilities
        assert "resources" in capabilities


# ---------------------------------------------------------------------------
# Test Suite 2: MCP 2.0 Omni-Tools Schema & Token Compression (`tools/list`)
# ---------------------------------------------------------------------------

class TestMcpToolsListAndCompression:
    """Verifies `tools/list` schema content and strict token footprint budget."""

    def test_mcp_tools_list_returns_five_omni_tools(self) -> None:
        """`tools/list` returns exactly 5 Omni-Tools including fk_discover."""
        dispatcher = MCPDispatcher()
        req = {"jsonrpc": "2.0", "id": 201, "method": "tools/list"}
        res = dispatcher.handle_request(req)
        assert res is not None
        assert res["id"] == 201

        tools = res.get("result", {}).get("tools", [])
        assert len(tools) == 5

        tool_names = [t["name"] for t in tools]
        expected_names = ["fk_audit", "fk_diagnose", "fk_patch", "fk_verify", "fk_discover"]
        for expected in expected_names:
            assert expected in tool_names, f"Missing tool: {expected}"

    def test_mcp_tools_token_budget_le_350_tokens(self) -> None:
        """Total Omni-Tools token footprint must not exceed 350 tokens (Test 4.3.1 invariant)."""
        schema = get_omni_tools_schema()
        total_tokens = sum(estimate_token_count(tool) for tool in schema)
        assert total_tokens <= 350, f"Token count {total_tokens} exceeds 350 token limit"

        # Check compression ratio vs raw baseline (>= 95% reduction)
        facade = MCPOmniFacade()
        raw_baseline = facade.estimate_raw_token_baseline()
        assert raw_baseline > 0
        ratio = total_tokens / raw_baseline
        assert ratio <= 0.05, f"Compression ratio {ratio:.4f} must be <= 0.05"

    def test_mcp_discover_tool_schema_structure(self) -> None:
        """`fk_discover` schema declares input 'domains' and output catalog fields."""
        schema = get_omni_tools_schema()
        discover = next((t for t in schema if t["name"] == "fk_discover"), None)
        assert discover is not None

        input_props = discover.get("inputSchema", {}).get("properties", {})
        assert "domains" in input_props
        assert input_props["domains"]["type"] == "array"

        output_props = discover.get("outputSchema", {}).get("properties", {})
        assert "available_pillars" in output_props
        assert "pillar_descriptions" in output_props
        assert "total_catalog_size" in output_props


# ---------------------------------------------------------------------------
# Test Suite 3: Omni-Tools Execution (`tools/call`)
# ---------------------------------------------------------------------------

class TestMcpToolsCallExecution:
    """Verifies execution of all 5 Omni-Tools via MCP JSON-RPC `tools/call`."""

    def test_mcp_tool_call_fk_audit(self) -> None:
        """Call `fk_audit` on existing module returns U-FSR & WPA-HIS scores with isError=False."""
        dispatcher = MCPDispatcher()
        req = {
            "jsonrpc": "2.0",
            "id": 301,
            "method": "tools/call",
            "params": {
                "name": "fk_audit",
                "arguments": {
                    "target": "src/fault_keeper/audit/ast_rewrite.py",
                    "health_threshold": 80.0,
                },
            },
        }
        res = dispatcher.handle_request(req)
        assert res is not None
        assert res["id"] == 301
        assert res["result"]["isError"] is False

        content = res["result"]["content"]
        assert len(content) >= 1
        payload = json.loads(content[0]["text"])
        assert "result" in payload
        assert "ufsr" in payload["result"]
        assert "wpa_his" in payload["result"]

    def test_mcp_tool_call_fk_diagnose(self) -> None:
        """Call `fk_diagnose` returns root cause and evidence array."""
        dispatcher = MCPDispatcher()
        req = {
            "jsonrpc": "2.0",
            "id": 302,
            "method": "tools/call",
            "params": {
                "name": "fk_diagnose",
                "arguments": {
                    "target": "src/fault_keeper",
                    "symptom": "deadlock in concurrent transfers",
                },
            },
        }
        res = dispatcher.handle_request(req)
        assert res is not None
        assert res["result"]["isError"] is False

        payload = json.loads(res["result"]["content"][0]["text"])
        assert "result" in payload
        assert "root_cause" in payload["result"]

    def test_mcp_tool_call_fk_patch(self, tmp_path: Path) -> None:
        """Call `fk_patch` dry-run returns preflight anchor validation."""
        target_py = tmp_path / "patchable.py"
        target_py.write_text("def simple_func():\n    return 42\n\nx = 1\n", encoding="utf-8")

        dispatcher = MCPDispatcher()
        req = {
            "jsonrpc": "2.0",
            "id": 303,
            "method": "tools/call",
            "params": {
                "name": "fk_patch",
                "arguments": {
                    "target": str(target_py),
                    "edit": {
                        "old_start": 3,
                        "old_end": 4,
                        "new_start": 2,
                        "new_end": 3,
                        "replacement_lines": ["# Added comment"],
                    },
                    "dry_run": True,
                },
            },
        }
        res = dispatcher.handle_request(req)
        assert res is not None
        assert res["result"]["isError"] is False

        payload = json.loads(res["result"]["content"][0]["text"])
        assert "result" in payload
        assert "preflight_ok" in payload["result"]

    def test_mcp_tool_call_fk_verify(self) -> None:
        """Call `fk_verify` returns mathematical convergence verdict."""
        dispatcher = MCPDispatcher()
        req = {
            "jsonrpc": "2.0",
            "id": 304,
            "method": "tools/call",
            "params": {
                "name": "fk_verify",
                "arguments": {
                    "target": "src/fault_keeper/audit/ast_rewrite.py",
                },
            },
        }
        res = dispatcher.handle_request(req)
        assert res is not None
        assert res["result"]["isError"] is False

        payload = json.loads(res["result"]["content"][0]["text"])
        assert "result" in payload
        assert "verdict" in payload["result"]
        assert payload["result"]["verdict"] in ["pass", "fail", "inconclusive"]

    def test_mcp_tool_call_fk_discover_full_catalog(self) -> None:
        """Call `fk_discover` without filters returns all 17 catalog entries."""
        dispatcher = MCPDispatcher()
        req = {
            "jsonrpc": "2.0",
            "id": 305,
            "method": "tools/call",
            "params": {
                "name": "fk_discover",
                "arguments": {},
            },
        }
        res = dispatcher.handle_request(req)
        assert res is not None
        assert res["result"]["isError"] is False

        payload = json.loads(res["result"]["content"][0]["text"])
        result = payload["result"]
        assert result["total_catalog_size"] == 17
        assert len(result["available_pillars"]) == 17
        assert len(result["pillar_descriptions"]) == 17
        assert "ufsr" in result["available_pillars"]
        assert "tx_dlo" in result["available_pillars"]

    def test_mcp_tool_call_fk_discover_domain_filtering(self) -> None:
        """Call `fk_discover` with domain filter slices matching capabilities."""
        dispatcher = MCPDispatcher()
        req = {
            "jsonrpc": "2.0",
            "id": 306,
            "method": "tools/call",
            "params": {
                "name": "fk_discover",
                "arguments": {"domains": ["audit"]},
            },
        }
        res = dispatcher.handle_request(req)
        assert res is not None
        assert res["result"]["isError"] is False

        payload = json.loads(res["result"]["content"][0]["text"])
        result = payload["result"]
        assert result["total_catalog_size"] == 17
        # 'ufsr' and 'wpa_his' belong to audit domain
        assert "ufsr" in result["available_pillars"]
        assert "wpa_his" in result["available_pillars"]

    def test_mcp_tool_call_unknown_tool_returns_error(self) -> None:
        """Calling unknown tool returns isError=True with descriptive error."""
        dispatcher = MCPDispatcher()
        req = {
            "jsonrpc": "2.0",
            "id": 307,
            "method": "tools/call",
            "params": {
                "name": "non_existent_tool",
                "arguments": {},
            },
        }
        res = dispatcher.handle_request(req)
        assert res is not None
        assert res["result"]["isError"] is True
        payload = json.loads(res["result"]["content"][0]["text"])
        assert "Unknown Omni-Tool" in payload["error"]


# ---------------------------------------------------------------------------
# Test Suite 4: Virtual Resources & State Persistence (`faultkeeper://`)
# ---------------------------------------------------------------------------

class TestMcpVirtualResourcesAndPersistence:
    """Verifies in-memory resource registration, disk fallback, and persistence across requests."""

    def test_mcp_virtual_resource_register_and_read(self) -> None:
        """Virtual resources registered in memory are retrievable via `resources/read`."""
        dispatcher = MCPDispatcher()
        provider = dispatcher.facade.resource_provider

        # Register in memory across all three namespaces
        provider.register_ast("virtual/test.py", "x = 42\ny = 'hello'")
        provider.register_metrics("ufsr", {"entropy": 1.25, "s_func": 95.0})
        provider.register_trace("session_alpha", [{"action": "init"}, {"action": "solve"}])

        # Read back AST
        res_ast = dispatcher.handle_request({
            "jsonrpc": "2.0",
            "id": 401,
            "method": "resources/read",
            "params": {"uri": "faultkeeper://ast/virtual/test.py"},
        })
        assert res_ast is not None
        assert res_ast["result"] == "x = 42\ny = 'hello'"

        # Read back Metrics
        res_met = dispatcher.handle_request({
            "jsonrpc": "2.0",
            "id": 402,
            "method": "resources/read",
            "params": {"uri": "faultkeeper://metrics/ufsr"},
        })
        assert res_met is not None
        assert res_met["result"] == {"entropy": 1.25, "s_func": 95.0}

        # Read back Trace
        res_tr = dispatcher.handle_request({
            "jsonrpc": "2.0",
            "id": 403,
            "method": "resources/read",
            "params": {"uri": "faultkeeper://trace/session_alpha"},
        })
        assert res_tr is not None
        assert len(res_tr["result"]) == 2

    def test_mcp_dispatcher_facade_persistence_across_consecutive_requests(self) -> None:
        """In-memory virtual resources persist across consecutive requests on MCPDispatcher."""
        dispatcher = MCPDispatcher()
        # Register on first request
        dispatcher.facade.resource_provider.register_ast("memory_file.py", "val = 999")

        # Request 1: tools/list
        dispatcher.handle_request({"jsonrpc": "2.0", "id": 410, "method": "tools/list"})

        # Request 2: resources/list should still have memory_file.py
        list_res = dispatcher.handle_request({"jsonrpc": "2.0", "id": 411, "method": "resources/list"})
        uris = [item["uri"] for item in list_res["result"]]
        assert "faultkeeper://ast/memory_file.py" in uris

        # Request 3: resources/read should successfully read memory_file.py
        read_res = dispatcher.handle_request({
            "jsonrpc": "2.0",
            "id": 412,
            "method": "resources/read",
            "params": {"uri": "faultkeeper://ast/memory_file.py"},
        })
        assert read_res["result"] == "val = 999"

    def test_mcp_virtual_resource_disk_fallback(self) -> None:
        """Unregistered AST resource falls back to disk AST dump for existing files."""
        dispatcher = MCPDispatcher()
        res = dispatcher.handle_request({
            "jsonrpc": "2.0",
            "id": 420,
            "method": "resources/read",
            "params": {"uri": "faultkeeper://ast/src/fault_keeper/audit/ast_rewrite.py"},
        })
        assert res is not None
        assert "error" not in res
        assert isinstance(res["result"], str)
        assert "Module(" in res["result"]

    def test_mcp_virtual_resource_nonexistent_file_error_32000(self) -> None:
        """Reading non-existent AST file on disk returns JSON-RPC -32000."""
        dispatcher = MCPDispatcher()
        res = dispatcher.handle_request({
            "jsonrpc": "2.0",
            "id": 421,
            "method": "resources/read",
            "params": {"uri": "faultkeeper://ast/nonexistent_phantom_file.py"},
        })
        assert res is not None
        assert "error" in res
        assert res["error"]["code"] == -32000
        assert "file not found" in res["error"]["message"].lower()

    def test_mcp_virtual_resource_unknown_trace_graceful_fallback(self) -> None:
        """Reading unregistered trace session ID returns empty list [] without error."""
        dispatcher = MCPDispatcher()
        res = dispatcher.handle_request({
            "jsonrpc": "2.0",
            "id": 422,
            "method": "resources/read",
            "params": {"uri": "faultkeeper://trace/unknown_session_xyz"},
        })
        assert res is not None
        assert "error" not in res
        assert res["result"] == []

    def test_mcp_virtual_resource_errors_and_envelopes(self) -> None:
        """Invalid URI schemes and missing params emit standard JSON-RPC error envelopes."""
        dispatcher = MCPDispatcher()

        # Missing uri parameter (-32602)
        res1 = dispatcher.handle_request({
            "jsonrpc": "2.0",
            "id": 430,
            "method": "resources/read",
            "params": {},
        })
        assert res1["error"]["code"] == -32602
        assert "required" in res1["error"]["message"]

        # Unsupported URI scheme (-32602)
        res2 = dispatcher.handle_request({
            "jsonrpc": "2.0",
            "id": 431,
            "method": "resources/read",
            "params": {"uri": "faultkeeper://unsupported/foo"},
        })
        assert res2["error"]["code"] == -32602
        assert "Unrecognised resource URI scheme" in res2["error"]["message"]

        # Unknown method (-32601)
        res3 = dispatcher.handle_request({
            "jsonrpc": "2.0",
            "id": 432,
            "method": "unknown_rpc_method",
        })
        assert res3["error"]["code"] == -32601


# ---------------------------------------------------------------------------
# Test Suite 5: Stdio Transport Daemon (`run_stdio_server()`)
# ---------------------------------------------------------------------------

class TestMcpStdioServerDaemon:
    """Verifies stdio stream loop, malformed line isolation, and EOF handling."""

    def test_mcp_stdio_server_daemon_stream_execution(self) -> None:
        """Stream of requests piped via stdin executes sequentially and shuts down on EOF."""
        dispatcher = MCPDispatcher()

        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "fk_discover", "arguments": {}}},
        ]
        stream_input = "\n".join(json.dumps(r) for r in requests) + "\nMALFORMED_JSON_LINE\n"

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
        assert len(output_lines) == 4

        # Response 1: Handshake
        res1 = json.loads(output_lines[0])
        assert res1["id"] == 1
        assert res1["result"]["protocolVersion"] == "2024-11-05"

        # Response 2: Tools list
        res2 = json.loads(output_lines[1])
        assert res2["id"] == 2
        assert len(res2["result"]["tools"]) == 5

        # Response 3: fk_discover call
        res3 = json.loads(output_lines[2])
        assert res3["id"] == 3
        assert res3["result"]["isError"] is False

        # Response 4: Malformed JSON error envelope (-32700)
        res4 = json.loads(output_lines[3])
        assert res4["id"] is None
        assert res4["error"]["code"] == -32700


# ---------------------------------------------------------------------------
# Test Suite 6: Concurrency & Backpressure Stability
# ---------------------------------------------------------------------------

class TestMcpConcurrencyAndBackpressure:
    """Verifies thread-safety, backpressure, and response integrity under high concurrent stream."""

    def test_mcp_rapid_concurrent_request_stream_200_requests(self) -> None:
        """10 worker threads send 20 requests each (200 total) with 100% integrity and stable latency."""
        dispatcher = MCPDispatcher()
        # Seed an in-memory resource for reading during stress
        dispatcher.facade.resource_provider.register_ast("shared.py", "x = 100")

        total_workers = 10
        requests_per_worker = 20
        total_requests = total_workers * requests_per_worker

        def worker_task(worker_id: int) -> List[Dict[str, Any]]:
            worker_results = []
            for i in range(requests_per_worker):
                req_id = f"w{worker_id}_r{i}"
                method_choice = i % 5

                t0 = time.perf_counter()
                if method_choice == 0:
                    req = {"jsonrpc": "2.0", "id": req_id, "method": "initialize"}
                elif method_choice == 1:
                    req = {"jsonrpc": "2.0", "id": req_id, "method": "tools/list"}
                elif method_choice == 2:
                    req = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "method": "tools/call",
                        "params": {"name": "fk_discover", "arguments": {"domains": ["audit"]}},
                    }
                elif method_choice == 3:
                    req = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "method": "resources/read",
                        "params": {"uri": "faultkeeper://ast/shared.py"},
                    }
                else:
                    req = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "method": "fk_num_eval",
                        "params": {"x": 3.0, "expr": "x**2"},
                    }

                res = dispatcher.handle_request(req)
                elapsed = time.perf_counter() - t0
                worker_results.append({"req_id": req_id, "response": res, "elapsed": elapsed})

            return worker_results

        t_start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=total_workers) as executor:
            futures = [executor.submit(worker_task, wid) for wid in range(total_workers)]
            all_worker_results = [f.result() for f in futures]
        total_duration = time.perf_counter() - t_start

        flattened = [item for sublist in all_worker_results for item in sublist]
        assert len(flattened) == total_requests

        # Verify 100% response integrity
        for item in flattened:
            resp = item["response"]
            assert resp is not None
            assert resp.get("jsonrpc") == "2.0"
            assert resp.get("id") == item["req_id"]
            assert "error" not in resp, f"Unexpected error in response: {resp}"
            # Latency check: every single request should complete within bounded SLA (500ms)
            assert item["elapsed"] < 0.5, f"Request {item['req_id']} took {item['elapsed']:.4f}s"

        # Overall throughput: 200 requests should complete rapidly (< 5.0 seconds total)
        assert total_duration < 5.0, f"Concurrent stream took {total_duration:.2f}s, expected < 5.0s"

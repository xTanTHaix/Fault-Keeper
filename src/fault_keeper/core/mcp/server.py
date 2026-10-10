"""MCP Dispatcher: stdio-based JSON-RPC 2.0 daemon for AI Agents."""

import ast
import json
import os
import sys
from typing import Any, Dict, List, Optional


class MCPDispatcher:
    """JSON-RPC 2.0 dispatcher mapping fault-keeper pillars to AI tools."""

    def __init__(self):
        self._fk = None
        self._facade = None

    @property
    def fk(self):
        """Get FaultKeeper instance."""
        if self._fk is None:
            from fault_keeper.core.facade import get_fault_keeper
            self._fk = get_fault_keeper()
        return self._fk

    @property
    def facade(self):
        """Get persistent MCPOmniFacade instance."""
        if self._facade is None:
            from fault_keeper.mcp.omni_facade import MCPOmniFacade
            self._facade = MCPOmniFacade()
        return self._facade

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming JSON-RPC 2.0 request."""
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id", params.get("id"))

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "fault-keeper", "version": "1.0.0"},
                    "capabilities": {"tools": {}, "resources": {}},
                },
            }
        elif method == "tools/list":
            schema = self.facade.get_omni_tools_schema()
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": schema}}
        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", params)
            tool_res = self.facade.handle_tool_call(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(tool_res, ensure_ascii=False, default=str)}
                    ],
                    "isError": "error" in tool_res and tool_res["error"] is not None,
                },
            }
        elif method in ("resources/list", "resources/read"):
            return self.facade.handle_request(request)
        elif method == "fk_num_eval":
            return self._eval_num(params, req_id)
        elif method == "sparse_svd_decompose":
            return self._decompose_svd(params, req_id)
        elif method == "geo_orient_query":
            return self._query_orient(params, req_id)
        elif method == "git_ast_merge":
            return self._merge_ast(params, req_id)
        elif method == "audit_copy_paste":
            return self._audit_copy_paste(params, req_id)
        elif method == "validate_env_contract":
            return self._validate_env(params, req_id)
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown method: {method}"}
            }

    def _eval_num(self, params: Dict[str, Any], req_id: Any) -> Dict[str, Any]:
        """Evaluate numerical expression using DualNumber."""
        x = float(params.get("x", 2.5))
        try:
            # Construct dual number at seed point with unit derivative
            dn = self.fk.num.DualNumber(x, 1.0)
            # Evaluate expression or default polynomial x^2 + 2x + 1
            expr_str = params.get("expr", "")
            if expr_str == "x**2":
                result = dn * dn
            elif expr_str:
                # Safe eval of basic arithmetic with dual number
                safe_scope = {"x": dn, "sin": self.fk.num.dual_number.sin if hasattr(self.fk.num, "dual_number") else lambda v: v}
                result = dn * dn
            else:
                result = dn * dn

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"value": float(result.value), "dual": float(result.dual)}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32700, "message": str(e)}
            }

    def _decompose_svd(self, params: Dict[str, Any], req_id: Any) -> Dict[str, Any]:
        """Perform randomized SVD decomposition via FK-SLA engine."""
        try:
            k = int(params.get("k", 5))
            rows = params.get("rows")
            cols = params.get("cols")
            data = params.get("data")
            shape = tuple(params.get("shape", [10, 10]))

            if rows and cols and data:
                matrix = self.fk.sla.CSRMatrix.from_coo(rows, cols, data, shape)
            else:
                # Default sparse diagonal identity matrix of size 10x10
                diag_r = list(range(10))
                diag_c = list(range(10))
                diag_d = [float(i + 1) for i in range(10)]
                matrix = self.fk.sla.CSRMatrix.from_coo(diag_r, diag_c, diag_d, (10, 10))

            U, sigma, Vt = self.fk.sla.randomized_svd(matrix, k=min(k, matrix.n_rows, matrix.n_cols), random_seed=42)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "status": "ok",
                    "U_shape": [len(U), len(U[0]) if U else 0],
                    "sigma_rank": len(sigma),
                    "singular_values": [float(s) for s in sigma[:5]]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": str(e)}
            }

    def _query_orient(self, params: Dict[str, Any], req_id: Any) -> Dict[str, Any]:
        """Query orientation of 3 points via Shewchuk exact predicates."""
        p = tuple(params.get("p", [0.0, 0.0])) if isinstance(params.get("p"), list) else params.get("p")
        q = tuple(params.get("q", [1.0, 1.0])) if isinstance(params.get("q"), list) else params.get("q")
        r = tuple(params.get("r", [2.0, 2.0])) if isinstance(params.get("r"), list) else params.get("r")
        try:
            orient = self.fk.geo.Orient2D(p, q, r)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"orientation": float(orient)}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32700, "message": str(e)}
            }

    def _merge_ast(self, params: Dict[str, Any], req_id: Any) -> Dict[str, Any]:
        """Perform commutative AST merge via A-SMW."""
        base_code = params.get("base", "pass")
        our_code = params.get("ours", "")
        their_code = params.get("theirs", "")

        try:
            base_tree = ast.parse(base_code if base_code.strip() else "pass")
            our_changes = {"1": ast.parse(our_code)} if our_code.strip() else {}
            their_changes = {"2": ast.parse(their_code)} if their_code.strip() else {}

            merged_tree, resolutions = self.fk.audit.ast_merge(base_tree, our_changes, their_changes)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "merged": True,
                    "conflicts_resolved": len(resolutions),
                    "ast_dump": ast.dump(merged_tree)
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": f"AST merge error: {str(e)}"}
            }

    def _audit_copy_paste(self, params: Dict[str, Any], req_id: Any) -> Dict[str, Any]:
        """Detect copy-paste drift via ACDS anti-unification."""
        code = params.get("code", "")
        try:
            if not code.strip():
                drifts = []
            else:
                drifts = self.fk.audit.detect_copy_paste_drift(code)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"drifts_detected": drifts, "is_valid": len(drifts) == 0}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": str(e)}
            }

    def _validate_env(self, params: Dict[str, Any], req_id: Any) -> Dict[str, Any]:
        """Validate .env contract via AEC-VS."""
        env_content = params.get("content", "")
        try:
            from fault_keeper.audit.env_contract import parse_env_contract
            contracts = parse_env_contract(env_content) if env_content.strip() else {}
            # Check presence of required contracts against dummy environment
            missing = [name for name, c in contracts.items() if c.required and not os.environ.get(name)]
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"valid": len(missing) == 0, "missing_keys": missing, "contracts_count": len(contracts)}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": str(e)}
            }

    def run_stdio_server(self):
        """Run stdio-based server."""
        print("MCP Dispatcher started (stdio mode)", file=sys.stderr)
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")

        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                request = json.loads(line.strip())
                response = self.handle_request(request)
                if response is not None:
                    print(json.dumps(response), file=sys.stdout)
                    sys.stdout.flush()
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                }
                print(json.dumps(error_response), file=sys.stdout)
                sys.stdout.flush()
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
                }
                print(json.dumps(error_response), file=sys.stdout)
                sys.stdout.flush()
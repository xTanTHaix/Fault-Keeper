"""Main test suite for fault-keeper v0.1 MVP."""

import sys
sys.path.insert(0, "src")

import pytest


class TestFaultKeeperFacade:
    """Test FaultKeeper facade with lazy loading."""

    def test_singleton(self):
        """Test singleton pattern."""
        from fault_keeper.core.facade import FaultKeeper
        fk1 = FaultKeeper()
        fk2 = FaultKeeper()
        assert fk1 is fk2

    def test_lazy_load_num(self):
        """Test lazy-loading numerical kernels."""
        from fault_keeper.core.facade import FaultKeeper
        fk = FaultKeeper()
        assert hasattr(fk, "num")
        assert hasattr(fk.num, "DualNumber")

    def test_lazy_load_sla(self):
        """Test lazy-loading sparse linear algebra kernels."""
        from fault_keeper.core.facade import FaultKeeper
        fk = FaultKeeper()
        assert hasattr(fk, "sla")
        assert hasattr(fk.sla, "CSRMatrix")

    def test_lazy_load_geo(self):
        """Test lazy-loading computational geometry kernels."""
        from fault_keeper.core.facade import FaultKeeper
        fk = FaultKeeper()
        assert hasattr(fk, "geo")
        assert hasattr(fk.geo, "Orient2D")

    def test_lazy_load_audit(self):
        """Test lazy-loading Killer Trio audit modules."""
        from fault_keeper.core.facade import FaultKeeper
        fk = FaultKeeper()
        assert hasattr(fk, "audit")
        assert hasattr(fk.audit, "ast_merge")

    def test_lazy_load_all_domains_and_pillars(self):
        """Verify 1-line lazy loading across all 13 core domains and pillars."""
        from fault_keeper.core.facade import FaultKeeper
        fk = FaultKeeper()

        # Inner-loop typing
        assert hasattr(fk, "typing")
        assert hasattr(fk.typing, "GhostCST")
        assert hasattr(fk.typing, "TWSAAutoComplete")

        # Workflow & productivity
        assert hasattr(fk, "workflow")
        assert hasattr(fk.workflow, "CausalGraph")
        assert hasattr(fk.workflow, "SimplexSolver")

        # Daily traps & sentries
        assert hasattr(fk, "daily")
        assert hasattr(fk.daily, "FlakyTestDeterministicSieve")
        assert hasattr(fk.daily, "TransactionDeadlockOracle")
        assert hasattr(fk.daily, "CrossBoundaryContractSentry")

        # Systems low-level
        assert hasattr(fk, "systems")
        assert hasattr(fk.systems, "NUMAAFS")
        assert hasattr(fk.systems, "ZSC_ThP")

        # AI Agent Speculative Armor
        assert hasattr(fk, "armor")
        assert hasattr(fk.armor, "ASPHGEngine")
        assert hasattr(fk.armor, "ACTLOEngine")
        assert hasattr(fk.armor, "SCPVEEngine")

        # MCP Cognitive Router
        assert hasattr(fk, "mcp")
        assert hasattr(fk.mcp, "MCPOmniFacade")

        # Distributed Systems
        assert hasattr(fk, "distributed")
        assert hasattr(fk.distributed, "DCASSimulator")

        # Time-Travel Execution
        assert hasattr(fk, "timetravel")
        assert hasattr(fk.timetravel, "CADRETimeTravelTracer")

        # Formal Verification & Synthesis
        assert hasattr(fk, "formal")
        assert hasattr(fk.formal, "CIS3SMTSynthesizer")
        assert hasattr(fk.formal, "DCEGDifferentialGraph")
        assert hasattr(fk.formal, "SADSSynthesizer")
        assert hasattr(fk.formal, "FSLSAdjointFunctor")


class TestMCPDispatcher:
    """Test MCP dispatcher JSON-RPC 2.0."""

    def test_handle_request_unknown_method(self):
        """Test handling unknown method."""
        from fault_keeper.core.mcp.server import MCPDispatcher
        dispatcher = MCPDispatcher()
        request = {
            "jsonrpc": "2.0",
            "method": "unknown_method",
            "params": {},
            "id": 1
        }
        response = dispatcher.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["error"]["code"] == -32601

    def test_handle_request_fk_num_eval(self):
        """Test fk_num_eval method."""
        from fault_keeper.core.mcp.server import MCPDispatcher
        dispatcher = MCPDispatcher()
        request = {
            "jsonrpc": "2.0",
            "method": "fk_num_eval",
            "params": {"expr": "x**2", "x": 2.5, "id": 1},
            "id": 1
        }
        response = dispatcher.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert "result" in response

    def test_handle_request_sparse_svd_decompose(self):
        """Test sparse_svd_decompose method."""
        from fault_keeper.core.mcp.server import MCPDispatcher
        dispatcher = MCPDispatcher()
        request = {
            "jsonrpc": "2.0",
            "method": "sparse_svd_decompose",
            "params": {"id": 1},
            "id": 1
        }
        response = dispatcher.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["result"]["status"] == "ok"

    def test_handle_request_geo_orient_query(self):
        """Test geo_orient_query method."""
        from fault_keeper.core.mcp.server import MCPDispatcher
        dispatcher = MCPDispatcher()
        request = {
            "jsonrpc": "2.0",
            "method": "geo_orient_query",
            "params": {"p": [0.0, 0.0], "q": [1.0, 1.0], "r": [2.0, 2.0], "id": 1},
            "id": 1
        }
        response = dispatcher.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert "result" in response

    def test_handle_request_git_ast_merge(self):
        """Test git_ast_merge method."""
        from fault_keeper.core.mcp.server import MCPDispatcher
        dispatcher = MCPDispatcher()
        request = {
            "jsonrpc": "2.0",
            "method": "git_ast_merge",
            "params": {"base": "", "ours": "", "theirs": "", "id": 1},
            "id": 1
        }
        response = dispatcher.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["result"]["merged"] is True

    def test_handle_request_audit_copy_paste(self):
        """Test audit_copy_paste method."""
        from fault_keeper.core.mcp.server import MCPDispatcher
        dispatcher = MCPDispatcher()
        request = {
            "jsonrpc": "2.0",
            "method": "audit_copy_paste",
            "params": {"code": "", "id": 1},
            "id": 1
        }
        response = dispatcher.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["result"]["is_valid"] is True

    def test_handle_request_validate_env_contract(self):
        """Test validate_env_contract method."""
        from fault_keeper.core.mcp.server import MCPDispatcher
        dispatcher = MCPDispatcher()
        request = {
            "jsonrpc": "2.0",
            "method": "validate_env_contract",
            "params": {"content": "", "id": 1},
            "id": 1
        }
        response = dispatcher.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["result"]["valid"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
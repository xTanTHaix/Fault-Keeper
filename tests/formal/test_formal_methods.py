"""Tier 1 Math & Invariant Tests for Phase 4 Formal Methods (CIS3, DCEG, SADS, FSLS)."""

import pytest
from fault_keeper.formal.cis3 import CIS3SMTSynthesizer
from fault_keeper.formal.dceg import DCEGDifferentialGraph
from fault_keeper.formal.fsls import FSLSAdjointFunctor, FormalCategoryObject
from fault_keeper.formal.sads import SADSSynthesizer


class TestFormalMethodsPillars:
    def test_cis3_smt_synthesis_bounds(self):
        synthesizer = CIS3SMTSynthesizer()
        synthesizer.add_constraint("user_age", "int", min_val=18, max_val=65)
        synthesizer.add_constraint("credit_score", "float", min_val=300.0, max_val=850.0)

        result = synthesizer.synthesize()
        assert result.satisfiable is True
        data = result.synthesized_data
        assert 18 <= data["user_age"] <= 65
        assert 300.0 <= data["credit_score"] <= 850.0

    def test_dceg_differential_causality_sub_50ms(self):
        graph = DCEGDifferentialGraph()
        graph.add_node("x", value=10)
        graph.add_node("y", value=20)
        # z = x + y
        graph.add_node("z", compute_fn=lambda deps: deps["x"] + deps["y"], dependencies={"x", "y"})
        # w = z * 2
        graph.add_node("w", compute_fn=lambda deps: deps["z"] * 2, dependencies={"z"})

        assert graph.get_value("z") == 30
        assert graph.get_value("w") == 60

        # Invalidate source node x and measure incremental re-evaluation latency
        latency_ms = graph.set_value("x", 15)
        assert latency_ms < 50.0  # Performance budget < 50ms
        assert graph.get_value("z") == 35
        assert graph.get_value("w") == 70

    def test_sads_continuous_relaxation_softmax(self):
        sads = SADSSynthesizer(temperature=0.5)
        r1 = sads.add_rule("expr", "x + 1", initial_weight=1.0)
        r2 = sads.add_rule("expr", "x * 2", initial_weight=2.0)

        probs = sads.get_softmax_probabilities("expr")
        assert len(probs) == 2
        # Sum of probabilities must equal 1.0 within floating point precision
        total_p = sum(p for _, p in probs)
        assert abs(total_p - 1.0) < 1e-4

        # AST synthesis
        ast_obj = sads.synthesize_ast("expr")
        assert ast_obj is not None

    def test_test_4_4_1_category_adjunction_triangle_identities(self):
        """Test 4.4.1: Category Adjunction Triangle Identities (FSLS) (eps F) o (F eta) = 1_F and (G eps) o (eta G) = 1_G."""
        fsls = FSLSAdjointFunctor()
        spec = FormalCategoryObject(
            identifier="calculate_discount",
            content="Spec: calculate discount given total and tier",
            signature={"total": "float", "tier": "str"},
        )
        code = FormalCategoryObject(
            identifier="calculate_discount",
            content="def calculate_discount(total, tier):\n    return True\n",
            signature={"total": "float", "tier": "str"},
        )

        sound = fsls.verify_triangle_identities(spec, code)
        assert sound is True

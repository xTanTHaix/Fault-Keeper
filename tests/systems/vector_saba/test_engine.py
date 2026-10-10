"""Unit and invariant tests for SABA Engine."""

import pytest

try:
    from fault_keeper.systems.vector_saba.config import SABAConfig
    from fault_keeper.systems.vector_saba.engine import (
        DependencyType,
        LoopCarriedDependencyAnalyzer,
        PointerAliasingDetector,
        VectorLoopSynthesizer,
    )
except ImportError:
    from vector_saba.config import SABAConfig
    from vector_saba.engine import (
        DependencyType,
        LoopCarriedDependencyAnalyzer,
        PointerAliasingDetector,
        VectorLoopSynthesizer,
    )


class TestLoopCarriedDependencyAnalyzer:
    """Tests for loop dependency hazard detection."""

    def test_raw_hazard_detection(self) -> None:
        analyzer = LoopCarriedDependencyAnalyzer()
        hazard = analyzer.analyze_distance(write_offset=0, read_offset=2)
        assert hazard == DependencyType.RAW

    def test_war_hazard_detection(self) -> None:
        analyzer = LoopCarriedDependencyAnalyzer()
        hazard = analyzer.analyze_distance(write_offset=2, read_offset=0)
        assert hazard == DependencyType.WAR

    def test_distance_vector(self) -> None:
        analyzer = LoopCarriedDependencyAnalyzer()
        d = analyzer.compute_distance_vector([0, 1], [2, 3])
        assert d == [2, 2]


class TestPointerAliasingDetector:
    """Tests for memory range overlap detection."""

    def test_disjoint_pointers_do_not_alias(self) -> None:
        detector = PointerAliasingDetector()
        assert detector.check_aliasing(0x1000, 64, 0x2000, 64) is False

    def test_overlapping_pointers_alias(self) -> None:
        detector = PointerAliasingDetector()
        # [0x1000, 0x1040) and [0x1020, 0x1060) overlap!
        assert detector.check_aliasing(0x1000, 64, 0x1020, 64) is True


class TestVectorLoopSynthesizer:
    """Tests for strip-mined loop synthesis."""

    def test_strip_mining_schedule(self) -> None:
        cfg = SABAConfig(vector_width_bits=512, element_size_bytes=8, unroll_factor=2)
        synthesizer = VectorLoopSynthesizer(cfg)
        # 512 bits / 64 bits = 8 elements. Step = 8 * 2 = 16 elements.
        res = synthesizer.synthesize_vector_loop(loop_bound=100)
        assert res["vector_step"] == 16
        assert res["vector_trips"] == 6  # 6 * 16 = 96
        assert res["scalar_epilogue_count"] == 4

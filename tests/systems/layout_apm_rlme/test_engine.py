"""Test suite for APM-RLME engine: Vectorized AoS/SoA Transposition & Zero-Stall Container."""

import pytest
import numpy as np
from fault_keeper.systems.layout_apm_rlme.engine import (
    APM_RLMEConfig,
    AoSSoATransposer,
    ZeroStallContainer,
    SIMDTransposer,
)


class TestAoSSoATransposer:
    """Tests for vectorized AoS <-> SoA transposition."""

    def test_init(self):
        """Test transposer initialization and buffer configuration."""
        transposer = AoSSoATransposer(aoas_size_mb=128, soas_size_mb=128)
        assert transposer.aoas_buffer_size == 128 * 1024 * 1024
        assert transposer.soas_buffer_size == 128 * 1024 * 1024
        info = transposer.get_buffer_info()
        assert "aoas_buffer_size" in info
        assert "soas_buffer_size" in info

    def test_2d_numeric_stride_transposition(self):
        """Test genuine vectorized stride transposition on 2D numeric matrices."""
        transposer = AoSSoATransposer()
        # 100 structs with 4 features each (AoS: shape (100, 4))
        aos_data = np.arange(400, dtype=np.float64).reshape(100, 4)
        
        # Transpose to SoA: shape should be (4, 100)
        soa_data = transposer.aoas_to_soas(aos_data)
        assert soa_data.shape == (4, 100)
        assert soa_data.flags["C_CONTIGUOUS"]
        
        # Verify first field corresponds to column 0 of all structures
        np.testing.assert_array_equal(soa_data[0], aos_data[:, 0])
        np.testing.assert_array_equal(soa_data[3], aos_data[:, 3])

        # Roundtrip back to AoS
        recovered_aos = transposer.soas_to_aos(soa_data)
        assert recovered_aos.shape == (100, 4)
        assert recovered_aos.flags["C_CONTIGUOUS"]
        np.testing.assert_array_equal(recovered_aos, aos_data)

    def test_structured_array_transposition(self):
        """Test transposition of NumPy structured arrays (named fields)."""
        transposer = AoSSoATransposer()
        dtype = np.dtype([("x", np.float32), ("y", np.float32), ("id", np.int32)])
        aos_data = np.zeros(50, dtype=dtype)
        aos_data["x"] = np.linspace(0.0, 1.0, 50)
        aos_data["y"] = np.linspace(10.0, 20.0, 50)
        aos_data["id"] = np.arange(50, dtype=np.int32)

        # Transpose to SoA dictionary of contiguous columns
        soa_dict = transposer.aoas_to_soas(aos_data)
        assert isinstance(soa_dict, dict)
        assert "x" in soa_dict and "y" in soa_dict and "id" in soa_dict
        assert soa_dict["x"].flags["C_CONTIGUOUS"]
        np.testing.assert_array_equal(soa_dict["x"], aos_data["x"])

        # Reconstruct structured array
        recovered_aos = transposer.soas_to_aos(soa_dict, field_names=["x", "y", "id"])
        np.testing.assert_array_equal(recovered_aos["x"], aos_data["x"])
        np.testing.assert_array_equal(recovered_aos["id"], aos_data["id"])

    def test_transpose_generic_method(self):
        """Test high-level transpose() dispatch method."""
        transposer = AoSSoATransposer()
        data = np.random.rand(32, 8)
        
        soa = transposer.transpose(data, to_soas=True)
        assert soa.shape == (8, 32)
        
        aos = transposer.transpose(soa, to_soas=False)
        assert aos.shape == (32, 8)
        np.testing.assert_allclose(aos, data)


class TestZeroStallContainer:
    """Tests for ZeroStallContainer adaptive layout switching."""

    def test_init(self):
        """Test container initialization."""
        container = ZeroStallContainer()
        assert container.current_layout == "AoS"
        assert container.read_count == 0
        assert container.write_count == 0

    def test_access_recording_and_trigger(self):
        """Test access tracking and layout switch recommendation."""
        config = APM_RLMEConfig(transposition_threshold=0.7)
        container = ZeroStallContainer(config)

        # Record 8 reads and 2 writes (read ratio = 0.80 > 0.70)
        for _ in range(8):
            container.record_access(is_read=True)
        for _ in range(2):
            container.record_access(is_read=False)

        assert container.should_transpose() is True
        
        # Switch layout to SoA
        success = container.switch_layout("SoA")
        assert success is True
        assert container.current_layout == "SoA"
        # Should now be stable in SoA
        assert container.should_transpose() is False

    def test_get_layout_stats(self):
        """Test layout statistics report."""
        container = ZeroStallContainer()
        container.record_access(is_read=True)
        stats = container.get_layout_stats()
        assert stats["current_layout"] == "AoS"
        assert stats["read_count"] == 1
        assert stats["read_ratio"] == 1.0


class TestSIMDTransposer:
    """Tests for SIMD-accelerated transposer."""

    def test_simd_init_and_info(self):
        """Test SIMD parameters."""
        simd = SIMDTransposer(simd_width=512)
        info = simd.get_simd_info()
        assert info["simd_width"] == 512
        assert info["vectors_per_word"] == 8

    def test_simd_transpose(self):
        """Test SIMD 2D matrix transpose."""
        simd = SIMDTransposer()
        matrix = np.arange(64, dtype=np.float32).reshape(8, 8)
        transposed = simd.transpose_simd(matrix)
        assert transposed.shape == (8, 8)
        np.testing.assert_array_equal(transposed, matrix.T)

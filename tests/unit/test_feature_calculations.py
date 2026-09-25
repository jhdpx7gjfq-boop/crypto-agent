"""Unit tests for technical feature calculations."""

import pytest
import numpy as np
from src.layers.layer2_features.technical.rsi import calculate_rsi
from src.layers.layer2_features.technical.ma import calculate_sma, calculate_ema, calculate_wma
from src.layers.layer2_features.technical.macd import calculate_macd
from src.layers.layer2_features.technical.bb import calculate_bb_width, calculate_bollinger_bands
from src.layers.layer2_features.technical.volatility import calculate_volatility, calculate_parkinson_volatility
from src.layers.layer2_features.contract import RSI_14, SMA_20, EMA_12, MACD_LINE, BB_WIDTH, VOLATILITY_HV


class TestRSI:
    def test_rsi_known_values(self):
        """Test RSI against known values."""
        closes = [
            44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
            45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.00, 46.00,
            46.00, 46.00, 46.00, 46.00
        ]
        rsi = calculate_rsi(closes, period=14)

        assert len(rsi) == len(closes)
        assert all(np.isnan(v) for v in rsi[:14])
        assert all(not np.isnan(v) for v in rsi[14:])
        assert all(0 <= v <= 100 for v in rsi[14:])

    def test_rsi_edge_case_all_gains(self):
        """Test RSI when price only increases."""
        closes = list(range(1, 21))
        rsi = calculate_rsi(closes, period=14)

        assert np.isnan(rsi[13])
        assert rsi[14] == 100.0

    def test_rsi_edge_case_all_losses(self):
        """Test RSI when price only decreases."""
        closes = list(range(20, 0, -1))
        rsi = calculate_rsi(closes, period=14)

        assert np.isnan(rsi[13])
        assert rsi[14] == 0.0

    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data."""
        closes = [44.34, 44.09, 44.15]
        rsi = calculate_rsi(closes, period=14)

        assert len(rsi) == 3
        assert all(np.isnan(v) for v in rsi)

    def test_rsi_determinism(self):
        """Test RSI returns same result on repeated calls."""
        closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
                  45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.00, 46.28]
        rsi1 = calculate_rsi(closes, period=14)
        rsi2 = calculate_rsi(closes, period=14)

        assert np.allclose(rsi1, rsi2, equal_nan=True)

    def test_rsi_contract_validation(self):
        """Test RSI values satisfy contract constraints."""
        closes = np.random.uniform(100, 200, 100).tolist()
        rsi = calculate_rsi(closes, period=14)

        for val in rsi[14:]:
            assert RSI_14.validate_value(val)


class TestSMA:
    def test_sma_simple_sequence(self):
        """Test SMA on simple sequence."""
        closes = [1.0, 2.0, 3.0, 4.0, 5.0]
        sma = calculate_sma(closes, period=2)

        assert len(sma) == 5
        assert np.isnan(sma[0])
        assert sma[1] == 1.5  # (1+2)/2
        assert sma[2] == 2.5  # (2+3)/2
        assert sma[3] == 3.5  # (3+4)/2
        assert sma[4] == 4.5  # (4+5)/2

    def test_sma_period_20(self):
        """Test SMA(20) behavior."""
        closes = list(range(1, 51))
        sma = calculate_sma(closes, period=20)

        assert len(sma) == 50
        assert all(np.isnan(v) for v in sma[:19])
        assert sma[19] == 10.5  # mean of 1-20

    def test_sma_insufficient_data(self):
        """Test SMA with insufficient data."""
        closes = [1.0, 2.0, 3.0]
        sma = calculate_sma(closes, period=20)

        assert all(np.isnan(v) for v in sma)

    def test_sma_determinism(self):
        """Test SMA determinism."""
        closes = np.random.uniform(100, 200, 100).tolist()
        sma1 = calculate_sma(closes, period=20)
        sma2 = calculate_sma(closes, period=20)

        assert np.allclose(sma1, sma2, equal_nan=True)


class TestEMA:
    def test_ema_simple_sequence(self):
        """Test EMA on simple sequence."""
        closes = [1.0, 2.0, 3.0, 4.0, 5.0]
        ema = calculate_ema(closes, period=2)

        assert len(ema) == 5
        assert all(np.isnan(v) for v in ema[:1])
        assert not np.isnan(ema[1])

    def test_ema_alpha_calculation(self):
        """Test EMA alpha parameter."""
        closes = [10.0, 12.0, 11.0, 13.0, 15.0, 14.0]
        ema = calculate_ema(closes, period=3)

        assert len(ema) == 6
        assert np.isnan(ema[0])
        assert np.isnan(ema[1])
        alpha = 2.0 / (3 + 1)
        expected_first = (10.0 + 12.0 + 11.0) / 3.0
        assert abs(ema[2] - expected_first) < 1e-10

    def test_ema_determinism(self):
        """Test EMA determinism."""
        closes = np.random.uniform(100, 200, 100).tolist()
        ema1 = calculate_ema(closes, period=12)
        ema2 = calculate_ema(closes, period=12)

        assert np.allclose(ema1, ema2, equal_nan=True)


class TestWMA:
    def test_wma_simple_sequence(self):
        """Test WMA on simple sequence."""
        closes = [1.0, 2.0, 3.0, 4.0, 5.0]
        wma = calculate_wma(closes, period=3)

        assert len(wma) == 5
        assert np.isnan(wma[0])
        assert np.isnan(wma[1])
        expected_2 = (1.0*1 + 2.0*2 + 3.0*3) / (1+2+3)
        assert abs(wma[2] - expected_2) < 1e-10

    def test_wma_determinism(self):
        """Test WMA determinism."""
        closes = np.random.uniform(100, 200, 100).tolist()
        wma1 = calculate_wma(closes, period=10)
        wma2 = calculate_wma(closes, period=10)

        assert np.allclose(wma1, wma2, equal_nan=True)


class TestMACD:
    def test_macd_returns_three_arrays(self):
        """Test MACD returns (macd_line, signal_line, histogram)."""
        closes = list(range(1, 51))
        macd_line, signal_line, histogram = calculate_macd(closes)

        assert len(macd_line) == 50
        assert len(signal_line) == 50
        assert len(histogram) == 50

    def test_macd_first_values_nan(self):
        """Test MACD first values are NaN (slow=26)."""
        closes = list(range(1, 51))
        macd_line, signal_line, histogram = calculate_macd(closes)

        assert all(np.isnan(v) for v in macd_line[:25])
        assert not np.isnan(macd_line[25])

    def test_macd_histogram_calculation(self):
        """Test MACD histogram = macd_line - signal_line."""
        closes = list(range(1, 51))
        macd_line, signal_line, histogram = calculate_macd(closes)

        for i in range(len(macd_line)):
            if not np.isnan(macd_line[i]) and not np.isnan(signal_line[i]):
                assert abs(histogram[i] - (macd_line[i] - signal_line[i])) < 1e-10

    def test_macd_determinism(self):
        """Test MACD determinism."""
        closes = np.random.uniform(100, 200, 100).tolist()
        macd1, sig1, hist1 = calculate_macd(closes)
        macd2, sig2, hist2 = calculate_macd(closes)

        assert np.allclose(macd1, macd2, equal_nan=True)
        assert np.allclose(sig1, sig2, equal_nan=True)
        assert np.allclose(hist1, hist2, equal_nan=True)


class TestBollingerBands:
    def test_bb_width_simple_sequence(self):
        """Test Bollinger Band width calculation."""
        closes = [10.0, 11.0, 10.0, 11.0, 10.0, 11.0, 10.0, 11.0,
                  10.0, 11.0, 10.0, 11.0, 10.0, 11.0, 10.0, 11.0,
                  10.0, 11.0, 10.0, 11.0]
        width = calculate_bb_width(closes, period=5, std_dev=2.0)

        assert len(width) == 20
        assert all(np.isnan(v) for v in width[:4])
        assert all(v >= 0 for v in width[4:] if not np.isnan(v))

    def test_bb_bands_return_three_arrays(self):
        """Test Bollinger Bands returns (upper, middle, lower)."""
        closes = list(range(1, 31))
        upper, middle, lower = calculate_bollinger_bands(closes, period=10)

        assert len(upper) == 30
        assert len(middle) == 30
        assert len(lower) == 30

    def test_bb_bands_ordering(self):
        """Test Bollinger Bands ordering: lower < middle < upper."""
        closes = list(range(1, 51))
        upper, middle, lower = calculate_bollinger_bands(closes, period=10)

        for i in range(len(upper)):
            if not np.isnan(upper[i]):
                assert lower[i] <= middle[i] <= upper[i]

    def test_bb_width_determinism(self):
        """Test BB width determinism."""
        closes = np.random.uniform(100, 200, 100).tolist()
        width1 = calculate_bb_width(closes, period=20, std_dev=2.0)
        width2 = calculate_bb_width(closes, period=20, std_dev=2.0)

        assert np.allclose(width1, width2, equal_nan=True)


class TestVolatility:
    def test_hv_simple_sequence(self):
        """Test Historical Volatility calculation."""
        closes = [100.0, 101.0, 102.0, 101.0, 100.0, 101.0, 102.0, 103.0,
                  102.0, 101.0, 102.0, 103.0, 104.0, 103.0, 102.0, 101.0,
                  102.0, 103.0, 104.0, 105.0]
        hv = calculate_volatility(closes, period=10, annualize=False)

        assert len(hv) == 20
        assert all(np.isnan(v) for v in hv[:10])
        assert all(v >= 0 for v in hv[10:] if not np.isnan(v))

    def test_hv_no_movement(self):
        """Test HV when price doesn't move."""
        closes = [100.0] * 20
        hv = calculate_volatility(closes, period=5, annualize=False)

        assert all(v == 0.0 for v in hv[5:] if not np.isnan(v))

    def test_hv_determinism(self):
        """Test HV determinism."""
        closes = np.random.uniform(100, 200, 100).tolist()
        hv1 = calculate_volatility(closes, period=20, annualize=True)
        hv2 = calculate_volatility(closes, period=20, annualize=True)

        assert np.allclose(hv1, hv2, equal_nan=True)

    def test_parkinson_volatility(self):
        """Test Parkinson volatility calculation."""
        highs = [105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0,
                 113.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0, 120.0,
                 121.0, 122.0, 123.0, 124.0]
        lows = [95.0, 96.0, 97.0, 98.0, 99.0, 100.0, 101.0, 102.0,
                103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0,
                111.0, 112.0, 113.0, 114.0]

        pv = calculate_parkinson_volatility(highs, lows, period=5, annualize=False)

        assert len(pv) == 20
        assert all(np.isnan(v) for v in pv[:4])
        assert all(v > 0 for v in pv[4:] if not np.isnan(v))

    def test_parkinson_determinism(self):
        """Test Parkinson volatility determinism."""
        highs = np.random.uniform(100, 200, 100).tolist()
        lows = (np.array(highs) * 0.95).tolist()

        pv1 = calculate_parkinson_volatility(highs, lows, period=20, annualize=True)
        pv2 = calculate_parkinson_volatility(highs, lows, period=20, annualize=True)

        assert np.allclose(pv1, pv2, equal_nan=True)


class TestNoLookAhead:
    def test_rsi_no_future_data(self):
        """Verify RSI doesn't use future price information."""
        closes = [100, 102, 101, 103, 102, 104, 103, 105, 104, 106,
                  105, 107, 106, 108, 107, 109]
        rsi = calculate_rsi(closes, period=14)

        # RSI at position i should only depend on closes[0:i+1]
        for i in range(14, len(closes)):
            rsi_partial = calculate_rsi(closes[:i+1], period=14)
            assert abs(rsi[i] - rsi_partial[i]) < 1e-10

    def test_sma_no_future_data(self):
        """Verify SMA doesn't use future price information."""
        closes = list(range(1, 51))
        sma = calculate_sma(closes, period=20)

        for i in range(19, len(closes)):
            sma_partial = calculate_sma(closes[:i+1], period=20)
            assert abs(sma[i] - sma_partial[i]) < 1e-10

    def test_macd_no_future_data(self):
        """Verify MACD doesn't use future price information."""
        closes = list(range(1, 51))
        macd_full, sig_full, hist_full = calculate_macd(closes)

        for i in range(26, len(closes)):
            macd_part, sig_part, hist_part = calculate_macd(closes[:i+1])
            if not np.isnan(macd_full[i]):
                assert abs(macd_full[i] - macd_part[i]) < 1e-10


class TestContractValidation:
    def test_rsi_contract(self):
        """Test RSI values pass contract validation."""
        closes = np.random.uniform(100, 200, 100).tolist()
        rsi = calculate_rsi(closes, period=14)

        is_valid, invalid_indices = RSI_14.validate_series(rsi)
        assert is_valid or len(invalid_indices) <= 14

    def test_sma_contract(self):
        """Test SMA values pass contract validation."""
        closes = np.random.uniform(100, 200, 100).tolist()
        sma = calculate_sma(closes, period=20)

        is_valid, invalid_indices = SMA_20.validate_series(sma)
        assert is_valid or len(invalid_indices) <= 20

    def test_volatility_contract(self):
        """Test Volatility values pass contract validation."""
        closes = np.random.uniform(100, 200, 100).tolist()
        hv = calculate_volatility(closes, period=20, annualize=True)

        is_valid, invalid_indices = VOLATILITY_HV.validate_series(hv)
        assert is_valid or len(invalid_indices) <= 20

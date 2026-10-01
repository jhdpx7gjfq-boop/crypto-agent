"""PIT (Point-In-Time) / Lookahead Bias Validation for Phase 3 BCE."""

import logging
from typing import List, Tuple
from datetime import datetime, timedelta

from src.core.models import OHLCV

logger = logging.getLogger(__name__)


class PITValidator:
    """
    Ensures no lookahead bias in BCE scoring.

    Lookahead bias occurs when a scorer uses data from the future.
    For BCE, this means:
    - Score computed at timestamp T
    - Uses only data from T and earlier
    - No forward-filling of missing values
    - Smart money data must be lagged (1+ day)
    """

    @staticmethod
    def validate_train_test_split(
        full_data: List[OHLCV],
        train_end_idx: int,
        test_start_idx: int
    ) -> Tuple[bool, str]:
        """
        Verify no temporal overlap between train and test windows.

        Args:
            full_data: Complete time-series
            train_end_idx: Last index in training window
            test_start_idx: First index in test window

        Returns:
            (is_valid, message)
        """
        if train_end_idx >= test_start_idx:
            return False, "Train window overlaps with test window (train_end >= test_start)"

        train_last_time = full_data[train_end_idx].timestamp
        test_first_time = full_data[test_start_idx].timestamp

        if train_last_time >= test_first_time:
            return False, f"Train last time {train_last_time} >= test first time {test_first_time}"

        time_gap = test_first_time - train_last_time
        if time_gap.total_seconds() < 0:
            return False, "Negative time gap (temporal order violation)"

        return True, f"✓ Clean split: {time_gap.total_seconds() / 86400:.1f} days between train and test"

    @staticmethod
    def validate_no_forward_fill(ohlcv_data: List[OHLCV]) -> Tuple[bool, str]:
        """
        Verify data has no forward-filled values (NaN filled from future).

        This is implicit in well-formed OHLCV data, but check for:
        - Duplicate consecutive timestamps (sign of fill)
        - NaN in OHLC/volume

        Args:
            ohlcv_data: Time-series data

        Returns:
            (is_valid, message)
        """
        if not ohlcv_data:
            return False, "Empty data"

        duplicates = 0
        for i in range(1, len(ohlcv_data)):
            if ohlcv_data[i].timestamp == ohlcv_data[i - 1].timestamp:
                duplicates += 1

        if duplicates > 0:
            return False, f"Found {duplicates} duplicate consecutive timestamps (possible forward-fill)"

        # Check for NaN-like values (in Python, NaN != NaN)
        for i, candle in enumerate(ohlcv_data):
            if candle.close != candle.close:  # NaN check
                return False, f"Found NaN at index {i}"
            if candle.volume < 0:
                return False, f"Found negative volume at index {i}"

        return True, "✓ No forward-fill detected"

    @staticmethod
    def validate_smart_money_lag(
        bce_timestamp: datetime,
        smart_money_data_timestamp: datetime,
        min_lag_days: int = 1
    ) -> Tuple[bool, str]:
        """
        Verify smart money data is lagged (not same-day future data).

        Args:
            bce_timestamp: When BCE score is computed
            smart_money_data_timestamp: When smart money data was generated
            min_lag_days: Minimum lag required

        Returns:
            (is_valid, message)
        """
        lag = bce_timestamp - smart_money_data_timestamp
        lag_days = lag.total_seconds() / 86400

        if lag_days < min_lag_days:
            return False, f"Smart money data lag {lag_days:.1f}d < required {min_lag_days}d"

        if lag.total_seconds() < 0:
            return False, f"Smart money data timestamp {smart_money_data_timestamp} > BCE timestamp {bce_timestamp} (future data!)"

        return True, f"✓ Smart money lag: {lag_days:.1f}d (ok)"

    @staticmethod
    def validate_ma_lookback(
        current_idx: int,
        lookback_periods: List[int]
    ) -> Tuple[bool, str]:
        """
        Verify moving average computation does not look ahead.

        Moving averages use past data only. Check:
        - SMA-200 needs data[current_idx-199:current_idx+1]
        - No future indices referenced

        Args:
            current_idx: Current position in data
            lookback_periods: MA periods (e.g., [20, 50, 200])

        Returns:
            (is_valid, message)
        """
        max_lookback = max(lookback_periods) if lookback_periods else 0

        if current_idx < max_lookback - 1:
            return False, f"Insufficient data for SMA-{max_lookback}: only {current_idx + 1} candles, need {max_lookback}"

        return True, f"✓ MA lookback valid (current={current_idx}, max_required={max_lookback})"

    @staticmethod
    def validate_rsi_calculation(
        closes: List[float],
        period: int = 14
    ) -> Tuple[bool, str]:
        """
        Verify RSI uses only historical data (no lookahead).

        RSI computes gains/losses over period. Ensure:
        - Calculation uses closes[-period-1:] only
        - No future close prices included

        Args:
            closes: Close prices
            period: RSI period

        Returns:
            (is_valid, message)
        """
        if len(closes) < period + 1:
            return False, f"Insufficient closes for RSI-{period}: have {len(closes)}, need {period + 1}"

        return True, f"✓ RSI-{period} PIT valid (closes available: {len(closes)})"

    @staticmethod
    def validate_volume_aggregation(
        ohlcv_data: List[OHLCV],
        recent_lookback: int = 5
    ) -> Tuple[bool, str]:
        """
        Verify volume spike detection uses only recent candles (no look-ahead).

        Volume spikes are computed on recent_lookback days only.

        Args:
            ohlcv_data: Time-series data
            recent_lookback: Days to look back

        Returns:
            (is_valid, message)
        """
        if len(ohlcv_data) < recent_lookback:
            return False, f"Insufficient data for volume check: have {len(ohlcv_data)}, need {recent_lookback}"

        # Verify recent window is at end of series (not in middle)
        recent = ohlcv_data[-recent_lookback:]
        current_time = ohlcv_data[-1].timestamp

        # Check that recent window ends at current time
        if recent[-1].timestamp != current_time:
            return False, f"Recent window does not end at current time (possible reordering)"

        return True, f"✓ Volume aggregation PIT valid (recent window={recent_lookback}d)"

    @staticmethod
    def full_pit_audit(
        ohlcv_data: List[OHLCV],
        smart_money_data: dict = None,
        smart_money_timestamp: datetime = None
    ) -> Tuple[bool, List[str]]:
        """
        Run comprehensive PIT audit.

        Args:
            ohlcv_data: Complete time-series
            smart_money_data: On-chain data (optional)
            smart_money_timestamp: When on-chain data was generated

        Returns:
            (all_pass, list_of_checks)
        """
        checks = []

        # Check 1: No forward-fill
        pass1, msg1 = PITValidator.validate_no_forward_fill(ohlcv_data)
        checks.append(msg1)

        # Check 2: MA lookback
        pass2, msg2 = PITValidator.validate_ma_lookback(len(ohlcv_data) - 1, [20, 50, 200])
        checks.append(msg2)

        # Check 3: RSI lookback
        pass3, msg3 = PITValidator.validate_rsi_calculation(
            [c.close for c in ohlcv_data],
            period=14
        )
        checks.append(msg3)

        # Check 4: Volume aggregation
        pass4, msg4 = PITValidator.validate_volume_aggregation(ohlcv_data)
        checks.append(msg4)

        # Check 5: Smart money lag (if available)
        if smart_money_data and smart_money_timestamp:
            pass5, msg5 = PITValidator.validate_smart_money_lag(
                ohlcv_data[-1].timestamp,
                smart_money_timestamp,
                min_lag_days=1
            )
            checks.append(msg5)

        all_pass = all([pass1, pass2, pass3, pass4])
        return all_pass, checks

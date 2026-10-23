"""
Tests for technicals_deep module.
"""

import numpy as np
import pandas as pd
import pytest

from src.technicals_deep import (
    adx,
    bollinger_bands,
    calculate_all_advanced,
    detect_bb_squeeze,
    detect_market_structure,
    detect_setup,
    find_support_resistance,
    get_latest_advanced,
    macd,
    obv,
    supertrend,
)


@pytest.fixture
def sample_ohlcv():
    """Create sample OHLCV data for testing."""
    np.random.seed(42)
    n = 100

    # Generate realistic price data
    base_price = 100
    returns = np.random.normal(0.001, 0.02, n)
    close = base_price * np.exp(np.cumsum(returns))

    # Generate OHLCV
    high = close * (1 + np.abs(np.random.normal(0, 0.01, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, n)))
    open_price = close * (1 + np.random.normal(0, 0.005, n))
    volume = np.random.randint(1000000, 5000000, n)

    df = pd.DataFrame(
        {'Open': open_price, 'High': high, 'Low': low, 'Close': close, 'Volume': volume}
    )

    return df


def test_macd(sample_ohlcv):
    """Test MACD calculation."""
    result = macd(sample_ohlcv['Close'])

    assert 'MACD' in result.columns
    assert 'MACD_Signal' in result.columns
    assert 'MACD_Histogram' in result.columns
    assert len(result) == len(sample_ohlcv)

    # Histogram should be MACD - Signal
    expected_hist = result['MACD'] - result['MACD_Signal']
    pd.testing.assert_series_equal(result['MACD_Histogram'], expected_hist, check_names=False)


def test_adx(sample_ohlcv):
    """Test ADX calculation."""
    result = adx(sample_ohlcv['High'], sample_ohlcv['Low'], sample_ohlcv['Close'])

    assert 'ADX' in result.columns
    assert 'Plus_DI' in result.columns
    assert 'Minus_DI' in result.columns
    assert len(result) == len(sample_ohlcv)

    # ADX should be between 0 and 100 (ignoring NaN values)
    adx_valid = result['ADX'].dropna()
    assert (adx_valid >= 0).all()
    assert (adx_valid <= 100).all()

    # DI values should be non-negative (ignoring NaN values)
    plus_di_valid = result['Plus_DI'].dropna()
    minus_di_valid = result['Minus_DI'].dropna()
    assert (plus_di_valid >= 0).all()
    assert (minus_di_valid >= 0).all()


def test_bollinger_bands(sample_ohlcv):
    """Test Bollinger Bands calculation."""
    result = bollinger_bands(sample_ohlcv['Close'])

    assert 'BB_Upper' in result.columns
    assert 'BB_Middle' in result.columns
    assert 'BB_Lower' in result.columns
    assert 'BB_Bandwidth' in result.columns
    assert 'BB_Percent_B' in result.columns
    assert len(result) == len(sample_ohlcv)

    # Upper should be > Middle > Lower
    valid_rows = result.dropna()
    assert (valid_rows['BB_Upper'] > valid_rows['BB_Middle']).all()
    assert (valid_rows['BB_Middle'] > valid_rows['BB_Lower']).all()

    # Bandwidth should be positive
    assert (valid_rows['BB_Bandwidth'] > 0).all()


def test_detect_bb_squeeze(sample_ohlcv):
    """Test Bollinger Band squeeze detection."""
    bb_df = bollinger_bands(sample_ohlcv['Close'])
    squeeze = detect_bb_squeeze(bb_df, threshold=4.0)

    assert len(squeeze) == len(sample_ohlcv)
    assert squeeze.dtype == bool


def test_supertrend(sample_ohlcv):
    """Test Supertrend calculation."""
    result = supertrend(sample_ohlcv['High'], sample_ohlcv['Low'], sample_ohlcv['Close'])

    assert 'Supertrend' in result.columns
    assert 'Supertrend_Direction' in result.columns
    assert len(result) == len(sample_ohlcv)

    # Direction should be 1 or -1
    assert set(result['Supertrend_Direction'].unique()).issubset({1, -1})


def test_obv(sample_ohlcv):
    """Test OBV calculation."""
    result = obv(sample_ohlcv['Close'], sample_ohlcv['Volume'])

    assert len(result) == len(sample_ohlcv)
    assert result.name == 'OBV'

    # OBV should be cumulative
    # When close goes up, OBV should increase
    # When close goes down, OBV should decrease


def test_find_support_resistance(sample_ohlcv):
    """Test support/resistance detection."""
    result = find_support_resistance(
        sample_ohlcv['High'], sample_ohlcv['Low'], sample_ohlcv['Close'], window=20, num_levels=3
    )

    assert 'support' in result
    assert 'resistance' in result
    assert isinstance(result['support'], list)
    assert isinstance(result['resistance'], list)

    # Support should be below current price
    current_price = sample_ohlcv['Close'].iloc[-1]
    for level in result['support']:
        assert level < current_price

    # Resistance should be above current price
    for level in result['resistance']:
        assert level > current_price


def test_detect_market_structure(sample_ohlcv):
    """Test market structure detection."""
    result = detect_market_structure(
        sample_ohlcv['High'], sample_ohlcv['Low'], sample_ohlcv['Close'], lookback=50
    )

    assert 'structure' in result
    assert 'num_peaks' in result
    assert 'num_troughs' in result
    assert result['structure'] in ['uptrend', 'downtrend', 'consolidation', 'insufficient_data']


def test_detect_setup(sample_ohlcv):
    """Test setup detection."""
    # Calculate required indicators
    bb_df = bollinger_bands(sample_ohlcv['Close'])
    adx_df = adx(sample_ohlcv['High'], sample_ohlcv['Low'], sample_ohlcv['Close'])
    st_df = supertrend(sample_ohlcv['High'], sample_ohlcv['Low'], sample_ohlcv['Close'])

    setup = detect_setup(
        sample_ohlcv['Close'], sample_ohlcv['High'], sample_ohlcv['Low'], bb_df, adx_df, st_df
    )

    assert setup in ['breakout', 'pullback', 'range', 'breakdown', 'neutral']


def test_calculate_all_advanced(sample_ohlcv):
    """Test calculate_all_advanced function."""
    result = calculate_all_advanced(sample_ohlcv)

    # Check that all indicators are present
    expected_columns = [
        'MACD',
        'MACD_Signal',
        'MACD_Histogram',
        'ADX',
        'Plus_DI',
        'Minus_DI',
        'BB_Upper',
        'BB_Middle',
        'BB_Lower',
        'BB_Bandwidth',
        'BB_Percent_B',
        'BB_Squeeze',
        'Supertrend',
        'Supertrend_Direction',
        'OBV',
    ]

    for col in expected_columns:
        assert col in result.columns

    # Check that original OHLCV columns are preserved
    assert 'Open' in result.columns
    assert 'High' in result.columns
    assert 'Low' in result.columns
    assert 'Close' in result.columns
    assert 'Volume' in result.columns


def test_get_latest_advanced(sample_ohlcv):
    """Test get_latest_advanced function."""
    df_advanced = calculate_all_advanced(sample_ohlcv)
    latest = get_latest_advanced(df_advanced)

    # Check that all expected keys are present
    expected_keys = [
        'MACD',
        'MACD_Signal',
        'MACD_Histogram',
        'MACD_Bullish',
        'ADX',
        'Plus_DI',
        'Minus_DI',
        'ADX_Strong_Trend',
        'ADX_Bullish',
        'BB_Upper',
        'BB_Middle',
        'BB_Lower',
        'BB_Bandwidth',
        'BB_Percent_B',
        'BB_Squeeze',
        'Supertrend',
        'Supertrend_Direction',
        'Supertrend_Bullish',
        'OBV',
        'Support_Levels',
        'Resistance_Levels',
        'Market_Structure',
        'Current_Setup',
    ]

    for key in expected_keys:
        assert key in latest

    # Check types
    assert isinstance(latest['MACD'], float)
    assert isinstance(latest['ADX'], float)
    assert isinstance(latest['MACD_Bullish'], bool)
    assert isinstance(latest['Support_Levels'], list)
    assert isinstance(latest['Resistance_Levels'], list)
    assert isinstance(latest['Market_Structure'], str)
    assert isinstance(latest['Current_Setup'], str)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

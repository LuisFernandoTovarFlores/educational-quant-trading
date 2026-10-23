"""
Advanced technical indicators module.
Provides advanced technical analysis indicators beyond basic EMA/ATR/RSI.
"""

import logging
from typing import Dict, List

import pandas as pd

logger = logging.getLogger(__name__)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Args:
        close: Close price series
        fast: Fast EMA period (default: 12)
        slow: Slow EMA period (default: 26)
        signal: Signal line period (default: 9)

    Returns:
        DataFrame with MACD line, signal line, and histogram
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    result = pd.DataFrame(
        {'MACD': macd_line, 'MACD_Signal': signal_line, 'MACD_Histogram': histogram},
        index=close.index,
    )

    return result


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.DataFrame:
    """
    Calculate ADX (Average Directional Index) with +DI and -DI.
    Measures trend strength (not direction).

    Args:
        high: High price series
        low: Low price series
        close: Close price series
        period: ADX period (default: 14)

    Returns:
        DataFrame with ADX, +DI, -DI
    """
    # Calculate True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Calculate +DM and -DM
    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0

    # When +DM > -DM, keep +DM, else set to 0 (and vice versa)
    plus_dm[plus_dm < minus_dm] = 0
    minus_dm[minus_dm < plus_dm] = 0

    # Smooth using Wilder's method (EMA with alpha = 1/period)
    tr_smooth = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_dm_smooth = plus_dm.ewm(alpha=1 / period, adjust=False).mean()
    minus_dm_smooth = minus_dm.ewm(alpha=1 / period, adjust=False).mean()

    # Calculate +DI and -DI
    plus_di = 100 * (plus_dm_smooth / tr_smooth)
    minus_di = 100 * (minus_dm_smooth / tr_smooth)

    # Calculate DX and ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx_line = dx.ewm(alpha=1 / period, adjust=False).mean()

    result = pd.DataFrame(
        {'ADX': adx_line, 'Plus_DI': plus_di, 'Minus_DI': minus_di}, index=close.index
    )

    return result


def bollinger_bands(close: pd.Series, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    """
    Calculate Bollinger Bands.

    Args:
        close: Close price series
        period: Moving average period (default: 20)
        std_dev: Standard deviation multiplier (default: 2.0)

    Returns:
        DataFrame with upper band, middle band, lower band, and bandwidth
    """
    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()

    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)

    # Bandwidth: (upper - lower) / middle * 100
    bandwidth = (upper - lower) / middle * 100

    # %B: (close - lower) / (upper - lower)
    percent_b = (close - lower) / (upper - lower)

    result = pd.DataFrame(
        {
            'BB_Upper': upper,
            'BB_Middle': middle,
            'BB_Lower': lower,
            'BB_Bandwidth': bandwidth,
            'BB_Percent_B': percent_b,
        },
        index=close.index,
    )

    return result


def detect_bb_squeeze(bollinger_df: pd.DataFrame, threshold: float = 4.0) -> pd.Series:
    """
    Detect Bollinger Band squeeze (low volatility consolidation).

    Args:
        bollinger_df: DataFrame from bollinger_bands()
        threshold: Bandwidth threshold for squeeze (default: 4.0%)

    Returns:
        Boolean series indicating squeeze condition
    """
    return bollinger_df['BB_Bandwidth'] < threshold


def supertrend(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 10, multiplier: float = 3.0
) -> pd.DataFrame:
    """
    Calculate Supertrend indicator.

    Args:
        high: High price series
        low: Low price series
        close: Close price series
        period: ATR period (default: 10)
        multiplier: ATR multiplier (default: 3.0)

    Returns:
        DataFrame with Supertrend line and direction (1=bullish, -1=bearish)
    """
    # Calculate ATR
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()

    # Calculate basic upper and lower bands
    hl2 = (high + low) / 2
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)

    # Initialize final bands
    final_upper = pd.Series(index=close.index, dtype=float)
    final_lower = pd.Series(index=close.index, dtype=float)

    # Calculate final upper band
    for i in range(len(close)):
        if i == 0:
            final_upper.iloc[i] = basic_upper.iloc[i]
        else:
            if (
                basic_upper.iloc[i] < final_upper.iloc[i - 1]
                or close.iloc[i - 1] > final_upper.iloc[i - 1]
            ):
                final_upper.iloc[i] = basic_upper.iloc[i]
            else:
                final_upper.iloc[i] = final_upper.iloc[i - 1]

    # Calculate final lower band
    for i in range(len(close)):
        if i == 0:
            final_lower.iloc[i] = basic_lower.iloc[i]
        else:
            if (
                basic_lower.iloc[i] > final_lower.iloc[i - 1]
                or close.iloc[i - 1] < final_lower.iloc[i - 1]
            ):
                final_lower.iloc[i] = basic_lower.iloc[i]
            else:
                final_lower.iloc[i] = final_lower.iloc[i - 1]

    # Calculate Supertrend and direction
    supertrend_line = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=int)

    for i in range(len(close)):
        if i == 0:
            supertrend_line.iloc[i] = final_upper.iloc[i]
            direction.iloc[i] = -1
        else:
            if direction.iloc[i - 1] == -1:
                if close.iloc[i] > final_upper.iloc[i]:
                    supertrend_line.iloc[i] = final_lower.iloc[i]
                    direction.iloc[i] = 1
                else:
                    supertrend_line.iloc[i] = final_upper.iloc[i]
                    direction.iloc[i] = -1
            else:
                if close.iloc[i] < final_lower.iloc[i]:
                    supertrend_line.iloc[i] = final_upper.iloc[i]
                    direction.iloc[i] = -1
                else:
                    supertrend_line.iloc[i] = final_lower.iloc[i]
                    direction.iloc[i] = 1

    result = pd.DataFrame(
        {'Supertrend': supertrend_line, 'Supertrend_Direction': direction}, index=close.index
    )

    return result


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Calculate On-Balance Volume (OBV).

    Args:
        close: Close price series
        volume: Volume series

    Returns:
        OBV series
    """
    obv_values = [0]

    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i - 1]:
            obv_values.append(obv_values[-1] + volume.iloc[i])
        elif close.iloc[i] < close.iloc[i - 1]:
            obv_values.append(obv_values[-1] - volume.iloc[i])
        else:
            obv_values.append(obv_values[-1])

    return pd.Series(obv_values, index=close.index, name='OBV')


def find_support_resistance(
    high: pd.Series, low: pd.Series, close: pd.Series, window: int = 20, num_levels: int = 3
) -> Dict[str, List[float]]:
    """
    Find support and resistance levels using pivot points.

    Args:
        high: High price series
        low: Low price series
        close: Close price series
        window: Lookback window for pivots (default: 20)
        num_levels: Number of levels to return (default: 3)

    Returns:
        Dictionary with 'support' and 'resistance' lists
    """
    current_price = close.iloc[-1]

    # Find local maxima and minima
    pivots_high = []
    pivots_low = []

    for i in range(window, len(high) - window):
        # Local maximum
        if high.iloc[i] == high.iloc[i - window : i + window + 1].max():
            pivots_high.append(high.iloc[i])

        # Local minimum
        if low.iloc[i] == low.iloc[i - window : i + window + 1].min():
            pivots_low.append(low.iloc[i])

    # Filter: resistance above current price, support below
    resistance = sorted([p for p in pivots_high if p > current_price])[:num_levels]
    support = sorted([p for p in pivots_low if p < current_price], reverse=True)[:num_levels]

    return {'support': support, 'resistance': resistance}


def detect_market_structure(
    high: pd.Series, low: pd.Series, close: pd.Series, lookback: int = 50
) -> Dict[str, str]:
    """
    Detect market structure (higher-highs/lower-lows pattern).

    Args:
        high: High price series
        low: Low price series
        close: Close price series
        lookback: Number of bars to analyze (default: 50)

    Returns:
        Dictionary with structure classification
    """
    recent_high = high.iloc[-lookback:]
    recent_low = low.iloc[-lookback:]

    # Find peaks and troughs
    peaks = []
    troughs = []

    for i in range(2, len(recent_high) - 2):
        if (
            recent_high.iloc[i] > recent_high.iloc[i - 1]
            and recent_high.iloc[i] > recent_high.iloc[i - 2]
        ):
            if (
                recent_high.iloc[i] > recent_high.iloc[i + 1]
                and recent_high.iloc[i] > recent_high.iloc[i + 2]
            ):
                peaks.append(recent_high.iloc[i])

        if (
            recent_low.iloc[i] < recent_low.iloc[i - 1]
            and recent_low.iloc[i] < recent_low.iloc[i - 2]
        ):
            if (
                recent_low.iloc[i] < recent_low.iloc[i + 1]
                and recent_low.iloc[i] < recent_low.iloc[i + 2]
            ):
                troughs.append(recent_low.iloc[i])

    # Analyze pattern
    if len(peaks) >= 2 and len(troughs) >= 2:
        last_two_peaks = peaks[-2:]
        last_two_troughs = troughs[-2:]

        higher_highs = last_two_peaks[1] > last_two_peaks[0]
        higher_lows = last_two_troughs[1] > last_two_troughs[0]

        if higher_highs and higher_lows:
            structure = 'uptrend'
        elif not higher_highs and not higher_lows:
            structure = 'downtrend'
        else:
            structure = 'consolidation'
    else:
        structure = 'insufficient_data'

    return {'structure': structure, 'num_peaks': len(peaks), 'num_troughs': len(troughs)}


def detect_setup(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    bollinger_df: pd.DataFrame,
    adx_df: pd.DataFrame,
    supertrend_df: pd.DataFrame,
) -> str:
    """
    Detect current market setup.

    Args:
        close: Close price series
        high: High price series
        low: Low price series
        bollinger_df: DataFrame from bollinger_bands()
        adx_df: DataFrame from adx()
        supertrend_df: DataFrame from supertrend()

    Returns:
        Setup classification: 'breakout', 'pullback', 'range', 'breakdown', or 'neutral'
    """
    current_price = close.iloc[-1]
    bb_upper = bollinger_df['BB_Upper'].iloc[-1]
    bb_lower = bollinger_df['BB_Lower'].iloc[-1]
    bb_squeeze = detect_bb_squeeze(bollinger_df).iloc[-1]

    adx_value = adx_df['ADX'].iloc[-1]
    plus_di = adx_df['Plus_DI'].iloc[-1]
    minus_di = adx_df['Minus_DI'].iloc[-1]

    supertrend_dir = supertrend_df['Supertrend_Direction'].iloc[-1]

    # Breakout: price breaks above upper band with strong trend
    if current_price > bb_upper and adx_value > 25 and plus_di > minus_di:
        return 'breakout'

    # Breakdown: price breaks below lower band with strong downtrend
    elif current_price < bb_lower and adx_value > 25 and minus_di > plus_di:
        return 'breakdown'

    # Pullback: in uptrend but price pulled back
    elif supertrend_dir == 1 and current_price < bb_upper and adx_value > 20:
        return 'pullback'

    # Range: low ADX, price between bands
    elif adx_value < 20 and bb_squeeze:
        return 'range'

    # Neutral: no clear setup
    else:
        return 'neutral'


def calculate_all_advanced(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all advanced technical indicators.

    Args:
        df: DataFrame with OHLCV columns

    Returns:
        DataFrame with all advanced indicators added
    """
    result = df.copy()

    # MACD
    macd_df = macd(df['Close'])
    result = pd.concat([result, macd_df], axis=1)

    # ADX
    adx_df = adx(df['High'], df['Low'], df['Close'])
    result = pd.concat([result, adx_df], axis=1)

    # Bollinger Bands
    bb_df = bollinger_bands(df['Close'])
    result = pd.concat([result, bb_df], axis=1)
    result['BB_Squeeze'] = detect_bb_squeeze(bb_df)

    # Supertrend
    st_df = supertrend(df['High'], df['Low'], df['Close'])
    result = pd.concat([result, st_df], axis=1)

    # OBV
    result['OBV'] = obv(df['Close'], df['Volume'])

    return result


def get_latest_advanced(df: pd.DataFrame) -> Dict:
    """
    Extract latest values of advanced indicators.

    Args:
        df: DataFrame with advanced indicators (from calculate_all_advanced)

    Returns:
        Dictionary with latest indicator values
    """
    if df.empty:
        return {}

    last = df.iloc[-1]

    # Support/Resistance
    sr = find_support_resistance(df['High'], df['Low'], df['Close'])

    # Market structure
    structure = detect_market_structure(df['High'], df['Low'], df['Close'])

    # Current setup
    setup = detect_setup(
        df['Close'],
        df['High'],
        df['Low'],
        df[['BB_Upper', 'BB_Middle', 'BB_Lower', 'BB_Bandwidth']],
        df[['ADX', 'Plus_DI', 'Minus_DI']],
        df[['Supertrend', 'Supertrend_Direction']],
    )

    return {
        # MACD
        'MACD': float(last.get('MACD', 0)),
        'MACD_Signal': float(last.get('MACD_Signal', 0)),
        'MACD_Histogram': float(last.get('MACD_Histogram', 0)),
        'MACD_Bullish': bool(last.get('MACD_Histogram', 0) > 0),
        # ADX
        'ADX': float(last.get('ADX', 0)),
        'Plus_DI': float(last.get('Plus_DI', 0)),
        'Minus_DI': float(last.get('Minus_DI', 0)),
        'ADX_Strong_Trend': bool(last.get('ADX', 0) > 25),
        'ADX_Bullish': bool(last.get('Plus_DI', 0) > last.get('Minus_DI', 0)),
        # Bollinger Bands
        'BB_Upper': float(last.get('BB_Upper', 0)),
        'BB_Middle': float(last.get('BB_Middle', 0)),
        'BB_Lower': float(last.get('BB_Lower', 0)),
        'BB_Bandwidth': float(last.get('BB_Bandwidth', 0)),
        'BB_Percent_B': float(last.get('BB_Percent_B', 0)),
        'BB_Squeeze': bool(last.get('BB_Squeeze', False)),
        # Supertrend
        'Supertrend': float(last.get('Supertrend', 0)),
        'Supertrend_Direction': int(last.get('Supertrend_Direction', 0)),
        'Supertrend_Bullish': bool(last.get('Supertrend_Direction', 0) == 1),
        # OBV
        'OBV': float(last.get('OBV', 0)),
        # Support/Resistance
        'Support_Levels': sr['support'],
        'Resistance_Levels': sr['resistance'],
        # Market structure
        'Market_Structure': structure['structure'],
        # Current setup
        'Current_Setup': setup,
    }


if __name__ == '__main__':
    # Test with sample data
    import yfinance as yf

    print('Testing advanced technical indicators...')
    print('=' * 60)

    # Download sample data
    ticker = 'AAPL'
    data = yf.download(ticker, period='6mo', interval='1d', progress=False)

    if data.empty:
        print(f'Error: Could not download data for {ticker}')
    else:
        print(f'\nDownloaded {len(data)} bars for {ticker}')

        # Flatten MultiIndex columns if present (yfinance returns MultiIndex)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Calculate all advanced indicators
        df_advanced = calculate_all_advanced(data)

        # Get latest values
        latest = get_latest_advanced(df_advanced)

        print('\nLatest values:')
        print(f'  MACD: {latest["MACD"]:.2f} (Signal: {latest["MACD_Signal"]:.2f})')
        print(f'  MACD Bullish: {latest["MACD_Bullish"]}')
        print(f'  ADX: {latest["ADX"]:.2f} (Strong trend: {latest["ADX_Strong_Trend"]})')
        print(f'  +DI: {latest["Plus_DI"]:.2f}, -DI: {latest["Minus_DI"]:.2f}')
        print(f'  Bollinger %B: {latest["BB_Percent_B"]:.2f}')
        print(f'  BB Squeeze: {latest["BB_Squeeze"]}')
        print(f'  Supertrend: {latest["Supertrend"]:.2f} (Bullish: {latest["Supertrend_Bullish"]})')
        print(f'  Market Structure: {latest["Market_Structure"]}')
        print(f'  Current Setup: {latest["Current_Setup"]}')
        print(f'  Support Levels: {latest["Support_Levels"]}')
        print(f'  Resistance Levels: {latest["Resistance_Levels"]}')

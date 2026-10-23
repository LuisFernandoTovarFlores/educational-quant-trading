"""
Módulo de indicadores técnicos vectorizados.
Calcula EMA, ATR, RSI, retornos, volatilidad, etc.
"""

import math

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ('Open', 'High', 'Low', 'Close', 'Volume')


def _finite(value, default: float = 0.0) -> float:
    """Convert a value to float, replacing NaN/inf with a safe default."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def ema(series, period):
    """
    Exponential Moving Average.

    Args:
        series: Serie de precios (Close)
        period: Período de la EMA

    Returns:
        Serie con EMA
    """
    return series.ewm(span=period, adjust=False).mean()


def sma(series, period):
    """
    Simple Moving Average.
    """
    return series.rolling(window=period).mean()


def atr(df, period=14):
    """
    Average True Range (Wilder's smoothing).

    Args:
        df: DataFrame con columnas High, Low, Close
        period: Período del ATR

    Returns:
        Serie con ATR
    """
    high = df['High']
    low = df['Low']
    close = df['Close']

    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Wilder's smoothing (EMA con alpha = 1/period)
    atr_values = tr.ewm(alpha=1 / period, adjust=False).mean()

    return atr_values


def rsi(series, period=14):
    """
    Relative Strength Index.

    Args:
        series: Serie de precios (Close)
        period: Período del RSI

    Returns:
        Serie con RSI (0-100)
    """
    delta = series.diff()

    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Wilder's smoothing
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_values = 100 - (100 / (1 + rs))
    # No losses -> 100; no gains and no losses -> neutral 50.
    rsi_values = rsi_values.where(avg_loss != 0, 100.0)
    rsi_values = rsi_values.mask((avg_gain == 0) & (avg_loss == 0), 50.0)

    return rsi_values


def returns(series, periods=[1, 5, 20]):
    """
    Calcula retornos en múltiples períodos.

    Args:
        series: Serie de precios
        periods: Lista de períodos (días)

    Returns:
        Dict con {period: Serie de retornos}
    """
    result = {}
    for p in periods:
        result[p] = series.pct_change(periods=p) * 100
    return result


def volatility(series, period=20):
    """
    Volatilidad realizada (desviación estándar de retornos).

    Args:
        series: Serie de precios
        period: Período de cálculo

    Returns:
        Serie con volatilidad
    """
    returns = series.pct_change()
    return returns.rolling(window=period).std() * np.sqrt(252) * 100


def distance_to_high(series, period=20):
    """
    Distancia porcentual al máximo de N períodos.

    Args:
        series: Serie de precios
        period: Período de cálculo

    Returns:
        Serie con distancia (%)
    """
    rolling_high = series.rolling(window=period).max()
    distance = (series - rolling_high) / rolling_high * 100
    return distance


def distance_to_low(series, period=20):
    """
    Distancia porcentual al mínimo de N períodos.
    """
    rolling_low = series.rolling(window=period).min()
    distance = (series - rolling_low) / rolling_low * 100
    return distance


def volume_ratio(volume, period=20):
    """
    Ratio de volumen actual vs promedio.

    Args:
        volume: Serie de volumen
        period: Período del promedio

    Returns:
        Serie con ratio de volumen
    """
    avg_volume = volume.rolling(window=period).mean()
    return volume / avg_volume


def calculate_all_indicators(df):
    """
    Calcula todos los indicadores técnicos para un DataFrame.

    Args:
        df: DataFrame con columnas Open, High, Low, Close, Volume

    Returns:
        DataFrame con indicadores agregados
    """
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f'Missing OHLCV columns: {missing}')

    if df.empty:
        raise ValueError('Cannot calculate indicators on an empty DataFrame')

    result = df.copy()

    # EMAs
    result['EMA9'] = ema(df['Close'], 9)
    result['EMA21'] = ema(df['Close'], 21)

    # ATR
    result['ATR14'] = atr(df, 14)

    # RSI
    result['RSI14'] = rsi(df['Close'], 14)

    # Retornos
    ret = returns(df['Close'], [1, 5, 20])
    result['Ret1D'] = ret[1]
    result['Ret5D'] = ret[5]
    result['Ret20D'] = ret[20]

    # Volatilidad
    result['Vol20D'] = volatility(df['Close'], 20)

    # Distancia a máximos/mínimos
    result['DistHigh20'] = distance_to_high(df['Close'], 20)
    result['DistLow20'] = distance_to_low(df['Close'], 20)

    # Ratio de volumen
    result['VolRatio'] = volume_ratio(df['Volume'], 20)

    # ATR en porcentaje
    result['ATRpct'] = result['ATR14'] / df['Close'] * 100

    # ¿Está sobre EMA21?
    result['AboveEMA21'] = df['Close'] > result['EMA21']

    return result


def get_latest_indicators(df):
    """
    Extrae los indicadores de la última fila.

    Args:
        df: DataFrame con indicadores (de calculate_all_indicators)

    Returns:
        Dict con indicadores de la última fecha
    """
    if df.empty:
        return None

    last = df.iloc[-1]

    return {
        'date': df.index[-1].strftime('%Y-%m-%d'),
        'price': _finite(last['Close']),
        'EMA9': _finite(last.get('EMA9', 0)),
        'EMA21': _finite(last.get('EMA21', 0)),
        'ATR14': _finite(last.get('ATR14', 0)),
        'RSI14': _finite(last.get('RSI14', 50), 50.0),
        'Ret1D': _finite(last.get('Ret1D', 0)),
        'Ret5D': _finite(last.get('Ret5D', 0)),
        'Ret20D': _finite(last.get('Ret20D', 0)),
        'Vol20D': _finite(last.get('Vol20D', 0)),
        'DistHigh20': _finite(last.get('DistHigh20', 0)),
        'DistLow20': _finite(last.get('DistLow20', 0)),
        'VolRatio': _finite(last.get('VolRatio', 1.0), 1.0),
        'ATRpct': _finite(last.get('ATRpct', 0)),
        'AboveEMA21': bool(last.get('AboveEMA21', False)),
    }

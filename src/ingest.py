"""
Módulo de ingesta de datos desde yfinance.
Descarga velas D1 y W1 para todos los activos del universo.
"""

import logging

import pandas as pd
import yfinance as yf

from config.universe import get_all_tickers
from src.paths import RAW_DATA_DIR

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ('Open', 'High', 'Low', 'Close', 'Volume')
MIN_ROWS = 30


def download_ticker_data(ticker, period='1y', interval='1d'):
    """
    Descarga datos OHLCV de un ticker.

    Args:
        ticker: Símbolo del activo
        period: Período de datos (default: 1 año)
        interval: Intervalo de velas (1d, 1wk)

    Returns:
        DataFrame con OHLCV o None si falla
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)

        if df.empty:
            logger.warning('%s: no data returned by yfinance', ticker)
            return None

        missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
        if missing:
            logger.warning('%s: missing columns %s', ticker, missing)
            return None

        df = df[list(REQUIRED_COLUMNS)].dropna()
        df.index = pd.to_datetime(df.index)

        if len(df) < MIN_ROWS:
            logger.warning('%s: only %s rows; skipping', ticker, len(df))
            return None

        return df

    except Exception as exc:  # noqa: BLE001 - a single failed ticker must not abort the run
        logger.error('%s: download failed: %s', ticker, exc)
        return None


def download_all_data(tickers=None, period='1y', save=True):
    """
    Descarga datos de todos los tickers del universo.

    Args:
        tickers: Lista de tickers (default: todos del universo)
        period: Período de datos
        save: Si True, guarda en data/raw/

    Returns:
        Dict con {ticker: DataFrame}
    """
    if tickers is None:
        tickers = get_all_tickers()

    logger.info('Downloading daily data for %s tickers', len(tickers))

    data = {}
    for ticker in tickers:
        df = download_ticker_data(ticker, period=period, interval='1d')
        if df is not None:
            data[ticker] = df

            if save:
                RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
                filepath = RAW_DATA_DIR / f'{ticker}_daily.csv'
                df.to_csv(filepath)

    logger.info('Downloaded %s/%s daily series', len(data), len(tickers))
    return data


def download_weekly_data(tickers=None, period='1y', save=True):
    """
    Descarga datos semanales de todos los tickers.
    """
    if tickers is None:
        tickers = get_all_tickers()

    logger.info('Downloading weekly data for %s tickers', len(tickers))

    data = {}
    for ticker in tickers:
        df = download_ticker_data(ticker, period=period, interval='1wk')
        if df is not None:
            data[ticker] = df

            if save:
                RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
                filepath = RAW_DATA_DIR / f'{ticker}_weekly.csv'
                df.to_csv(filepath)

    logger.info('Downloaded %s/%s weekly series', len(data), len(tickers))
    return data


def load_ticker_data(ticker, interval='daily'):
    """
    Carga datos de un ticker desde data/raw/.

    Args:
        ticker: Símbolo del activo
        interval: "daily" o "weekly"

    Returns:
        DataFrame o None si no existe
    """
    suffix = 'daily' if interval == 'daily' else 'weekly'
    filepath = RAW_DATA_DIR / f'{ticker}_{suffix}.csv'

    if not filepath.exists():
        return None

    return pd.read_csv(filepath, index_col=0, parse_dates=True)


if __name__ == '__main__':
    # Test: descargar datos de todos los activos
    daily_data = download_all_data()
    weekly_data = download_weekly_data()

    print('\n📊 Resumen:')
    print(f'  Diarios: {len(daily_data)} activos')
    print(f'  Semanales: {len(weekly_data)} activos')

"""Shared data-pipeline helpers.

Keeping universe ingestion and ranking in one place avoids duplicating the
same download/indicator logic in the CLI and the executive report.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd

from config.universe import get_all_tickers
from src.indicators import calculate_all_indicators, get_latest_indicators
from src.ingest import download_all_data
from src.scoring import rank_universe

logger = logging.getLogger(__name__)


def build_universe_indicators(
    tickers: Optional[List[str]] = None,
    period: str = '1y',
    save: bool = True,
) -> Tuple[Dict[str, dict], Dict[str, pd.DataFrame]]:
    """Download data and compute the latest indicators for every ticker.

    Returns
    -------
    tuple[dict, dict]
        ``({ticker: indicators}, {ticker: dataframe})``.
    """
    tickers = tickers or get_all_tickers()
    data = download_all_data(tickers, period=period, save=save)

    indicators: Dict[str, dict] = {}
    for ticker, df in data.items():
        try:
            latest = get_latest_indicators(calculate_all_indicators(df))
        except Exception as exc:  # noqa: BLE001 - keep one bad ticker from killing the run
            logger.warning('Could not compute indicators for %s: %s', ticker, exc)
            continue
        if latest:
            indicators[ticker] = latest

    return indicators, data


def build_ranked_universe(
    tickers: Optional[List[str]] = None,
    period: str = '1y',
    save: bool = True,
) -> Tuple[List[dict], Dict[str, dict]]:
    """Return the ranked universe plus the raw indicator map."""
    indicators, _ = build_universe_indicators(tickers=tickers, period=period, save=save)
    return rank_universe(indicators), indicators

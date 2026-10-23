"""
Fundamental analysis module.
Provides fundamental data for stocks and ETFs using Finnhub and yfinance.
"""

import logging
from datetime import datetime
from typing import Dict, List

import requests
import yfinance as yf

from config.secrets import get_secrets

logger = logging.getLogger(__name__)

FINNHUB_BASE = 'https://finnhub.io/api/v1'
REQUEST_TIMEOUT = 10


def is_etf(ticker: str) -> bool:
    """
    Detect if a ticker is an ETF.

    Args:
        ticker: Stock ticker symbol

    Returns:
        True if ETF, False if stock
    """
    # Known ETFs in our universe
    etf_list = [
        'XLF',
        'XLE',
        'XLK',
        'XBI',
        'SMH',
        'XLU',
        'XLI',
        'GDX',
        'TQQQ',
        'SOXL',
        'FNGU',
        'SQQQ',
        'SOXS',
        'PSQ',
        'SPDN',
        'SGOV',
        'BIL',
        'SHY',
    ]
    return ticker.upper() in etf_list


def get_stock_fundamentals(ticker: str) -> Dict:
    """
    Get fundamental data for a stock using Finnhub API.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dictionary with fundamental metrics
    """
    secrets = get_secrets()
    api_key = secrets.get('FINNHUB_API_KEY')

    if not api_key:
        logger.warning(f'No Finnhub API key found for {ticker}')
        return {}

    try:
        headers = {'X-Finnhub-Token': api_key}

        # Company profile
        profile_url = f'{FINNHUB_BASE}/stock/profile2?symbol={ticker}'
        profile_resp = requests.get(profile_url, headers=headers, timeout=REQUEST_TIMEOUT)
        profile = profile_resp.json() if profile_resp.status_code == 200 else {}

        # Basic financials (metrics)
        metrics_url = f'{FINNHUB_BASE}/stock/metric?symbol={ticker}&metric=all'
        metrics_resp = requests.get(metrics_url, headers=headers, timeout=REQUEST_TIMEOUT)
        metrics_data = metrics_resp.json() if metrics_resp.status_code == 200 else {}
        metrics = metrics_data.get('metric', {})

        # Recommendation trends
        rec_url = f'{FINNHUB_BASE}/stock/recommendation?symbol={ticker}'
        rec_resp = requests.get(rec_url, headers=headers, timeout=REQUEST_TIMEOUT)
        recommendations = rec_resp.json() if rec_resp.status_code == 200 else []

        # Earnings calendar
        earnings_url = f'{FINNHUB_BASE}/calendar/earnings?symbol={ticker}'
        earnings_resp = requests.get(earnings_url, headers=headers, timeout=REQUEST_TIMEOUT)
        earnings_data = earnings_resp.json() if earnings_resp.status_code == 200 else {}

        fundamentals = {
            'ticker': ticker,
            'type': 'stock',
            'name': profile.get('name', ''),
            'industry': profile.get('finnhubIndustry', ''),
            'sector': profile.get('sector', ''),
            'market_cap': profile.get('marketCapitalization', 0),
            'country': profile.get('country', ''),
            'currency': profile.get('currency', 'USD'),
            # Valuation metrics
            'pe_ratio': metrics.get('peBasicExclExtraTTM', None),
            'pe_ratio_fwd': metrics.get('peNormalizedAnnual', None),
            'pb_ratio': metrics.get('pbAnnual', None),
            'ps_ratio': metrics.get('psTTM', None),
            'ev_to_ebitda': metrics.get('evToEbitda', None),
            # Profitability
            'gross_margin': metrics.get('grossMargin', None),
            'operating_margin': metrics.get('operatingMargin', None),
            'net_margin': metrics.get('netMargin', None),
            'roe': metrics.get('roe', None),
            'roa': metrics.get('roa', None),
            # Growth
            'revenue_growth': metrics.get('revenueGrowth', None),
            'earnings_growth': metrics.get('earningsGrowth', None),
            # Financial health
            'debt_to_equity': metrics.get('totalDebt/totalEquity', None),
            'current_ratio': metrics.get('currentRatio', None),
            'quick_ratio': metrics.get('quickRatio', None),
            # Dividends
            'dividend_yield': metrics.get('dividendYield', None),
            'payout_ratio': metrics.get('payoutRatio', None),
            # Analyst recommendations
            'recommendations': recommendations[:5] if recommendations else [],
            # Next earnings date
            'next_earnings': None,
        }

        # Extract next earnings date
        if earnings_data and 'earningsCalendar' in earnings_data:
            earnings_list = earnings_data['earningsCalendar']
            if earnings_list:
                # Sort by date and get the next one
                future_earnings = [
                    e
                    for e in earnings_list
                    if e.get('date', '') >= datetime.now().strftime('%Y-%m-%d')
                ]
                if future_earnings:
                    fundamentals['next_earnings'] = future_earnings[0].get('date')

        return fundamentals

    except Exception as e:
        logger.error(f'Error fetching fundamentals for {ticker}: {e}')
        return {}


def get_etf_fundamentals(ticker: str) -> Dict:
    """
    Get fundamental data for an ETF using yfinance.

    Args:
        ticker: ETF ticker symbol

    Returns:
        Dictionary with ETF metrics
    """
    try:
        etf = yf.Ticker(ticker)
        info = etf.info

        fundamentals = {
            'ticker': ticker,
            'type': 'etf',
            'name': info.get('longName', ''),
            'category': info.get('category', ''),
            'fund_family': info.get('fundFamily', ''),
            # Size and liquidity
            'total_assets': info.get('totalAssets', 0),
            'avg_volume': info.get('averageVolume', 0),
            'avg_volume_10d': info.get('averageVolume10days', 0),
            # Costs
            'expense_ratio': info.get('annualReportExpenseRatio', None),
            # Yield
            'dividend_yield': info.get('yield', None),
            'yield_3y': info.get('threeYearAverageReturn', None),
            # Performance
            'beta_3y': info.get('beta3Year', None),
            'ytd_return': info.get('ytdReturn', None),
            'return_3y': info.get('threeYearAverageReturn', None),
            'return_5y': info.get('fiveYearAverageReturn', None),
            # Holdings
            'num_holdings': info.get('numberOfHoldings', None),
            # Top holdings (if available)
            'top_holdings': [],
            # Sector weights (if available)
            'sector_weights': {},
        }

        # Try to get holdings
        try:
            holdings = etf.funds_data.top_holdings
            if holdings is not None and not holdings.empty:
                fundamentals['top_holdings'] = holdings.head(10).to_dict('records')
        except Exception as e:
            logger.debug(f'Could not fetch holdings for {ticker}: {e}')

        # Try to get sector weights
        try:
            sector_weights = etf.funds_data.sector_weightings
            if sector_weights is not None and not sector_weights.empty:
                fundamentals['sector_weights'] = sector_weights.to_dict('records')
        except Exception as e:
            logger.debug(f'Could not fetch sector weights for {ticker}: {e}')

        return fundamentals

    except Exception as e:
        logger.error(f'Error fetching ETF fundamentals for {ticker}: {e}')
        return {}


def get_fundamentals(ticker: str) -> Dict:
    """
    Get fundamental data for any ticker (stock or ETF).

    Args:
        ticker: Ticker symbol

    Returns:
        Dictionary with fundamental metrics
    """
    if is_etf(ticker):
        return get_etf_fundamentals(ticker)
    else:
        return get_stock_fundamentals(ticker)


def get_fundamentals_batch(tickers: List[str]) -> Dict[str, Dict]:
    """
    Get fundamental data for multiple tickers.

    Args:
        tickers: List of ticker symbols

    Returns:
        Dictionary mapping ticker to fundamentals
    """
    results = {}
    for ticker in tickers:
        logger.info(f'Fetching fundamentals for {ticker}...')
        results[ticker] = get_fundamentals(ticker)
    return results


def valuation_verdict(fundamentals: Dict) -> str:
    """
    Generate a simple valuation verdict based on fundamentals.

    Args:
        fundamentals: Dictionary with fundamental metrics

    Returns:
        Verdict string: 'cheap', 'fair', 'expensive', or 'unknown'
    """
    if fundamentals.get('type') == 'etf':
        return 'N/A (ETF)'

    pe = fundamentals.get('pe_ratio')
    pb = fundamentals.get('pb_ratio')

    # Simple heuristic based on P/E and P/B
    if pe is None or pb is None:
        return 'unknown'

    # Very rough thresholds (should be sector-adjusted in production)
    if pe < 15 and pb < 2:
        return 'cheap'
    elif pe > 30 or pb > 5:
        return 'expensive'
    else:
        return 'fair'


if __name__ == '__main__':
    # Test with a few tickers
    test_tickers = ['AAPL', 'NVDA', 'TQQQ', 'XLF']

    for ticker in test_tickers:
        print(f'\n{"=" * 60}')
        print(f'Fundamentals for {ticker}:')
        print('=' * 60)

        fund = get_fundamentals(ticker)

        if fund:
            print(f'Type: {fund.get("type")}')
            print(f'Name: {fund.get("name")}')

            if fund.get('type') == 'stock':
                print(f'Industry: {fund.get("industry")}')
                print(f'Market Cap: ${fund.get("market_cap", 0):,.0f}M')
                print(f'P/E Ratio: {fund.get("pe_ratio")}')
                print(f'P/B Ratio: {fund.get("pb_ratio")}')
                print(f'ROE: {fund.get("roe")}')
                print(f'Revenue Growth: {fund.get("revenue_growth")}')
                print(f'Dividend Yield: {fund.get("dividend_yield")}')
                print(f'Next Earnings: {fund.get("next_earnings")}')
                print(f'Verdict: {valuation_verdict(fund)}')
            else:
                print(f'Category: {fund.get("category")}')
                print(f'Total Assets: ${fund.get("total_assets", 0):,.0f}')
                print(f'Expense Ratio: {fund.get("expense_ratio")}')
                print(f'Dividend Yield: {fund.get("dividend_yield")}')
                print(f'Beta (3Y): {fund.get("beta_3y")}')
                print(f'Number of Holdings: {fund.get("num_holdings")}')
        else:
            print('No data available')

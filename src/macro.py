"""
Macro module - Market regime detection and macroeconomic data.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict

import pandas as pd
import yfinance as yf

from config.secrets import get_secrets

logger = logging.getLogger(__name__)


def get_vix_data(period: str = '1y') -> pd.DataFrame:
    """
    Get VIX (volatility index) data.

    Args:
        period: Data period (default: '1y')

    Returns:
        DataFrame with VIX data
    """
    try:
        vix = yf.Ticker('^VIX')
        df = vix.history(period=period)
        return df
    except Exception as e:
        logger.error(f'Error fetching VIX data: {e}')
        return pd.DataFrame()


def get_market_indices(period: str = '1y') -> Dict[str, pd.DataFrame]:
    """
    Get major market indices data.

    Args:
        period: Data period (default: '1y')

    Returns:
        Dictionary with index data (SPY, QQQ, IWM)
    """
    indices = {'SPY': 'S&P 500', 'QQQ': 'Nasdaq 100', 'IWM': 'Russell 2000'}

    data = {}
    for ticker, name in indices.items():
        try:
            df = yf.Ticker(ticker).history(period=period)
            data[ticker] = df
        except Exception as e:
            logger.error(f'Error fetching {name} data: {e}')

    return data


def get_treasury_yields(period: str = '1y') -> Dict[str, pd.DataFrame]:
    """
    Get US Treasury yields data from FRED.

    Args:
        period: Data period (default: '1y')

    Returns:
        Dictionary with yield data (10Y, 2Y)
    """
    try:
        from fredapi import Fred

        secrets = get_secrets()
        fred_api_key = secrets.get('FRED_API_KEY')

        if not fred_api_key:
            logger.warning('FRED_API_KEY not found, using yfinance fallback')
            return _get_treasury_yields_yfinance(period)

        fred = Fred(api_key=fred_api_key)

        # Get 10-year Treasury yield
        dgs10 = fred.get_series(
            'DGS10', observation_start=(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        )

        # Get 2-year Treasury yield
        dgs2 = fred.get_series(
            'DGS2', observation_start=(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        )

        # Combine into DataFrame
        df = pd.DataFrame({'10Y': dgs10, '2Y': dgs2}).dropna()

        return {'TREASURY': df}

    except Exception as e:
        logger.error(f'Error fetching Treasury yields from FRED: {e}')
        return _get_treasury_yields_yfinance(period)


def _get_treasury_yields_yfinance(period: str = '1y') -> Dict[str, pd.DataFrame]:
    """
    Fallback: Get Treasury yields from yfinance.

    Args:
        period: Data period

    Returns:
        Dictionary with yield data
    """
    try:
        # 10-year Treasury
        tnx = yf.Ticker('^TNX')
        dgs10 = tnx.history(period=period)['Close']

        # 2-year Treasury
        # Note: ^IRX is 13-week T-bill, not 2Y. Using ^TYX as proxy
        tyx = yf.Ticker('^TYX')
        dgs2 = tyx.history(period=period)['Close']

        df = pd.DataFrame({'10Y': dgs10, '2Y': dgs2}).dropna()

        return {'TREASURY': df}

    except Exception as e:
        logger.error(f'Error fetching Treasury yields from yfinance: {e}')
        return {}


def get_dollar_index(period: str = '1y') -> pd.DataFrame:
    """
    Get US Dollar Index (DXY) data.

    Args:
        period: Data period (default: '1y')

    Returns:
        DataFrame with DXY data
    """
    try:
        dxy = yf.Ticker('DX-Y.NYB')
        df = dxy.history(period=period)
        return df
    except Exception as e:
        logger.error(f'Error fetching DXY data: {e}')
        return pd.DataFrame()


def calculate_market_regime() -> Dict:
    """
    Calculate current market regime based on multiple indicators.

    Returns:
        Dictionary with regime classification and supporting data
    """
    regime_data = {
        'timestamp': datetime.now().isoformat(),
        'regime': 'NEUTRAL',
        'confidence': 0.0,
        'indicators': {},
        'details': {},
    }

    risk_on_score = 0
    risk_off_score = 0
    total_indicators = 0

    # 1. VIX Analysis
    try:
        vix_data = get_vix_data(period='3mo')
        if not vix_data.empty:
            vix_current = vix_data['Close'].iloc[-1]
            vix_20d_avg = vix_data['Close'].rolling(window=20).mean().iloc[-1]

            regime_data['indicators']['VIX'] = {
                'current': float(vix_current),
                '20d_avg': float(vix_20d_avg),
            }

            total_indicators += 1
            if vix_current < 15:
                risk_on_score += 2
                regime_data['details']['VIX'] = 'Very low volatility - RISK ON'
            elif vix_current < 20:
                risk_on_score += 1
                regime_data['details']['VIX'] = 'Low volatility - RISK ON'
            elif vix_current < 25:
                regime_data['details']['VIX'] = 'Moderate volatility - NEUTRAL'
            elif vix_current < 30:
                risk_off_score += 1
                regime_data['details']['VIX'] = 'High volatility - RISK OFF'
            else:
                risk_off_score += 2
                regime_data['details']['VIX'] = 'Very high volatility - RISK OFF'
    except Exception as e:
        logger.error(f'Error analyzing VIX: {e}')

    # 2. Market Trend Analysis (SPY vs 200-day MA)
    try:
        spy_data = get_market_indices(period='1y')['SPY']
        if not spy_data.empty:
            spy_current = spy_data['Close'].iloc[-1]
            spy_200ma = spy_data['Close'].rolling(window=200).mean().iloc[-1]
            spy_50ma = spy_data['Close'].rolling(window=50).mean().iloc[-1]

            regime_data['indicators']['SPY'] = {
                'current': float(spy_current),
                '200d_ma': float(spy_200ma),
                '50d_ma': float(spy_50ma),
                'above_200ma': bool(spy_current > spy_200ma),
                'above_50ma': bool(spy_current > spy_50ma),
            }

            total_indicators += 1
            if spy_current > spy_200ma and spy_current > spy_50ma:
                risk_on_score += 2
                regime_data['details']['SPY'] = 'Above 50d and 200d MA - RISK ON'
            elif spy_current > spy_200ma:
                risk_on_score += 1
                regime_data['details']['SPY'] = 'Above 200d MA - RISK ON'
            elif spy_current < spy_200ma and spy_current < spy_50ma:
                risk_off_score += 2
                regime_data['details']['SPY'] = 'Below 50d and 200d MA - RISK OFF'
            else:
                risk_off_score += 1
                regime_data['details']['SPY'] = 'Below 200d MA - RISK OFF'
    except Exception as e:
        logger.error(f'Error analyzing SPY: {e}')

    # 3. Yield Curve Analysis
    try:
        treasury_data = get_treasury_yields(period='3mo')
        if 'TREASURY' in treasury_data and not treasury_data['TREASURY'].empty:
            treasury_df = treasury_data['TREASURY']
            yield_10y = treasury_df['10Y'].iloc[-1]
            yield_2y = treasury_df['2Y'].iloc[-1]
            spread = yield_10y - yield_2y

            regime_data['indicators']['YIELD_CURVE'] = {
                '10Y': float(yield_10y),
                '2Y': float(yield_2y),
                'spread': float(spread),
                'inverted': bool(spread < 0),
            }

            total_indicators += 1
            if spread > 1.0:
                risk_on_score += 2
                regime_data['details']['YIELD_CURVE'] = 'Steep positive spread - RISK ON'
            elif spread > 0:
                risk_on_score += 1
                regime_data['details']['YIELD_CURVE'] = 'Positive spread - RISK ON'
            elif spread > -0.5:
                regime_data['details']['YIELD_CURVE'] = 'Slightly inverted - NEUTRAL'
            else:
                risk_off_score += 2
                regime_data['details']['YIELD_CURVE'] = 'Deeply inverted - RISK OFF'
    except Exception as e:
        logger.error(f'Error analyzing yield curve: {e}')

    # 4. Dollar Strength Analysis
    try:
        dxy_data = get_dollar_index(period='3mo')
        if not dxy_data.empty:
            dxy_current = dxy_data['Close'].iloc[-1]
            dxy_20d_avg = dxy_data['Close'].rolling(window=20).mean().iloc[-1]
            dxy_trend = (dxy_current - dxy_20d_avg) / dxy_20d_avg * 100

            regime_data['indicators']['DXY'] = {
                'current': float(dxy_current),
                '20d_avg': float(dxy_20d_avg),
                'trend_pct': float(dxy_trend),
            }

            total_indicators += 1
            if dxy_trend < -2:
                risk_on_score += 1
                regime_data['details']['DXY'] = 'Weakening dollar - RISK ON'
            elif dxy_trend > 2:
                risk_off_score += 1
                regime_data['details']['DXY'] = 'Strengthening dollar - RISK OFF'
            else:
                regime_data['details']['DXY'] = 'Stable dollar - NEUTRAL'
    except Exception as e:
        logger.error(f'Error analyzing DXY: {e}')

    # Determine regime
    if total_indicators > 0:
        if risk_on_score >= 3:
            regime_data['regime'] = 'RISK_ON'
            regime_data['confidence'] = min(risk_on_score / (total_indicators * 2), 1.0)
        elif risk_off_score >= 3:
            regime_data['regime'] = 'RISK_OFF'
            regime_data['confidence'] = min(risk_off_score / (total_indicators * 2), 1.0)
        else:
            regime_data['regime'] = 'NEUTRAL'
            regime_data['confidence'] = 1.0 - (
                abs(risk_on_score - risk_off_score) / (total_indicators * 2)
            )

    return regime_data


def is_leveraged_etf_allowed(regime: str) -> bool:
    """
    Check if leveraged ETFs are allowed in current regime.

    Args:
        regime: Current market regime ('RISK_ON', 'NEUTRAL', 'RISK_OFF')

    Returns:
        True if leveraged ETFs are allowed, False otherwise
    """
    return regime == 'RISK_ON'


def is_inverse_etf_allowed(regime: str) -> bool:
    """
    Check if inverse ETFs are allowed in current regime.

    Args:
        regime: Current market regime ('RISK_ON', 'NEUTRAL', 'RISK_OFF')

    Returns:
        True if inverse ETFs are allowed, False otherwise
    """
    return regime == 'RISK_OFF'


def get_regime_recommendation() -> Dict:
    """
    Get trading recommendations based on current regime.

    Returns:
        Dictionary with regime and trading recommendations
    """
    regime_data = calculate_market_regime()
    regime = regime_data['regime']

    recommendations = {
        'RISK_ON': {
            'description': 'Bull market conditions - aggressive strategies allowed',
            'leveraged_etfs': True,
            'inverse_etfs': False,
            'cash_proxy': False,
            'strategy': 'Momentum and trend-following strategies',
            'position_size': 'Full position allowed',
        },
        'NEUTRAL': {
            'description': 'Mixed conditions - moderate strategies',
            'leveraged_etfs': False,
            'inverse_etfs': False,
            'cash_proxy': False,
            'strategy': 'Selective opportunities, avoid leverage',
            'position_size': 'Full position allowed but prefer quality',
        },
        'RISK_OFF': {
            'description': 'Bear market conditions - defensive strategies',
            'leveraged_etfs': False,
            'inverse_etfs': True,
            'cash_proxy': True,
            'strategy': 'Defensive positions, inverse ETFs, or cash proxy',
            'position_size': 'Reduce exposure or move to cash proxy',
        },
    }

    result = regime_data.copy()
    result['recommendations'] = recommendations.get(regime, recommendations['NEUTRAL'])

    return result


if __name__ == '__main__':
    # Test regime calculation
    print('Calculating market regime...')
    print('=' * 60)

    regime_data = get_regime_recommendation()

    print(f'\nMarket Regime: {regime_data["regime"]}')
    print(f'Confidence: {regime_data["confidence"]:.2%}')
    print(f'Timestamp: {regime_data["timestamp"]}')

    print('\nIndicators:')
    for indicator, data in regime_data['indicators'].items():
        print(f'  {indicator}: {data}')

    print('\nDetails:')
    for key, detail in regime_data['details'].items():
        print(f'  {key}: {detail}')

    print('\nRecommendations:')
    rec = regime_data['recommendations']
    print(f'  Description: {rec["description"]}')
    print(f'  Leveraged ETFs: {"✓" if rec["leveraged_etfs"] else "✗"}')
    print(f'  Inverse ETFs: {"✓" if rec["inverse_etfs"] else "✗"}')
    print(f'  Cash Proxy: {"✓" if rec["cash_proxy"] else "✗"}')
    print(f'  Strategy: {rec["strategy"]}')
    print(f'  Position Size: {rec["position_size"]}')

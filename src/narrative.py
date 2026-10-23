"""
Narrative module - Recopila todos los datos para el reporte ejecutivo.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import yfinance as yf

from src.fundamentals import get_fundamentals
from src.indicators import calculate_all_indicators, get_latest_indicators
from src.macro import calculate_market_regime
from src.news import get_news_summary
from src.paths import OUTPUT_DIR, STATE_DIR
from src.technicals_deep import calculate_all_advanced, get_latest_advanced

logger = logging.getLogger(__name__)


def get_position_data(ticker: str) -> dict:
    """
    Obtiene todos los datos técnicos para un ticker.

    Args:
        ticker: Símbolo del ticker

    Returns:
        Dict con indicadores técnicos básicos y avanzados
    """
    try:
        # Descargar datos
        data = yf.download(ticker, period='6mo', interval='1d', progress=False)

        if data.empty:
            logger.error(f'No data for {ticker}')
            return {}

        # Aplanar columnas MultiIndex si existen
        if hasattr(data.columns, 'levels'):
            data.columns = data.columns.droplevel(1)

        # Calcular indicadores básicos
        indicators_df = calculate_all_indicators(data)
        basic = get_latest_indicators(indicators_df)

        # Calcular indicadores avanzados
        advanced_df = calculate_all_advanced(data)
        advanced = get_latest_advanced(advanced_df)

        # Extraer valores con nombres correctos
        basic_values = {
            'price': basic.get('price', 0),
            'ema21': basic.get('EMA21', 0),
            'rsi14': basic.get('RSI14', 50),
            'atr14': basic.get('ATR14', 0),
            'atr_pct': basic.get('ATRpct', 0),
            'above_ema21': basic.get('AboveEMA21', False),
            'ret5d': basic.get('Ret5D', 0),
            'ret20d': basic.get('Ret20D', 0),
            'dist_high20': basic.get('DistHigh20', 0),
        }

        return {'basic': basic_values, 'advanced': advanced}

    except Exception as e:
        logger.error(f'Error getting position data for {ticker}: {e}')
        return {}


def generate_dossier(portfolio_path: str = None) -> dict:
    """
    Genera el dossier completo con todos los datos para el reporte ejecutivo.

    Args:
        portfolio_path: Ruta al archivo portfolio.json (default: state/portfolio.json)

    Returns:
        Dict con todos los datos estructurados
    """
    path = Path(portfolio_path) if portfolio_path else STATE_DIR / 'portfolio.json'
    with open(path, 'r', encoding='utf-8') as f:
        portfolio = json.load(f)

    position_ticker = portfolio['position']['ticker']
    logger.info(f'Generating dossier for {position_ticker}')

    # Obtener datos técnicos (con defaults si falla la red)
    position_data = get_position_data(position_ticker) or {}
    basic = position_data.get('basic', {})
    advanced = position_data.get('advanced', {})

    # Obtener fundamentales
    fundamentals = get_fundamentals(position_ticker)

    # Obtener macro
    macro_regime = calculate_market_regime()

    # Obtener noticias
    news_summary = get_news_summary(position_ticker, days=7)

    # Construir dossier
    dossier = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'ticker': position_ticker,
        'regime': macro_regime['regime'],
        'regime_confidence': macro_regime['confidence'],
        # Portafolio
        'position': {
            'ticker': position_ticker,
            'entry_price': portfolio['position']['entry_price_usd'],
            'entry_date': portfolio['position']['entry_date'],
            'stop_loss': portfolio['position'].get('stop_loss_usd', 0),
        },
        'capital': {
            'initial_mxn': portfolio['capital']['initial_mxn'],
            'current_mxn': portfolio['capital']['current_mxn'],
            'return_pct': portfolio['capital']['return_pct'],
        },
        # Técnicos
        'technicals': {
            'price': round(basic.get('price', 0), 2),
            'ema21': round(basic.get('ema21', 0), 2),
            'rsi': round(basic.get('rsi14', 50), 1),
            'atr': round(basic.get('atr14', 0), 2),
            'atr_pct': round(basic.get('atr_pct', 0), 2),
            'above_ema21': basic.get('above_ema21', False),
            'ret_5d': round(basic.get('ret5d', 0), 2),
            'ret_20d': round(basic.get('ret20d', 0), 2),
            'dist_high': round(basic.get('dist_high20', 0), 2),
        },
        # Técnicos avanzados
        'advanced': {
            'macd': round(advanced.get('MACD', 0), 3),
            'macd_bullish': advanced.get('MACD_Bullish', False),
            'adx': round(advanced.get('ADX', 0), 1),
            'bb_percent_b': round(advanced.get('BB_Percent_B', 0), 3),
            'supertrend': round(advanced.get('Supertrend', 0), 2),
            'supertrend_bullish': advanced.get('Supertrend_Bullish', False),
            'market_structure': advanced.get('Market_Structure', 'unknown'),
            'current_setup': advanced.get('Current_Setup', 'neutral'),
            'support_levels': [round(s, 2) for s in advanced.get('Support_Levels', [])[:3]],
            'resistance_levels': [round(r, 2) for r in advanced.get('Resistance_Levels', [])[:3]],
        },
        # Fundamentales
        'fundamentals': fundamentals,
        # Macro
        'macro': {
            'vix': round(macro_regime['indicators'].get('VIX', {}).get('current', 0) or 0, 2),
            'spy_vs_200ma': round(
                (
                    (macro_regime['indicators'].get('SPY', {}).get('current', 0) or 0)
                    - (macro_regime['indicators'].get('SPY', {}).get('200d_ma', 0) or 0)
                )
                / (macro_regime['indicators'].get('SPY', {}).get('200d_ma', 1) or 1)
                * 100,
                2,
            ),
            'yield_curve': round(
                macro_regime['indicators'].get('YIELD_CURVE', {}).get('spread', 0) or 0,
                2,
            ),
            'dxy': round(macro_regime['indicators'].get('DXY', {}).get('current', 0) or 0, 2),
        },
        # Noticias
        'news': {
            'total_articles': news_summary.get('total_articles', 0),
            'sentiment': news_summary.get(
                'sentiment',
                {
                    'positive': 0,
                    'negative': 0,
                    'neutral': 0,
                    'average_sentiment': 0,
                    'sentiment_label': 'NEUTRAL',
                },
            ),
            'articles': news_summary.get('articles', [])[:5],
        },
        # Decisión
        'decision': 'HOLD',  # Se calculará en executive_report.py
        'rotation_candidate': None,
        'rotation_reasons': [],
        'next_review': portfolio.get('next_review', datetime.now().strftime('%Y-%m-%d')),
    }

    # Agregar veredicto de valuación si es acción
    if fundamentals.get('type') == 'stock':
        from src.fundamentals import valuation_verdict

        dossier['valuation_verdict'] = valuation_verdict(fundamentals)
    else:
        dossier['valuation_verdict'] = 'N/A'

    # Calcular stop loss con nuevo multiplicador por categoría
    from src.risk import calculate_stop_by_category, is_trade_suitable

    current_price = basic.get('price', portfolio['position']['entry_price_usd'])
    current_atr = basic.get('atr14', 0)

    if current_price > 0 and current_atr > 0:
        calculated_stop = calculate_stop_by_category(position_ticker, current_price, current_atr)
        dossier['position']['stop_loss_calculated'] = round(calculated_stop, 2)
        dossier['position']['stop_loss_risk_pct'] = round(
            (calculated_stop - current_price) / current_price * 100, 2
        )
        dossier['position']['suitable'] = is_trade_suitable(
            position_ticker, current_price, current_atr
        )

    return dossier


def save_dossier(dossier: dict, output_path: str = None):
    """
    Guarda el dossier en formato JSON.

    Args:
        dossier: Dict con el dossier
        output_path: Ruta del archivo de salida
    """
    path = Path(output_path) if output_path else OUTPUT_DIR / 'dossier.json'
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(dossier, f, indent=2, default=str)

    logger.info(f'Dossier saved to {path}')
    return path


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print('Generating dossier...')
    dossier = generate_dossier()

    print(f'\nDossier generated for {dossier["ticker"]}')
    print(f'Regime: {dossier["regime"]} ({dossier["regime_confidence"]:.1%})')
    print(f'Technical: EMA21=${dossier["technicals"]["ema21"]}, RSI={dossier["technicals"]["rsi"]}')
    print(f'Advanced: MACD={dossier["advanced"]["macd"]}, ADX={dossier["advanced"]["adx"]}')
    print(
        f'News: {dossier["news"]["total_articles"]} articles, sentiment={dossier["news"]["sentiment"]["sentiment_label"]}'
    )

    save_dossier(dossier)
    print('\nDossier saved to output/dossier.json')

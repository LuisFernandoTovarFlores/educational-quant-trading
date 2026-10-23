"""
Módulo de scoring compuesto.
Calcula score 0-100 basado en momentum, tendencia, volatilidad, liquidez y régimen.
"""

import math

from config.loader import get_config


def _finite(value, default: float = 0.0) -> float:
    """Return a finite float or the provided default."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _ideal_range(config_key: str, fallback):
    """Read an ``[min, max]`` range from settings.yaml."""
    value = get_config().get(config_key, fallback)
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return float(value[0]), float(value[1])
    return fallback


def score_momentum(indicators, weights=None):
    """
    Score de momentum basado en retornos de 5d y 20d.

    Args:
        indicators: Dict con Ret5D, Ret20D
        weights: Dict con ret5d_weight, ret20d_weight

    Returns:
        Score 0-100
    """
    if weights is None:
        config = get_config()
        weights = {
            'ret5d_weight': config.get('scoring.momentum.ret5d_weight', 0.4),
            'ret20d_weight': config.get('scoring.momentum.ret20d_weight', 0.6),
        }

    ret5d = _finite(indicators.get('Ret5D', 0))
    ret20d = _finite(indicators.get('Ret20D', 0))

    # Combinar retornos
    momentum_raw = ret5d * weights['ret5d_weight'] + ret20d * weights['ret20d_weight']

    # Normalizar a 0-100 (50 = neutro, >50 = positivo, <50 = negativo)
    # Rango típico: -20% a +20% → mapear a 0-100
    score = max(0, min(100, 50 + momentum_raw * 2))

    return score


def score_trend(indicators):
    """
    Score de tendencia basado en EMA21 y distancia a máximos.

    Args:
        indicators: Dict con AboveEMA21, DistHigh20

    Returns:
        Score 0-100
    """
    above_ema21 = indicators.get('AboveEMA21', False)
    dist_high = _finite(indicators.get('DistHigh20', 0))

    score = 0

    # 50 puntos por estar sobre EMA21
    if above_ema21:
        score += 50

    # 50 puntos por distancia a máximos (más cerca = mejor)
    # dist_high es negativo (ej: -5% = 5% debajo del máximo)
    # Mapear: 0% distancia = 50 pts, -10% distancia = 0 pts
    dist_score = max(0, min(50, 50 + dist_high * 5))
    score += dist_score

    return score


def score_volatility(indicators, ideal_range=None):
    """
    Score de volatilidad (ATR%).

    Args:
        indicators: Dict con ATRpct
        ideal_range: Tuple (min, max) del rango ideal

    Returns:
        Score 0-100
    """
    if ideal_range is None:
        ideal_range = _ideal_range('scoring.volatility.ideal_range', (2.0, 5.0))

    atr_pct = _finite(indicators.get('ATRpct', 0))
    if atr_pct <= 0:
        return 0

    # Rango ideal: 2-5% ATR
    if ideal_range[0] <= atr_pct <= ideal_range[1]:
        return 100
    elif atr_pct < ideal_range[0]:
        # Muy baja volatilidad
        return max(0, atr_pct * 50)
    else:
        # Muy alta volatilidad
        return max(0, 100 - (atr_pct - ideal_range[1]) * 10)


def score_liquidity(indicators, ideal_range=None):
    """
    Score de liquidez basado en ratio de volumen.

    Args:
        indicators: Dict con VolRatio
        ideal_range: Tuple (min, max) del rango ideal

    Returns:
        Score 0-100
    """
    if ideal_range is None:
        ideal_range = _ideal_range('scoring.liquidity.ideal_range', (0.8, 1.5))

    vol_ratio = _finite(indicators.get('VolRatio', 1.0), 1.0)
    if vol_ratio <= 0:
        return 0

    # Rango ideal: 0.8-1.5
    if ideal_range[0] <= vol_ratio <= ideal_range[1]:
        return 100
    elif vol_ratio < ideal_range[0]:
        # Volumen bajo
        return max(0, vol_ratio * 125)
    else:
        # Volumen muy alto
        return max(0, 100 - (vol_ratio - ideal_range[1]) * 20)


def score_regime(indicators, ideal_range=None):
    """
    Score de régimen basado en RSI.

    Args:
        indicators: Dict con RSI14
        ideal_range: Tuple (min, max) del rango ideal

    Returns:
        Score 0-100
    """
    if ideal_range is None:
        ideal_range = _ideal_range('scoring.regime.ideal_range', (50, 70))

    rsi = _finite(indicators.get('RSI14', 50), 50.0)

    # Rango ideal: 50-70 (momentum sin sobrecompra)
    if ideal_range[0] <= rsi <= ideal_range[1]:
        return 100
    elif rsi < ideal_range[0]:
        # Sobreventa
        return max(0, rsi * 2)
    else:
        # Sobrecompra
        return max(0, 100 - (rsi - ideal_range[1]) * 2)


def calculate_composite_score(indicators, weights=None):
    """
    Calcula score compuesto 0-100.

    Args:
        indicators: Dict con todos los indicadores
        weights: Dict con pesos de cada componente

    Returns:
        Dict con score total y componentes
    """
    if weights is None:
        weights = get_config().get(
            'scoring.weights',
            {
                'momentum': 0.30,
                'trend': 0.25,
                'volatility': 0.20,
                'liquidity': 0.10,
                'regime': 0.15,
            },
        )

    momentum = score_momentum(indicators)
    trend = score_trend(indicators)
    volatility = score_volatility(indicators)
    liquidity = score_liquidity(indicators)
    regime = score_regime(indicators)

    total = (
        momentum * weights['momentum']
        + trend * weights['trend']
        + volatility * weights['volatility']
        + liquidity * weights['liquidity']
        + regime * weights['regime']
    )

    return {
        'score': round(total, 1),
        'momentum': round(momentum, 1),
        'trend': round(trend, 1),
        'volatility': round(volatility, 1),
        'liquidity': round(liquidity, 1),
        'regime': round(regime, 1),
    }


def rank_universe(all_indicators, weights=None):
    """
    Rankea todos los activos del universo por score compuesto.

    Args:
        all_indicators: Dict {ticker: indicators_dict}
        weights: Pesos del scoring

    Returns:
        Lista de dicts ordenados por score (descendente)
    """
    results = []

    for ticker, indicators in all_indicators.items():
        score_data = calculate_composite_score(indicators, weights)
        results.append({'ticker': ticker, **score_data, **indicators})

    # Ordenar por score descendente
    results.sort(key=lambda x: x['score'], reverse=True)

    # Agregar rank
    for i, r in enumerate(results):
        r['rank'] = i + 1

    return results


def get_top_n(ranked, n=3):
    """
    Obtiene los top N activos.

    Args:
        ranked: Lista rankeada (de rank_universe)
        n: Número de activos

    Returns:
        Lista con top N
    """
    return ranked[:n]


def get_ticker_rank(ranked, ticker):
    """
    Obtiene el rank y score de un ticker específico.

    Args:
        ranked: Lista rankeada
        ticker: Ticker a buscar

    Returns:
        Dict con rank, score, y datos o None si no existe
    """
    for r in ranked:
        if r['ticker'] == ticker:
            return r
    return None


def is_in_top_percentile(ranked, ticker, percentile=30):
    """
    Verifica si un ticker está en el top X% del ranking.

    Args:
        ranked: Lista rankeada
        ticker: Ticker a verificar
        percentile: Percentil (ej: 30 = top 30%)

    Returns:
        Boolean
    """
    total = len(ranked)
    cutoff = max(1, int(total * percentile / 100))

    for i, r in enumerate(ranked):
        if r['ticker'] == ticker:
            return i < cutoff

    return False

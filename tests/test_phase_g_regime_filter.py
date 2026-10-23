"""
Tests para Fase G: Filtro de régimen de mercado en decision.py.
"""

import pytest

from src.decision import filter_by_regime, make_decision


@pytest.fixture
def sample_position():
    """Posición de ejemplo."""
    return {
        'ticker': 'TQQQ',
        'entry_price_usd': 81.01,
        'entry_date': '2026-10-02',
        'stop_loss_usd': 76.65,
    }


@pytest.fixture
def sample_indicators():
    """Indicadores de ejemplo."""
    return {
        'AboveEMA21': True,
        'EMA21': 75.71,
        'RSI14': 64.4,
        'ATR14': 2.9,
        'ATRpct': 3.57,
        'Ret5D': 1.77,
        'Ret20D': 12.68,
        'DistHigh20': 0.0,
    }


@pytest.fixture
def sample_ranked_universe():
    """Universo rankeado de ejemplo."""
    return [
        {
            'ticker': 'TQQQ',
            'score': 88.9,
            'AboveEMA21': True,
            'price': 81.01,
            'ATR14': 2.9,
            'DistHigh20': 0.0,
        },
        {
            'ticker': 'NVDA',
            'score': 86.0,
            'AboveEMA21': True,
            'price': 233.95,
            'ATR14': 5.91,
            'DistHigh20': -1.65,
        },
        {
            'ticker': 'SOXL',
            'score': 93.2,
            'AboveEMA21': True,
            'price': 163.71,
            'ATR14': 12.28,
            'DistHigh20': -3.56,
        },
        {
            'ticker': 'SGOV',
            'score': 56.3,
            'AboveEMA21': True,
            'price': 100.44,
            'ATR14': 0.04,
            'DistHigh20': -0.25,
        },
        {
            'ticker': 'SQQQ',
            'score': 50.6,
            'AboveEMA21': False,
            'price': 33.12,
            'ATR14': 1.45,
            'DistHigh20': -20.08,
        },
    ]


def test_filter_by_regime_risk_on(sample_ranked_universe):
    """Test: RISK_ON permite todos excepto cash proxy."""
    filtered = filter_by_regime(sample_ranked_universe, 'RISK_ON')

    tickers = [r['ticker'] for r in filtered]

    # SGOV (cash proxy) debe estar excluido
    assert 'SGOV' not in tickers

    # TQQQ, NVDA, SOXL (apalancados) deben estar incluidos
    assert 'TQQQ' in tickers
    assert 'NVDA' in tickers
    assert 'SOXL' in tickers


def test_filter_by_regime_neutral(sample_ranked_universe):
    """Test: NEUTRAL solo permite activos estándar."""
    filtered = filter_by_regime(sample_ranked_universe, 'NEUTRAL')

    tickers = [r['ticker'] for r in filtered]

    # Solo NVDA debe quedar (activo estándar)
    assert 'NVDA' in tickers

    # Apalancados, inversos y cash proxy deben estar excluidos
    assert 'TQQQ' not in tickers
    assert 'SOXL' not in tickers
    assert 'SQQQ' not in tickers
    assert 'SGOV' not in tickers


def test_filter_by_regime_risk_off(sample_ranked_universe):
    """Test: RISK_OFF solo permite cash proxy."""
    filtered = filter_by_regime(sample_ranked_universe, 'RISK_OFF')

    tickers = [r['ticker'] for r in filtered]

    # Solo SGOV debe quedar (cash proxy)
    assert 'SGOV' in tickers

    # Todos los demás deben estar excluidos
    assert 'TQQQ' not in tickers
    assert 'NVDA' not in tickers
    assert 'SOXL' not in tickers
    assert 'SQQQ' not in tickers


def test_make_decision_risk_on_hold(sample_position, sample_indicators, sample_ranked_universe):
    """Test: RISK_ON + condiciones Hold = HOLD."""
    decision = make_decision(
        sample_position,
        sample_indicators,
        sample_ranked_universe,
        earnings_next_week=False,
        regime='RISK_ON',
    )

    assert decision['action'] == 'HOLD'
    assert decision['ticker'] == 'TQQQ'


def test_make_decision_risk_off_force_cash_proxy(
    sample_position, sample_indicators, sample_ranked_universe
):
    """Test: RISK_OFF + activo apalancado = forzar rotación a cash proxy."""
    decision = make_decision(
        sample_position,
        sample_indicators,
        sample_ranked_universe,
        earnings_next_week=False,
        regime='RISK_OFF',
    )

    assert decision['action'] == 'ROTATE_TO_CASH_PROXY'
    assert decision['from_ticker'] == 'TQQQ'
    assert decision['to_ticker'] == 'SGOV'


def test_make_decision_neutral_force_standard():
    """Test: NEUTRAL + activo apalancado = forzar rotación a estándar."""
    position = {
        'ticker': 'SOXL',
        'entry_price_usd': 163.71,
        'entry_date': '2026-10-02',
        'stop_loss_usd': 150.0,
    }

    indicators = {
        'AboveEMA21': True,
        'EMA21': 137.6,
        'RSI14': 65.1,
        'ATR14': 12.28,
        'ATRpct': 7.5,
        'Ret5D': 8.1,
        'Ret20D': 53.47,
        'DistHigh20': -3.56,
    }

    ranked_universe = [
        {
            'ticker': 'SOXL',
            'score': 93.2,
            'AboveEMA21': True,
            'price': 163.71,
            'ATR14': 12.28,
            'DistHigh20': -3.56,
        },
        {
            'ticker': 'NVDA',
            'score': 86.0,
            'AboveEMA21': True,
            'price': 233.95,
            'ATR14': 5.91,
            'DistHigh20': -1.65,
        },
        {
            'ticker': 'TQQQ',
            'score': 88.9,
            'AboveEMA21': True,
            'price': 81.01,
            'ATR14': 2.9,
            'DistHigh20': 0.0,
        },
    ]

    decision = make_decision(
        position, indicators, ranked_universe, earnings_next_week=False, regime='NEUTRAL'
    )

    assert decision['action'] == 'ROTATE_TO_STANDARD'
    assert decision['from_ticker'] == 'SOXL'
    assert decision['to_ticker'] == 'NVDA'


def test_make_decision_risk_on_allows_leveraged():
    """Test: RISK_ON permite mantener activos apalancados."""
    position = {
        'ticker': 'TQQQ',
        'entry_price_usd': 81.01,
        'entry_date': '2026-10-02',
        'stop_loss_usd': 76.65,
    }

    indicators = {
        'AboveEMA21': True,
        'EMA21': 75.71,
        'RSI14': 64.4,
        'ATR14': 2.9,
        'ATRpct': 3.57,
        'Ret5D': 1.77,
        'Ret20D': 12.68,
        'DistHigh20': 0.0,
    }

    ranked_universe = [
        {
            'ticker': 'TQQQ',
            'score': 88.9,
            'rank': 1,
            'AboveEMA21': True,
            'price': 81.01,
            'ATR14': 2.9,
            'DistHigh20': 0.0,
        },
        {
            'ticker': 'NVDA',
            'score': 86.0,
            'rank': 2,
            'AboveEMA21': True,
            'price': 233.95,
            'ATR14': 5.91,
            'DistHigh20': -1.65,
        },
    ]

    decision = make_decision(
        position, indicators, ranked_universe, earnings_next_week=False, regime='RISK_ON'
    )

    # Debe mantener TQQQ (apalancado) en régimen RISK_ON
    # Puede ser HOLD o HOLD_WITH_WARNINGS, lo importante es que no rote
    assert decision['action'] in ['HOLD', 'HOLD_WITH_WARNINGS']
    assert decision['ticker'] == 'TQQQ'
    assert 'to_ticker' not in decision  # No debe haber rotación


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

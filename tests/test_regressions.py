"""Regression tests for the fixes documented in docs/OPEN_SOURCE_AUDIT.md.

These tests are intentionally offline and deterministic.
"""

from __future__ import annotations

import json
from datetime import date, datetime

import pandas as pd
import pytest

from src.accounting import _week_key, apply_commission, charge_weekly_fee, update_return_pct
from src.decision import check_rotate_conditions, execute_rotation
from src.earnings import is_earnings_next_week
from src.indicators import calculate_all_indicators, get_latest_indicators
from src.report import export_screener_csv, generate_weekly_report
from src.risk import generate_stop_report
from src.scoring import score_momentum, score_volatility


def _ohlcv(rows=5):
    index = pd.date_range('2026-01-01', periods=rows, freq='D')
    close = pd.Series(range(100, 100 + rows), index=index, dtype=float)
    return pd.DataFrame(
        {
            'Open': close,
            'High': close + 1,
            'Low': close - 1,
            'Close': close,
            'Volume': 1_000_000,
        },
        index=index,
    )


def _candidate(ticker, score, price=100.0, atr=2.0, above_ema=True, dist_high=-10.0):
    return {
        'ticker': ticker,
        'rank': 1,
        'score': score,
        'price': price,
        'ATR14': atr,
        'ATRpct': atr / price * 100,
        'AboveEMA21': above_ema,
        'DistHigh20': dist_high,
        'RSI14': 60.0,
        'Ret5D': 2.0,
        'Ret20D': 8.0,
        'VolRatio': 1.0,
        'momentum': 70.0,
        'trend': 80.0,
        'volatility': 90.0,
        'liquidity': 80.0,
        'regime': 75.0,
    }


def _portfolio(entry=50.0, capital=100000.0, initial=100000.0):
    return {
        'position': {
            'ticker': 'AAPL',
            'entry_price_usd': entry,
            'entry_date': '2026-01-05',
            'stop_loss_usd': 45.0,
        },
        'capital': {
            'initial_mxn': initial,
            'current_mxn': capital,
            'return_pct': 0.0,
        },
        'history': [],
    }


# ---------------------------------------------------------------------------
# C1 / C11: indicators and NaN handling
# ---------------------------------------------------------------------------


def test_get_latest_indicators_replaces_nan_with_defaults():
    indicators = get_latest_indicators(calculate_all_indicators(_ohlcv(rows=5)))

    assert indicators['Ret20D'] == 0.0
    assert indicators['price'] == 104.0
    assert all(
        isinstance(indicators[key], float) for key in ('EMA21', 'ATR14', 'RSI14', 'Ret5D', 'ATRpct')
    )


def test_scoring_handles_nan_without_returning_extremes():
    assert score_momentum({'Ret5D': float('nan'), 'Ret20D': float('nan')}) == 50.0
    assert score_volatility({'ATRpct': float('nan')}) == 0


# ---------------------------------------------------------------------------
# C6: earnings window
# ---------------------------------------------------------------------------


def test_earnings_window_is_next_monday_to_friday(monkeypatch):
    monkeypatch.setattr(
        'src.earnings.get_earnings_date',
        lambda ticker: datetime(2026, 10, 28, 16, 0),
    )

    # Thursday 2026-10-22 -> next week is Mon 2026-10-26 .. Fri 2026-10-30.
    assert is_earnings_next_week('AAPL', reference_date=date(2026, 10, 22)) is True
    assert is_earnings_next_week('AAPL', reference_date=date(2026, 10, 24)) is True
    assert is_earnings_next_week('AAPL', reference_date=date(2026, 10, 31)) is False


# ---------------------------------------------------------------------------
# C7: rotation scans past the leader when it fails a filter
# ---------------------------------------------------------------------------


def test_rotation_skips_leader_below_ema_and_uses_next_candidate():
    ranked = [
        _candidate('AMD', score=80.0, above_ema=False),
        _candidate('NVDA', score=70.0, above_ema=True),
        _candidate('TQQQ', score=50.0, above_ema=True),
    ]
    position = {'ticker': 'TQQQ', 'entry_price_usd': 100.0}

    result = check_rotate_conditions(position, {}, ranked, regime='RISK_ON')

    assert result['rotate'] is True
    assert result['candidate']['ticker'] == 'NVDA'
    assert result['score_diff'] == 20.0


def test_rotation_does_not_rotate_when_no_candidate_beats_hurdle():
    ranked = [
        _candidate('AMD', score=60.0, above_ema=True),
        _candidate('TQQQ', score=50.0, above_ema=True),
    ]
    position = {'ticker': 'TQQQ', 'entry_price_usd': 100.0}

    result = check_rotate_conditions(position, {}, ranked, regime='RISK_ON')

    assert result['rotate'] is False
    assert result['candidate'] is None


# ---------------------------------------------------------------------------
# C9: stop report accounting
# ---------------------------------------------------------------------------


def test_stop_report_remaining_capital_goes_down():
    report = generate_stop_report(100.0, 2.0, 10_000.0, ticker='AAPL')

    assert report['stop_price'] == 95.0
    assert report['risk_pct'] == pytest.approx(-5.0)
    assert report['risk_mxn'] == pytest.approx(500.0)
    assert report['remaining_capital'] == pytest.approx(9_500.0)


# ---------------------------------------------------------------------------
# C8: commission accounting
# ---------------------------------------------------------------------------


def test_apply_commission():
    net, fee = apply_commission(10_000.0, 0.20)
    assert net == 9_980.0
    assert fee == 20.0


def test_charge_weekly_fee_is_idempotent():
    portfolio = _portfolio(capital=10_000.0, initial=10_000.0)
    moment = datetime(2026, 10, 22)

    portfolio, fee = charge_weekly_fee(portfolio, today=moment)
    assert fee == 20.0
    assert portfolio['capital']['current_mxn'] == 9_980.0
    assert portfolio['last_fee_week'] == _week_key(moment)
    assert portfolio['capital']['return_pct'] == pytest.approx(-0.20)

    portfolio, second_fee = charge_weekly_fee(portfolio, today=moment)
    assert second_fee == 0.0
    assert portfolio['capital']['current_mxn'] == 9_980.0


def test_execute_rotation_applies_rotation_commission(tmp_path, monkeypatch):
    class RotationConfig:
        def get(self, key, default=None):
            values = {
                'costs.charge_on': 'rotation',
                'costs.commission_pct': 0.20,
            }
            return values.get(key, default)

    monkeypatch.setattr('src.decision.get_config', lambda: RotationConfig())

    portfolio_path = tmp_path / 'portfolio.json'
    portfolio_path.write_text(json.dumps(_portfolio(entry=100.0)), encoding='utf-8')

    portfolio = execute_rotation(
        from_ticker='AAPL',
        to_ticker='NVDA',
        from_price=110.0,
        to_price=100.0,
        capital_mxn=10_000.0,
        atr_value=2.0,
        portfolio_path=portfolio_path,
    )

    # +10% return, then 0.20% commission on the resulting capital.
    assert portfolio['capital']['current_mxn'] == pytest.approx(10_978.0)
    assert portfolio['position']['ticker'] == 'NVDA'
    assert portfolio['position']['stop_loss_usd'] == 95.0
    assert portfolio['history'][0]['return_pct'] == pytest.approx(10.0)
    assert portfolio['fees'][-1]['amount_mxn'] == pytest.approx(22.0)


# ---------------------------------------------------------------------------
# C3 / C4: report stop multiplier and explicit capital
# ---------------------------------------------------------------------------


def test_screener_uses_passed_capital_and_category_multiplier(tmp_path):
    ranked = [_candidate('TQQQ', score=80.0)]
    filepath = export_screener_csv(
        ranked,
        filename='screener.csv',
        capital_mxn=100_000.0,
        output_dir=tmp_path,
    )

    row = pd.read_csv(filepath).iloc[0]
    # TQQQ is a 3x leveraged ETF: stop = 100 - 3.0 * 2 = 94.
    assert row['stop_loss'] == pytest.approx(94.0)
    assert row['risk_pct'] == pytest.approx(-6.0)
    assert row['risk_mxn'] == pytest.approx(6_000.0)
    assert bool(row['suitable']) is True


def test_weekly_report_pitch_uses_category_multiplier():
    candidate = _candidate('TQQQ', score=80.0)
    ranked = [candidate]
    decision = {
        'action': 'ROTATE',
        'from_ticker': 'AAPL',
        'to_ticker': 'TQQQ',
        'candidate': candidate,
        'reasons': ['✅ test'],
        'details': {'rotate_check': {'score_diff': 30.0, 'rb_ratio': 2.5}},
    }

    report = generate_weekly_report(decision, ranked, _portfolio())

    # 3.0 x ATR(2) = 6 -> 94.00, not the legacy 1.5 x ATR = 97.00.
    assert '**Stop Loss:** $94.00' in report


# ---------------------------------------------------------------------------
# C1: dossier must use the current price, not the entry price
# ---------------------------------------------------------------------------


def test_dossier_uses_current_price_for_stop(tmp_path, monkeypatch):
    import src.narrative as narrative

    monkeypatch.setattr(
        narrative,
        'get_position_data',
        lambda ticker: {
            'basic': {
                'price': 100.0,
                'ema21': 99.0,
                'rsi14': 60.0,
                'atr14': 2.0,
                'atr_pct': 2.0,
                'above_ema21': True,
                'ret5d': 1.0,
                'ret20d': 5.0,
                'dist_high20': -3.0,
            },
            'advanced': {},
        },
    )
    monkeypatch.setattr(narrative, 'get_fundamentals', lambda ticker: {})
    monkeypatch.setattr(
        narrative,
        'calculate_market_regime',
        lambda: {'regime': 'NEUTRAL', 'confidence': 0.5, 'indicators': {}},
    )
    monkeypatch.setattr(
        narrative,
        'get_news_summary',
        lambda ticker, days=7: {
            'total_articles': 0,
            'sentiment': {
                'positive': 0,
                'negative': 0,
                'neutral': 0,
                'average_sentiment': 0,
                'sentiment_label': 'NEUTRAL',
            },
            'articles': [],
        },
    )

    portfolio_path = tmp_path / 'portfolio.json'
    portfolio_path.write_text(json.dumps(_portfolio(entry=50.0)), encoding='utf-8')

    dossier = narrative.generate_dossier(str(portfolio_path))

    # 2.5 x ATR(2) below the CURRENT price (100), not the entry price (50).
    assert dossier['position']['stop_loss_calculated'] == 95.0
    assert dossier['position']['stop_loss_risk_pct'] == pytest.approx(-5.0)


# ---------------------------------------------------------------------------
# Accounting helper
# ---------------------------------------------------------------------------


def test_update_return_pct():
    portfolio = _portfolio(capital=90_000.0)
    assert update_return_pct(portfolio) == pytest.approx(-10.0)

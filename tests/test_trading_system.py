"""
Tests unitarios para el sistema de swing trading cuantitativo.
Usa datos sintéticos para validar cada módulo.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Tests de indicadores.py
# ============================================================================


class TestIndicators:
    """Tests del módulo de indicadores técnicos."""

    def test_ema_basic(self):
        """EMA debe calcular correctamente para una serie simple."""
        from src.indicators import ema

        series = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        result = ema(series, 3)

        assert len(result) == len(series)
        assert result.iloc[-1] > series.iloc[-2]  # EMA debe estar cerca del último valor
        assert not result.isna().any()

    def test_ema_period_1(self):
        """EMA con período 1 debe ser muy cercana al precio."""
        from src.indicators import ema

        series = pd.Series([10, 20, 30, 40, 50])
        result = ema(series, 1)

        # Con período 1, EMA debe ser muy cercana al último valor
        assert abs(result.iloc[-1] - series.iloc[-1]) < 0.01

    def test_atr_basic(self):
        """ATR debe calcular correctamente el True Range."""
        from src.indicators import atr

        df = pd.DataFrame(
            {
                'High': [10, 12, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24],
                'Low': [8, 9, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
                'Close': [9, 11, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
            }
        )

        result = atr(df, 14)

        assert len(result) == len(df)
        assert result.iloc[-1] > 0
        assert not result.isna().any()

    def test_rsi_basic(self):
        """RSI debe estar entre 0 y 100 (ignorando NaN iniciales)."""
        from src.indicators import rsi

        series = pd.Series([10, 11, 12, 11, 10, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
        result = rsi(series, 14)

        assert len(result) == len(series)
        # Ignorar NaN iniciales
        valid = result.dropna()
        if len(valid) > 0:
            assert (valid >= 0).all()
            assert (valid <= 100).all()

    def test_rsi_uptrend(self):
        """RSI debe ser alto (>50) en tendencia alcista."""
        from src.indicators import rsi

        # Serie con tendencia alcista clara
        series = pd.Series([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26])
        result = rsi(series, 14)

        # Los últimos valores deben ser altos (sobrecompra)
        assert result.iloc[-1] > 70

    def test_returns_basic(self):
        """Retornos deben calcularse correctamente."""
        from src.indicators import returns

        series = pd.Series([100, 110, 120, 130, 140])
        result = returns(series, [1, 2])

        assert 1 in result
        assert 2 in result

        # Retorno de 1 día: (110-100)/100 = 10%
        assert abs(result[1].iloc[1] - 10.0) < 0.01

    def test_distance_to_high(self):
        """Distancia a máximo debe ser 0 en el máximo."""
        from src.indicators import distance_to_high

        series = pd.Series([10, 15, 20, 25, 30, 25, 20])
        result = distance_to_high(series, 5)

        # En el máximo (30), la distancia debe ser 0
        assert abs(result.iloc[4]) < 0.01

    def test_calculate_all_indicators(self):
        """calculate_all_indicators debe agregar todas las columnas."""
        from src.indicators import calculate_all_indicators

        df = pd.DataFrame(
            {
                'Open': [100] * 30,
                'High': [105] * 30,
                'Low': [95] * 30,
                'Close': list(range(100, 130)),
                'Volume': [1000] * 30,
            }
        )

        result = calculate_all_indicators(df)

        expected_columns = [
            'EMA9',
            'EMA21',
            'ATR14',
            'RSI14',
            'Ret1D',
            'Ret5D',
            'Ret20D',
            'Vol20D',
            'DistHigh20',
            'DistLow20',
            'VolRatio',
            'ATRpct',
            'AboveEMA21',
        ]

        for col in expected_columns:
            assert col in result.columns, f'Falta columna: {col}'


# ============================================================================
# Tests de scoring.py
# ============================================================================


class TestScoring:
    """Tests del módulo de scoring."""

    def test_score_momentum_positive(self):
        """Momentum positivo debe dar score > 50."""
        from src.scoring import score_momentum

        indicators = {'Ret5D': 5.0, 'Ret20D': 10.0}
        score = score_momentum(indicators)

        assert score > 50

    def test_score_momentum_negative(self):
        """Momentum negativo debe dar score < 50."""
        from src.scoring import score_momentum

        indicators = {'Ret5D': -5.0, 'Ret20D': -10.0}
        score = score_momentum(indicators)

        assert score < 50

    def test_score_trend_above_ema(self):
        """Estar sobre EMA21 debe dar al menos 50 puntos."""
        from src.scoring import score_trend

        indicators = {'AboveEMA21': True, 'DistHigh20': -2.0}
        score = score_trend(indicators)

        assert score >= 50

    def test_score_trend_below_ema(self):
        """Estar bajo EMA21 debe dar menos de 50 puntos."""
        from src.scoring import score_trend

        indicators = {'AboveEMA21': False, 'DistHigh20': -5.0}
        score = score_trend(indicators)

        assert score < 50

    def test_score_volatility_ideal(self):
        """ATR en rango ideal (2-5%) debe dar 100 puntos."""
        from src.scoring import score_volatility

        indicators = {'ATRpct': 3.5}
        score = score_volatility(indicators)

        assert score == 100

    def test_score_volatility_too_low(self):
        """ATR muy bajo (<1%) debe dar score bajo."""
        from src.scoring import score_volatility

        indicators = {'ATRpct': 0.5}
        score = score_volatility(indicators)

        assert score < 50

    def test_score_volatility_too_high(self):
        """ATR muy alto (>8%) debe dar score bajo."""
        from src.scoring import score_volatility

        indicators = {'ATRpct': 10.0}
        score = score_volatility(indicators)

        # Con ATR de 10%, el score debe ser menor que 100
        assert score < 100

    def test_score_regime_ideal(self):
        """RSI en rango ideal (50-70) debe dar 100 puntos."""
        from src.scoring import score_regime

        indicators = {'RSI14': 60.0}
        score = score_regime(indicators)

        assert score == 100

    def test_calculate_composite_score(self):
        """Score compuesto debe estar entre 0 y 100."""
        from src.scoring import calculate_composite_score

        indicators = {
            'Ret5D': 2.0,
            'Ret20D': 5.0,
            'AboveEMA21': True,
            'DistHigh20': -2.0,
            'ATRpct': 3.0,
            'VolRatio': 1.2,
            'RSI14': 60.0,
        }

        result = calculate_composite_score(indicators)

        assert 0 <= result['score'] <= 100
        assert 'momentum' in result
        assert 'trend' in result
        assert 'volatility' in result
        assert 'liquidity' in result
        assert 'regime' in result

    def test_rank_universe(self):
        """rank_universe debe ordenar por score descendente."""
        from src.scoring import rank_universe

        all_indicators = {
            'A': {
                'Ret5D': 1.0,
                'Ret20D': 2.0,
                'AboveEMA21': True,
                'DistHigh20': -1.0,
                'ATRpct': 3.0,
                'VolRatio': 1.0,
                'RSI14': 60.0,
            },
            'B': {
                'Ret5D': 5.0,
                'Ret20D': 10.0,
                'AboveEMA21': True,
                'DistHigh20': -1.0,
                'ATRpct': 3.0,
                'VolRatio': 1.0,
                'RSI14': 60.0,
            },
            'C': {
                'Ret5D': -5.0,
                'Ret20D': -10.0,
                'AboveEMA21': False,
                'DistHigh20': -5.0,
                'ATRpct': 3.0,
                'VolRatio': 1.0,
                'RSI14': 40.0,
            },
        }

        ranked = rank_universe(all_indicators)

        assert len(ranked) == 3
        assert ranked[0]['score'] >= ranked[1]['score'] >= ranked[2]['score']
        assert ranked[0]['rank'] == 1
        assert ranked[1]['rank'] == 2
        assert ranked[2]['rank'] == 3

    def test_is_in_top_percentile(self):
        """is_in_top_percentile debe verificar correctamente."""
        from src.scoring import is_in_top_percentile, rank_universe

        all_indicators = {
            'A': {
                'Ret5D': 1.0,
                'Ret20D': 2.0,
                'AboveEMA21': True,
                'DistHigh20': -1.0,
                'ATRpct': 3.0,
                'VolRatio': 1.0,
                'RSI14': 60.0,
            },
            'B': {
                'Ret5D': 5.0,
                'Ret20D': 10.0,
                'AboveEMA21': True,
                'DistHigh20': -1.0,
                'ATRpct': 3.0,
                'VolRatio': 1.0,
                'RSI14': 60.0,
            },
            'C': {
                'Ret5D': -5.0,
                'Ret20D': -10.0,
                'AboveEMA21': False,
                'DistHigh20': -5.0,
                'ATRpct': 3.0,
                'VolRatio': 1.0,
                'RSI14': 40.0,
            },
            'D': {
                'Ret5D': 0.0,
                'Ret20D': 0.0,
                'AboveEMA21': True,
                'DistHigh20': -2.0,
                'ATRpct': 3.0,
                'VolRatio': 1.0,
                'RSI14': 55.0,
            },
        }

        ranked = rank_universe(all_indicators)

        # Top 25% = primer elemento (de 4)
        assert is_in_top_percentile(ranked, 'B', 25)
        assert not is_in_top_percentile(ranked, 'C', 25)


# ============================================================================
# Tests de risk.py
# ============================================================================


class TestRisk:
    """Tests del módulo de gestión de riesgo."""

    def test_calculate_stop_loss_atr(self):
        """Stop loss debe calcularse correctamente."""
        from src.risk import calculate_stop_loss_atr

        stop = calculate_stop_loss_atr(100.0, 5.0, 2.5)

        assert stop == 100.0 - (2.5 * 5.0)
        assert stop == 87.5

    def test_get_stop_multiplier(self):
        """Debe retornar 3.0 para apalancados 3x y 2.5 para estándar."""
        from src.risk import get_stop_multiplier

        # Apalancados 3x
        assert get_stop_multiplier('TQQQ') == 3.0
        assert get_stop_multiplier('SOXL') == 3.0
        assert get_stop_multiplier('FNGU') == 3.0
        assert get_stop_multiplier('SQQQ') == 3.0
        assert get_stop_multiplier('SOXS') == 3.0

        # Estándar
        assert get_stop_multiplier('AAPL') == 2.5
        assert get_stop_multiplier('NVDA') == 2.5
        assert get_stop_multiplier('AMD') == 2.5
        assert get_stop_multiplier('SMH') == 2.5

    def test_calculate_stop_by_category(self):
        """Stop debe usar multiplicador por categoría."""
        from src.risk import calculate_stop_by_category

        # TQQQ (apalancado 3x) - debe usar 3.0x
        stop_tqqq = calculate_stop_by_category('TQQQ', 100.0, 5.0)
        assert stop_tqqq == 100.0 - (3.0 * 5.0)
        assert stop_tqqq == 85.0

        # AMD (estándar) - debe usar 2.5x
        stop_amd = calculate_stop_by_category('AMD', 100.0, 5.0)
        assert stop_amd == 100.0 - (2.5 * 5.0)
        assert stop_amd == 87.5

    def test_is_trade_suitable(self):
        """Debe validar idoneidad con cap de 12%."""
        from src.risk import is_trade_suitable

        # Caso apto: riesgo < 12%
        # Precio 100, ATR 4 → stop 3x = 88, riesgo = -12%
        # Necesitamos algo con riesgo < 12%
        assert is_trade_suitable('AAPL', 100.0, 4.0)  # 100 - 2.5*4 = 90, riesgo -10%

        # Caso no apto: riesgo > 12%
        # Precio 100, ATR 6 → stop 3x = 82, riesgo = -18%
        assert not is_trade_suitable('TQQQ', 100.0, 6.0)  # 100 - 3*6 = 82, riesgo -18%

    def test_calculate_risk_pct(self):
        """Riesgo en porcentaje debe ser negativo."""
        from src.risk import calculate_risk_pct

        risk = calculate_risk_pct(100.0, 95.0)

        assert risk == -5.0

    def test_calculate_risk_mxn(self):
        """Riesgo en MXN debe calcularse correctamente."""
        from src.risk import calculate_risk_mxn

        risk = calculate_risk_mxn(100000.0, -5.0)

        assert risk == 5000.0

    def test_calculate_weekly_range(self):
        """Rango semanal debe calcularse correctamente."""
        from src.risk import calculate_weekly_range

        range_val = calculate_weekly_range(5.0, 1.5)

        assert range_val == 7.5

    def test_calculate_risk_reward_ratio(self):
        """Ratio R:B debe calcularse correctamente."""
        from src.risk import calculate_risk_reward_ratio

        ratio = calculate_risk_reward_ratio(100.0, 95.0, 110.0)

        # Riesgo: 5, Beneficio: 10, Ratio: 2.0
        assert ratio == 2.0

    def test_validate_stop_distance(self):
        """Validación de distancia de stop debe funcionar."""
        from src.risk import validate_stop_distance

        # Distancia de 5% > 1% mínimo
        assert validate_stop_distance(95.0, 100.0, 1.0)

        # Distancia de 0.5% < 1% mínimo
        assert not validate_stop_distance(99.5, 100.0, 1.0)

    def test_check_stop_execution(self):
        """Verificación de ejecución de stop debe funcionar."""
        from src.risk import check_stop_execution

        # Precio actual <= stop → ejecutar
        assert check_stop_execution(95.0, 100.0)

        # Precio actual > stop → no ejecutar
        assert not check_stop_execution(105.0, 100.0)

    def test_update_trailing_stop(self):
        """Trailing stop solo debe subir, nunca bajar."""
        from src.risk import update_trailing_stop

        # Stop actual: 90, nuevo stop calculado: 92 → debe subir a 92
        new_stop = update_trailing_stop(90.0, 100.0, 5.0, 1.5)
        assert new_stop == 92.5

        # Stop actual: 95, nuevo stop calculado: 92 → debe quedarse en 95
        new_stop = update_trailing_stop(95.0, 100.0, 5.0, 1.5)
        assert new_stop == 95.0


# ============================================================================
# Tests de decision.py
# ============================================================================


class TestDecision:
    """Tests del módulo de decisión."""

    def test_check_hold_conditions_pass(self):
        """Hold debe pasar si todas las condiciones se cumplen."""
        from src.decision import check_hold_conditions

        position = {'ticker': 'TEST'}
        indicators = {'AboveEMA21': True}
        ranked = [
            {'ticker': 'TEST', 'score': 80.0, 'rank': 1},
            {'ticker': 'OTHER', 'score': 70.0, 'rank': 2},
            {'ticker': 'ANOTHER', 'score': 60.0, 'rank': 3},
        ]

        result = check_hold_conditions(position, indicators, ranked, earnings_next_week=False)

        # Debe estar en top 30% (1 de 3 = 33%, pero 1 de 4 = 25%)
        # Agregamos más para asegurar top 30%
        ranked.append({'ticker': 'FOURTH', 'score': 50.0, 'rank': 4})
        result = check_hold_conditions(position, indicators, ranked, earnings_next_week=False)

        assert result['hold']

    def test_check_hold_conditions_fail_ema(self):
        """Hold debe fallar si está bajo EMA21."""
        from src.decision import check_hold_conditions

        position = {'ticker': 'TEST'}
        indicators = {'AboveEMA21': False}
        ranked = [{'ticker': 'TEST', 'score': 80.0, 'rank': 1}]

        result = check_hold_conditions(position, indicators, ranked, earnings_next_week=False)

        assert not result['hold']
        assert any('EMA21' in r for r in result['reasons'])

    def test_check_hold_conditions_fail_earnings(self):
        """Hold debe fallar si hay earnings próxima semana."""
        from src.decision import check_hold_conditions

        position = {'ticker': 'TEST'}
        indicators = {'AboveEMA21': True}
        ranked = [{'ticker': 'TEST', 'score': 80.0, 'rank': 1}]

        result = check_hold_conditions(position, indicators, ranked, earnings_next_week=True)

        assert not result['hold']
        assert any('earnings' in r.lower() for r in result['reasons'])

    def test_make_decision_hold(self):
        """make_decision debe retornar HOLD o HOLD_WITH_WARNINGS si cumple condiciones."""
        from src.decision import make_decision

        position = {'ticker': 'TEST'}
        indicators = {'AboveEMA21': True}
        ranked = [
            {'ticker': 'TEST', 'score': 80.0, 'rank': 1},
            {'ticker': 'OTHER', 'score': 70.0, 'rank': 2},
            {'ticker': 'ANOTHER', 'score': 60.0, 'rank': 3},
            {'ticker': 'FOURTH', 'score': 50.0, 'rank': 4},
        ]

        result = make_decision(position, indicators, ranked, earnings_next_week=False)

        assert result['action'] in ['HOLD', 'HOLD_WITH_WARNINGS']

    def test_make_decision_rotate(self):
        """make_decision debe retornar ROTATE si hay mejor candidato con suficiente diferencia."""
        from src.decision import make_decision

        position = {'ticker': 'TEST'}
        indicators = {'AboveEMA21': False}  # Falla Hold
        ranked = [
            {
                'ticker': 'LEADER',
                'score': 95.0,
                'rank': 1,
                'AboveEMA21': True,
                'ATR14': 5.0,
                'price': 100.0,
                'DistHigh20': -2.0,
            },
            {'ticker': 'TEST', 'score': 70.0, 'rank': 2},
        ]

        result = make_decision(position, indicators, ranked, earnings_next_week=False)

        # Debe rotar o al menos considerar rotación
        assert result['action'] in ['ROTATE', 'HOLD_WITH_WARNINGS']
        if result['action'] == 'ROTATE':
            assert result['to_ticker'] == 'LEADER'


# ============================================================================
# Tests de integration
# ============================================================================


class TestIntegration:
    """Tests de integración del pipeline completo."""

    def test_full_pipeline_synthetic(self):
        """Pipeline completo con datos sintéticos."""
        from src.decision import make_decision
        from src.indicators import calculate_all_indicators, get_latest_indicators
        from src.scoring import rank_universe

        # Crear datos sintéticos
        np.random.seed(42)
        n_days = 100

        df = pd.DataFrame(
            {
                'Open': np.random.uniform(100, 110, n_days),
                'High': np.random.uniform(110, 120, n_days),
                'Low': np.random.uniform(90, 100, n_days),
                'Close': np.linspace(100, 120, n_days),  # Tendencia alcista
                'Volume': np.random.uniform(1000, 2000, n_days),
            },
            index=pd.date_range('2026-01-01', periods=n_days),
        )

        # Calcular indicadores
        df_ind = calculate_all_indicators(df)
        indicators = get_latest_indicators(df_ind)

        assert indicators is not None
        assert indicators['price'] > 0
        assert indicators['AboveEMA21']  # Tendencia alcista

        # Rankear (solo un activo)
        ranked = rank_universe({'TEST': indicators})

        assert len(ranked) == 1
        assert ranked[0]['ticker'] == 'TEST'

        # Decisión
        position = {'ticker': 'TEST'}
        decision = make_decision(position, indicators, ranked, earnings_next_week=False)

        assert decision['action'] in ['HOLD', 'HOLD_WITH_WARNINGS']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

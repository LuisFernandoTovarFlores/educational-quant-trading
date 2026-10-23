"""
Módulo de decisión Hold vs Rotate.
Implementa el algoritmo de decisión del AGENTS.md sección 3.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from config.loader import get_config
from config.universe import UNIVERSE
from src.accounting import charge_rotation_fee, update_return_pct
from src.paths import STATE_DIR

logger = logging.getLogger(__name__)

DEFAULT_PORTFOLIO_PATH = STATE_DIR / 'portfolio.json'


def load_portfolio(path: Optional[Path] = None):
    """Carga el estado actual del portafolio."""
    filepath = Path(path) if path is not None else DEFAULT_PORTFOLIO_PATH
    if not filepath.exists():
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error('Could not read portfolio %s: %s', filepath, exc)
        return None


def save_portfolio(portfolio, path: Optional[Path] = None):
    """Guarda el estado del portafolio."""
    filepath = Path(path) if path is not None else DEFAULT_PORTFOLIO_PATH
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(portfolio, f, indent=2, ensure_ascii=False)
    return filepath


def filter_by_regime(ranked_universe, regime):
    """
    Filtra candidatos según el régimen de mercado.

    Args:
        ranked_universe: Lista rankeada del universo
        regime: Régimen de mercado ('RISK_ON', 'NEUTRAL', 'RISK_OFF')

    Returns:
        Lista filtrada
    """
    if regime == 'RISK_OFF':
        # Solo cash proxy
        allowed_tickers = UNIVERSE.get('DEFENSIVE_CASH', [])
        return [r for r in ranked_universe if r['ticker'] in allowed_tickers]

    elif regime == 'NEUTRAL':
        # Solo activos estándar (excluir apalancados e inversos)
        excluded_tickers = (
            UNIVERSE.get('LEVERAGED_LONG', [])
            + UNIVERSE.get('INVERSE_SHORT', [])
            + UNIVERSE.get('DEFENSIVE_CASH', [])
        )
        return [r for r in ranked_universe if r['ticker'] not in excluded_tickers]

    else:  # RISK_ON
        # Todos los activos permitidos (excepto cash proxy)
        excluded_tickers = UNIVERSE.get('DEFENSIVE_CASH', [])
        return [r for r in ranked_universe if r['ticker'] not in excluded_tickers]


def check_hold_conditions(
    current_position, current_indicators, ranked_universe, earnings_next_week=False
):
    """
    Verifica si se deben mantener las condiciones de Hold.
    Incluye salida de dos niveles: blanda (EMA21) + dura (stop duro).

    Args:
        current_position: Dict con ticker, entry_price, etc.
        current_indicators: Dict con indicadores del activo actual
        ranked_universe: Lista rankeada del universo
        earnings_next_week: Boolean si reporta earnings próxima semana

    Returns:
        Dict con {hold: bool, reasons: list}
    """
    ticker = current_position['ticker']
    reasons = []
    suitable = None

    # 1. ¿Está sobre EMA21? (salida blanda)
    above_ema21 = bool(current_indicators.get('AboveEMA21', False))
    if not above_ema21:
        reasons.append(f'❌ {ticker} por debajo de EMA21 (tendencia rota)')

    # 2. ¿Reporta earnings próxima semana?
    if earnings_next_week:
        reasons.append(f'❌ {ticker} reporta earnings próxima semana')

    # 3. ¿Está en top 30% del ranking?
    from src.scoring import is_in_top_percentile

    config = get_config()
    percentile = config.get('decision.hold.min_score_percentile', 30)
    in_top_30 = is_in_top_percentile(ranked_universe, ticker, percentile)
    if not in_top_30:
        rank_info = next((r for r in ranked_universe if r['ticker'] == ticker), None)
        if rank_info:
            reasons.append(
                f'❌ {ticker} rank {rank_info["rank"]}/{len(ranked_universe)} '
                f'(fuera de top {percentile}%)'
            )
        else:
            reasons.append(f'❌ {ticker} no aparece en el ranking del universo')

    # 4. ¿El activo es apto? (cap de riesgo)
    from src.risk import is_trade_suitable

    if 'ATR14' in current_indicators and 'price' in current_indicators:
        suitable = is_trade_suitable(
            ticker, current_indicators['price'], current_indicators['ATR14']
        )
        if not suitable:
            reasons.append(f'❌ {ticker} no apto (riesgo > 12%)')

    hold = len(reasons) == 0

    return {
        'hold': hold,
        'reasons': reasons,
        'above_ema21': above_ema21,
        'earnings_next_week': earnings_next_week,
        'in_top_30': in_top_30,
        'suitable': suitable,
    }


def check_rotate_conditions(
    current_position,
    current_indicators,
    ranked_universe,
    hurdle_points=None,
    min_rb_ratio=None,
    regime='RISK_ON',
):
    """
    Verifica si se deben rotar a otro activo.

    Recorre todo el ranking (no solo el líder) y devuelve el primer candidato
    que cumpla: hurdle de score, EMA21, idoneidad (cap de riesgo) y R:B.

    Args:
        current_position: Dict con ticker, entry_price, etc.
        current_indicators: Dict con indicadores del activo actual
        ranked_universe: Lista rankeada del universo
        hurdle_points: Puntos mínimos de diferencia (default: settings.yaml)
        min_rb_ratio: Ratio R:B mínimo (default: settings.yaml)
        regime: Régimen de mercado ('RISK_ON', 'NEUTRAL', 'RISK_OFF')

    Returns:
        Dict con {rotate: bool, candidate: dict, reasons: list}
    """
    config = get_config()
    if hurdle_points is None:
        hurdle_points = config.get('decision.rotate.score_hurdle_points', 15)
    if min_rb_ratio is None:
        min_rb_ratio = config.get('decision.rotate.min_risk_reward_ratio', 2.0)

    ticker = current_position['ticker']
    reasons = []

    # Filtrar candidatos según el régimen
    filtered_universe = filter_by_regime(ranked_universe, regime)

    # Obtener score del activo actual
    current_rank_info = next((r for r in filtered_universe if r['ticker'] == ticker), None)
    if not current_rank_info:
        return {
            'rotate': False,
            'candidate': None,
            'reasons': [f'⚠️  Activo actual {ticker} no permitido en régimen {regime}'],
        }

    current_score = current_rank_info['score']
    rejected = []

    # El ranking está ordenado de mayor a menor score.
    for candidate in filtered_universe:
        candidate_ticker = candidate['ticker']
        if candidate_ticker == ticker:
            continue

        price = candidate.get('price', 0) or 0
        atr = candidate.get('ATR14', 0) or 0

        if price <= 0 or atr <= 0:
            rejected.append(f'⚠️  {candidate_ticker}: sin precio/ATR válido')
            continue

        if not candidate.get('AboveEMA21', False):
            rejected.append(f'⚠️  {candidate_ticker}: por debajo de EMA21')
            continue

        from src.risk import is_trade_suitable

        if not is_trade_suitable(candidate_ticker, price, atr):
            rejected.append(f'⚠️  {candidate_ticker}: no apto (riesgo > cap)')
            continue

        score_diff = candidate['score'] - current_score
        if score_diff < hurdle_points:
            # El ranking está ordenado: ningún candidato posterior superará el hurdle.
            rejected.append(
                f'⚠️  {candidate_ticker} solo supera por {score_diff:.1f} pts '
                f'(hurdle: {hurdle_points})'
            )
            break

        from src.risk import calculate_risk_reward_ratio, calculate_stop_by_category

        stop_price = calculate_stop_by_category(candidate_ticker, price, atr)
        # Target: máximo de 20 días (aproximación conservadora).
        target_price = price * (1 + abs(candidate.get('DistHigh20', 0)) / 100)
        rb_ratio = calculate_risk_reward_ratio(price, stop_price, target_price)

        if rb_ratio < min_rb_ratio:
            rejected.append(f'⚠️  {candidate_ticker}: ratio R:B {rb_ratio:.2f} < {min_rb_ratio}')
            continue

        reasons.append(f'✅ Candidato {candidate_ticker} supera por {score_diff:.1f} pts')
        reasons.append(f'✅ Ratio R:B {rb_ratio:.2f} >= {min_rb_ratio}')
        reasons.append('✅ Candidato apto (riesgo <= cap)')

        return {
            'rotate': True,
            'candidate': candidate,
            'reasons': reasons,
            'score_diff': score_diff,
            'rb_ratio': rb_ratio,
        }

    reasons.extend(rejected[:5])
    return {
        'rotate': False,
        'candidate': None,
        'reasons': reasons or ['⚠️  No hay candidatos aptos disponibles en este régimen'],
    }


def make_decision(
    current_position,
    current_indicators,
    ranked_universe,
    earnings_next_week=False,
    regime='RISK_ON',
):
    """
    Toma la decisión final: Hold o Rotate.

    Args:
        current_position: Dict con ticker, entry_price, etc.
        current_indicators: Dict con indicadores del activo actual
        ranked_universe: Lista rankeada del universo
        earnings_next_week: Boolean si reporta earnings próxima semana
        regime: Régimen de mercado ('RISK_ON', 'NEUTRAL', 'RISK_OFF')

    Returns:
        Dict con decisión completa
    """
    ticker = current_position['ticker']

    # Si el régimen es RISK_OFF y el activo actual no es cash proxy, forzar rotación
    if regime == 'RISK_OFF':
        cash_proxy_tickers = UNIVERSE.get('DEFENSIVE_CASH', [])
        if ticker not in cash_proxy_tickers:
            # Buscar el mejor cash proxy
            cash_proxy_candidates = filter_by_regime(ranked_universe, regime)
            if cash_proxy_candidates:
                best_cash_proxy = cash_proxy_candidates[0]
                return {
                    'action': 'ROTATE_TO_CASH_PROXY',
                    'from_ticker': ticker,
                    'to_ticker': best_cash_proxy['ticker'],
                    'candidate': best_cash_proxy,
                    'reasons': [
                        '⚠️ Régimen RISK_OFF detectado',
                        f'✅ Rotación forzada a cash proxy {best_cash_proxy["ticker"]}',
                    ],
                    'details': {'regime': regime, 'forced_rotation': True},
                }

    # Si el régimen es NEUTRAL y el activo actual es apalancado/inverso, forzar rotación
    if regime == 'NEUTRAL':
        leveraged_tickers = UNIVERSE.get('LEVERAGED_LONG', []) + UNIVERSE.get('INVERSE_SHORT', [])
        if ticker in leveraged_tickers:
            # Buscar el mejor candidato estándar
            standard_candidates = filter_by_regime(ranked_universe, regime)
            if standard_candidates:
                best_candidate = standard_candidates[0]
                return {
                    'action': 'ROTATE_TO_STANDARD',
                    'from_ticker': ticker,
                    'to_ticker': best_candidate['ticker'],
                    'candidate': best_candidate,
                    'reasons': [
                        '⚠️ Régimen NEUTRAL detectado',
                        f'✅ Rotación forzada desde activo apalancado/inverso a {best_candidate["ticker"]}',
                    ],
                    'details': {'regime': regime, 'forced_rotation': True},
                }

    # Verificar condiciones de Hold
    hold_check = check_hold_conditions(
        current_position, current_indicators, ranked_universe, earnings_next_week
    )

    # Si cumple Hold, mantener
    if hold_check['hold']:
        return {
            'action': 'HOLD',
            'ticker': current_position['ticker'],
            'reasons': hold_check['reasons'] or ['✅ Cumple todas las condiciones de Hold'],
            'details': hold_check,
        }

    # Si no cumple Hold, evaluar Rotate (con filtro de régimen)
    rotate_check = check_rotate_conditions(
        current_position, current_indicators, ranked_universe, regime=regime
    )

    if rotate_check['rotate']:
        return {
            'action': 'ROTATE',
            'from_ticker': current_position['ticker'],
            'to_ticker': rotate_check['candidate']['ticker'],
            'candidate': rotate_check['candidate'],
            'reasons': hold_check['reasons'] + rotate_check['reasons'],
            'details': {'hold_check': hold_check, 'rotate_check': rotate_check, 'regime': regime},
        }

    # Si no cumple Rotate tampoco, mantener pero con advertencias
    return {
        'action': 'HOLD_WITH_WARNINGS',
        'ticker': current_position['ticker'],
        'reasons': hold_check['reasons'] + rotate_check['reasons'],
        'details': {'hold_check': hold_check, 'rotate_check': rotate_check, 'regime': regime},
    }


def execute_rotation(
    from_ticker, to_ticker, from_price, to_price, capital_mxn, atr_value=None, portfolio_path=None
):
    """
    Ejecuta la rotación y actualiza el portafolio.

    La comisión se aplica si ``costs.charge_on == "rotation"``. En modo
    ``weekly`` la comisión se cobra en el pipeline semanal (una vez por semana).

    Args:
        from_ticker: Ticker de salida
        to_ticker: Ticker de entrada
        from_price: Precio de salida
        to_price: Precio de entrada
        capital_mxn: Capital actual
        atr_value: ATR(14) del nuevo activo (opcional, para calcular el stop)
        portfolio_path: Ruta alternativa al portfolio.json

    Returns:
        Nuevo estado del portafolio
    """
    portfolio = load_portfolio(portfolio_path)
    if not portfolio:
        raise FileNotFoundError('No portfolio found; create state/portfolio.json first')

    position = portfolio.get('position', {})
    entry_price = float(position.get('entry_price_usd') or 0)
    return_pct = ((from_price - entry_price) / entry_price * 100) if entry_price else 0.0

    exit_record = {
        'ticker': from_ticker,
        'entry_price_usd': entry_price,
        'entry_date': position.get('entry_date'),
        'exit_price_usd': from_price,
        'exit_date': datetime.now().strftime('%Y-%m-%d'),
        'return_pct': round(return_pct, 2),
    }
    portfolio.setdefault('history', []).append(exit_record)

    # Actualizar capital con el rendimiento de la posición.
    new_capital = capital_mxn * (1 + return_pct / 100)
    portfolio.setdefault('capital', {})['current_mxn'] = round(new_capital, 2)

    # Calcular stop del nuevo activo si se proporcionó ATR.
    stop_loss = None
    if atr_value is not None and atr_value > 0:
        from src.risk import calculate_stop_by_category

        stop_loss = round(calculate_stop_by_category(to_ticker, to_price, atr_value), 2)

    portfolio['position'] = {
        'ticker': to_ticker,
        'entry_price_usd': to_price,
        'entry_date': datetime.now().strftime('%Y-%m-%d'),
        'stop_loss_usd': stop_loss,
    }

    # La comisión solo se descuenta aquí en modo "rotation".
    if get_config().get('costs.charge_on', 'weekly') == 'rotation':
        portfolio, _ = charge_rotation_fee(portfolio)

    update_return_pct(portfolio)

    portfolio['last_review'] = datetime.now().strftime('%Y-%m-%d')
    portfolio['next_review'] = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')

    save_portfolio(portfolio, portfolio_path)
    return portfolio

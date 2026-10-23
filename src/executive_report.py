"""
Executive report module - Genera el reporte ejecutivo final en Markdown.
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader

from config.loader import get_config
from src.decision import make_decision
from src.earnings import is_earnings_next_week
from src.narrative import generate_dossier, save_dossier
from src.paths import OUTPUT_DIR, TEMPLATES_DIR
from src.pipeline import build_ranked_universe
from src.risk import calculate_stop_by_category

logger = logging.getLogger(__name__)


def format_number(value, decimals=0):
    """Formatea números con separadores de miles."""
    if value is None:
        return '0'
    try:
        return f'{float(value):,.{decimals}f}'
    except (ValueError, TypeError):
        return str(value)


def _current_indicators(dossier: dict, ranked_universe: List[dict], ticker: str) -> dict:
    """Find the current position in the ranking or build a minimal fallback."""
    current = next((row for row in ranked_universe if row.get('ticker') == ticker), None)
    if current is not None:
        return current

    technicals = dossier.get('technicals', {})
    position = dossier.get('position', {})
    return {
        'ticker': ticker,
        'score': 0,
        'price': technicals.get('price') or position.get('entry_price', 0),
        'ATR14': technicals.get('atr', 0),
        'ATRpct': technicals.get('atr_pct', 0),
        'AboveEMA21': technicals.get('above_ema21', False),
        'RSI14': technicals.get('rsi', 50),
        'Ret5D': technicals.get('ret_5d', 0),
        'Ret20D': technicals.get('ret_20d', 0),
        'DistHigh20': technicals.get('dist_high', 0),
    }


def determine_decision(dossier: dict, ranked_universe: Optional[List[dict]] = None) -> dict:
    """
    Determina la decisión de trading usando el motor único de ``src.decision``.

    Args:
        dossier: Dict con todos los datos
        ranked_universe: Ranking precalculado (opcional; si falta se descarga)

    Returns:
        Dict con decisión y detalles
    """
    config = get_config()
    position = dossier.get('position', {})
    ticker = position.get('ticker') or dossier.get('ticker')
    regime = dossier.get('regime', 'NEUTRAL')

    if ranked_universe is None:
        ranked_universe, _ = build_ranked_universe(
            period=config.get('data.period', '1y'),
            save=False,
        )

    if not ranked_universe:
        return {
            'decision': 'HOLD_WITH_WARNINGS',
            'reasons': ['⚠️ No se pudo construir el ranking del universo'],
            'candidate': None,
            'candidate_price': 0.0,
            'candidate_stop': 0.0,
        }

    current = _current_indicators(dossier, ranked_universe, ticker)

    try:
        earnings_next_week = is_earnings_next_week(ticker) if ticker else False
        decision = make_decision(
            position,
            current,
            ranked_universe,
            earnings_next_week=earnings_next_week,
            regime=regime,
        )
    except Exception as exc:  # noqa: BLE001 - report generation must degrade gracefully
        logger.exception('Decision engine failed: %s', exc)
        return {
            'decision': 'HOLD_WITH_WARNINGS',
            'reasons': [f'⚠️ No se pudo evaluar la decisión: {exc}'],
            'candidate': None,
            'candidate_price': 0.0,
            'candidate_stop': 0.0,
        }

    action = decision.get('action', 'HOLD')
    candidate = decision.get('candidate') or {}
    candidate_ticker = decision.get('to_ticker') or candidate.get('ticker')
    candidate_price = float(candidate.get('price', 0) or 0)
    candidate_stop = 0.0

    if candidate_ticker and candidate_price > 0:
        atr = float(candidate.get('ATR14', 0) or 0)
        if atr > 0:
            candidate_stop = round(
                calculate_stop_by_category(candidate_ticker, candidate_price, atr), 2
            )

    return {
        'decision': 'ROTATE' if action.startswith('ROTATE') else action,
        'reasons': decision.get('reasons', []),
        'candidate': candidate_ticker,
        'candidate_price': candidate_price,
        'candidate_stop': candidate_stop,
    }


def calculate_stop_loss(price: float, atr: float, multiplier: float = 2.5) -> float:
    """Calcula stop loss basado en ATR (helper legado)."""
    return round(price - (multiplier * atr), 2)


def generate_executive_report(
    portfolio_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    ranked_universe: Optional[List[dict]] = None,
) -> str:
    """
    Genera el reporte ejecutivo completo.

    Args:
        portfolio_path: Ruta al archivo portfolio.json
        output_dir: Directorio de salida
        ranked_universe: Ranking precalculado (opcional)

    Returns:
        Ruta del archivo de reporte generado
    """
    config = get_config()
    output_path = Path(output_dir) if output_dir else OUTPUT_DIR
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info('Generating executive report...')

    # Generar dossier
    dossier = generate_dossier(portfolio_path)

    # Determinar decisión con el motor único
    decision_data = determine_decision(dossier, ranked_universe)
    dossier['decision'] = decision_data['decision']
    dossier['rotation_reasons'] = decision_data['reasons']

    candidate = decision_data['candidate']
    if candidate:
        dossier['rotation_candidate'] = candidate
        dossier['candidate_price'] = decision_data['candidate_price']
        dossier['candidate_stop'] = decision_data['candidate_stop']

        # Calcular tamaño de posición con el FX configurado
        fx_rate = float(config.get('fx.usd_mxn', 20.0) or 20.0)
        if fx_rate <= 0:
            fx_rate = 20.0
        capital_usd = float(dossier['capital']['current_mxn']) / fx_rate
        price = float(decision_data['candidate_price'] or 0)

        if price > 0:
            dossier['position_size'] = int(capital_usd / price)
            dossier['candidate_stop_pct'] = round(
                (decision_data['candidate_stop'] - price) / price * 100, 2
            )
        else:
            dossier['position_size'] = 0
            dossier['candidate_stop_pct'] = 0.0

    # Guardar dossier
    save_dossier(dossier, str(output_path / 'dossier.json'))

    # Cargar plantilla
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    env.filters['number_format'] = format_number

    template = env.get_template('executive.md.j2')

    # Renderizar reporte
    report_content = template.render(**dossier)

    # Guardar reporte
    week_number = datetime.now().isocalendar()[1]
    year = datetime.now().year
    report_filename = f'executive_{year}-W{week_number:02d}.md'
    report_path = output_path / report_filename

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    logger.info(f'Executive report saved to {report_path}')

    return str(report_path)


def main(argv=None) -> int:
    """CLI entry point for the executive report."""
    parser = argparse.ArgumentParser(
        description='Generate the executive Markdown report for the current position.'
    )
    parser.add_argument(
        '--portfolio',
        default=None,
        help='Path to portfolio.json (default: state/portfolio.json)',
    )
    parser.add_argument(
        '--output-dir',
        default=None,
        help='Directory for generated reports (default: output/)',
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )

    report_path = generate_executive_report(
        portfolio_path=args.portfolio,
        output_dir=args.output_dir,
    )
    print(f'✅ Executive report generated: {report_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

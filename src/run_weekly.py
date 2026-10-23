"""
Orquestador semanal del sistema de swing trading.
Ejecuta el pipeline completo: ingest → indicators → scoring → decision → report.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Allow running as `python src/run_weekly.py` without installing the package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.loader import get_config  # noqa: E402
from config.universe import get_all_tickers  # noqa: E402
from src.accounting import charge_weekly_fee  # noqa: E402
from src.decision import load_portfolio, make_decision, save_portfolio  # noqa: E402
from src.earnings import check_earnings_for_universe  # noqa: E402
from src.macro import calculate_market_regime  # noqa: E402
from src.paths import ensure_runtime_dirs  # noqa: E402
from src.pipeline import build_ranked_universe  # noqa: E402
from src.report import export_screener_csv, generate_weekly_report, save_report  # noqa: E402
from src.risk import generate_stop_report  # noqa: E402

logger = logging.getLogger(__name__)


def _format_money(value: float) -> str:
    return f'${value:,.2f}'


def run_weekly_pipeline(
    period: str | None = None,
    save_data: bool = True,
    charge_commission: bool = True,
    skip_earnings: bool = False,
):
    """
    Ejecuta el pipeline semanal completo.

    Args:
        period: Período de datos para yfinance (default: settings.yaml)
        save_data: Guardar CSVs crudos en data/raw
        charge_commission: Aplicar la comisión semanal si está configurada
        skip_earnings: Omitir la consulta de earnings (más rápido)

    Returns:
        Dict con resultados del pipeline o None si falla
    """
    config = get_config()
    period = period or config.get('data.period', '1y')
    ensure_runtime_dirs()

    print('=' * 70)
    print(f'🚀 PIPELINE SEMANAL — {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 70)
    print()

    # 1. Cargar portafolio
    print('📂 Cargando portafolio...')
    portfolio = load_portfolio()
    if not portfolio:
        print('❌ No se encontró state/portfolio.json')
        print('   Crea uno a partir del ejemplo:')
        print('   cp examples/portfolio.example.json state/portfolio.json')
        return None

    current_position = portfolio['position']
    print(f'  Posición actual: {current_position["ticker"]}')
    print(f'  Capital: {_format_money(portfolio["capital"]["current_mxn"])} MXN')

    # Comisión semanal (idempotente por semana ISO)
    if charge_commission and config.get('costs.charge_on', 'weekly') == 'weekly':
        portfolio, fee = charge_weekly_fee(portfolio)
        if fee:
            save_portfolio(portfolio)
            print(f'  💸 Comisión semanal: {_format_money(fee)} MXN')
    print()

    # 2. Descargar datos y calcular indicadores
    print('📥 Descargando datos de mercado y calculando indicadores...')
    tickers = get_all_tickers()
    ranked_universe, all_indicators = build_ranked_universe(period=period, save=save_data)
    print(f'  Activos procesados: {len(all_indicators)}/{len(tickers)}')
    print()

    # 3. Ranking del universo
    print('🏆 Top 5 del ranking:')
    for i, row in enumerate(ranked_universe[:5]):
        print(f'    {i + 1}. {row["ticker"]}: {row["score"]:.1f} pts')
    print()

    # 4. Régimen de mercado
    print('🌍 Calculando régimen de mercado...')
    regime_data = calculate_market_regime()
    regime = regime_data['regime']
    regime_confidence = regime_data['confidence']

    print(f'  Régimen: {regime} (confianza: {regime_confidence:.1%})')
    vix_value = regime_data.get('vix')
    if isinstance(vix_value, (int, float)):
        print(f'  VIX: {vix_value:.2f}')
    else:
        vix_value = regime_data.get('indicators', {}).get('VIX', {}).get('current')
        print(f'  VIX: {vix_value:.2f}' if isinstance(vix_value, (int, float)) else '  VIX: N/A')

    spy_value = regime_data.get('spy_vs_200ma')
    if not isinstance(spy_value, (int, float)):
        spy_current = regime_data.get('indicators', {}).get('SPY', {}).get('current', 0)
        spy_ma = regime_data.get('indicators', {}).get('SPY', {}).get('200d_ma', 0)
        spy_value = (spy_current - spy_ma) / spy_ma * 100 if spy_ma else None
    print(
        f'  SPY vs 200d MA: {spy_value:.2f}%'
        if isinstance(spy_value, (int, float))
        else '  SPY vs 200d MA: N/A'
    )
    print()

    # 5. Verificar earnings
    earnings_info = {}
    if skip_earnings:
        print('📅 Earnings: omitido (--skip-earnings)')
    else:
        print('📅 Verificando earnings...')
        earnings_info = check_earnings_for_universe(tickers)
        earnings_next_week_list = [
            ticker for ticker, info in earnings_info.items() if info['has_earnings_next_week']
        ]
        if earnings_next_week_list:
            print(f'  ⚠️  Activos con earnings próxima semana: {", ".join(earnings_next_week_list)}')
        else:
            print('  ✅ No hay earnings relevantes')
    print()

    # 6. Tomar decisión
    print('🎯 Tomando decisión...')
    current_indicators = all_indicators.get(current_position['ticker'], {})
    current_earnings = (
        earnings_info.get(current_position['ticker'], {}).get('has_earnings_next_week', False)
        if not skip_earnings
        else False
    )

    decision = make_decision(
        current_position,
        current_indicators,
        ranked_universe,
        earnings_next_week=current_earnings,
        regime=regime,
    )

    print(f'  Decisión: {decision["action"]}')
    for reason in decision['reasons']:
        print(f'    {reason}')
    print()

    # 7. Stop loss del candidato (si aplica)
    stop_report = None
    if decision['action'].startswith('ROTATE') and decision.get('candidate'):
        candidate = decision['candidate']
        stop_report = generate_stop_report(
            candidate['price'],
            candidate['ATR14'],
            portfolio['capital']['current_mxn'],
            ticker=candidate['ticker'],
        )

        print('💰 Stop loss del candidato:')
        print(f'  Precio entrada: ${stop_report["entry_price"]:.2f}')
        print(f'  Stop loss: ${stop_report["stop_price"]:.2f}')
        print(f'  Riesgo: {stop_report["risk_pct"]:.2f}% / ${stop_report["risk_mxn"]:,.0f} MXN')
        print(f'  Rango semanal: {stop_report["weekly_range_pct"]:.2f}%')
        print()

    # 8. Generar reporte
    print('📝 Generando reporte...')
    report = generate_weekly_report(
        decision,
        ranked_universe,
        portfolio,
        earnings_info,
        regime_data=regime_data,
    )

    report_path = save_report(report)
    print(f'  Reporte guardado en: {report_path}')

    # 9. Exportar screener
    screener_path = export_screener_csv(
        ranked_universe,
        capital_mxn=portfolio['capital']['current_mxn'],
    )
    print(f'  Screener exportado en: {screener_path}')
    print()

    # 10. Resumen final
    print('=' * 70)
    print('📋 RESUMEN')
    print('=' * 70)
    print(f'  Acción: {decision["action"]}')

    if decision['action'].startswith('ROTATE'):
        print(f'  Desde: {decision.get("from_ticker")}')
        print(f'  Hacia: {decision.get("to_ticker")}')
        if stop_report:
            print(f'  Stop: ${stop_report["stop_price"]:.2f}')
    else:
        print(f'  Mantener: {decision.get("ticker")}')

    print()
    print(f'  Próxima revisión: {portfolio.get("next_review")}')
    print('=' * 70)

    return {
        'decision': decision,
        'ranked_universe': ranked_universe,
        'portfolio': portfolio,
        'report_path': report_path,
        'screener_path': screener_path,
        'stop_report': stop_report,
    }


def main(argv=None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Run the weekly quantitative swing-trading pipeline.'
    )
    parser.add_argument(
        '--period',
        default=None,
        help='yfinance period (default: settings.yaml, e.g. 1y)',
    )
    parser.add_argument(
        '--no-save-data',
        action='store_true',
        help='Do not write raw CSVs to data/raw',
    )
    parser.add_argument(
        '--skip-earnings',
        action='store_true',
        help='Skip the earnings calendar lookup (faster, fewer API calls)',
    )
    parser.add_argument(
        '--no-commission',
        action='store_true',
        help='Do not charge the weekly commission for this run',
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )

    results = run_weekly_pipeline(
        period=args.period,
        save_data=not args.no_save_data,
        charge_commission=not args.no_commission,
        skip_earnings=args.skip_earnings,
    )

    if results:
        print('\n✅ Pipeline completado exitosamente')
        return 0

    print('\n❌ Pipeline falló')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())

"""
Módulo de generación de reportes.
Genera reporte semanal en Markdown con Top 3 + pitch + auditoría.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from config.loader import get_config
from src.paths import PROJECT_ROOT, STATE_DIR

logger = logging.getLogger(__name__)


def load_portfolio(path=None):
    """Carga el estado del portafolio."""
    filepath = Path(path) if path is not None else STATE_DIR / 'portfolio.json'
    if not filepath.exists():
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error('Could not read portfolio %s: %s', filepath, exc)
        return None


def generate_weekly_report(
    decision, ranked_universe, portfolio, earnings_info=None, regime_data=None
):
    """
    Genera reporte semanal completo.

    Args:
        decision: Dict con decisión (de make_decision)
        ranked_universe: Lista rankeada del universo
        portfolio: Estado del portafolio
        earnings_info: Dict con info de earnings
        regime_data: Dict con info del régimen de mercado

    Returns:
        String con reporte en Markdown
    """
    lines = []

    # Header
    lines.append(f'# Reporte Semanal — {datetime.now().strftime("%Y-%m-%d")}')
    lines.append('')

    # Régimen de mercado
    if regime_data:
        lines.append('## 🌍 Régimen de Mercado')
        lines.append('')
        regime = regime_data.get('regime', 'UNKNOWN')
        confidence = regime_data.get('confidence', 0)
        lines.append(f'**Régimen:** {regime} (Confianza: {confidence:.1%})')
        lines.append('')

        # Detalles del régimen
        details = regime_data.get('details', {})
        if details:
            for key, value in details.items():
                lines.append(f'- **{key}:** {value}')
            lines.append('')

        # Recomendaciones según régimen
        recommendations = regime_data.get('recommendations', {})
        if recommendations:
            lines.append('**Restricciones:**')
            lines.append(
                f'- ETFs apalancados: {"✅ Permitidos" if recommendations.get("allow_leveraged_etfs") else "❌ Bloqueados"}'
            )
            lines.append(
                f'- ETFs inversos: {"✅ Permitidos" if recommendations.get("allow_inverse_etfs") else "❌ Bloqueados"}'
            )
            lines.append(
                f'- Cash proxy: {"✅ Permitidos" if recommendations.get("allow_cash_proxy") else "⚠️ Solo en RISK_OFF"}'
            )
            lines.append('')

    # Estado del portafolio
    lines.append('## 📊 Estado del Portafolio')
    lines.append('')
    lines.append(f'- **Posición actual:** {portfolio["position"]["ticker"]}')
    lines.append(f'- **Precio entrada:** ${portfolio["position"]["entry_price_usd"]:.2f} USD')
    lines.append(f'- **Fecha entrada:** {portfolio["position"]["entry_date"]}')
    lines.append(f'- **Stop loss:** ${portfolio["position"].get("stop_loss_usd", 0):.2f} USD')
    lines.append(f'- **Capital actual:** ${portfolio["capital"]["current_mxn"]:,.2f} MXN')
    lines.append(f'- **Retorno acumulado:** {portfolio["capital"]["return_pct"]:.2f}%')
    lines.append('')

    # Decisión
    lines.append('## 🎯 Decisión')
    lines.append('')

    action = decision['action']

    # Manejar acciones especiales por régimen
    if action == 'ROTATE_TO_CASH_PROXY':
        lines.append('**🛡️ ROTACIÓN FORZOSA A CASH PROXY**')
        lines.append('')
        lines.append(f'- **Desde:** {decision.get("from_ticker")}')
        lines.append(f'- **Hacia:** {decision.get("to_ticker")}')
        lines.append('- **Razón:** Régimen RISK_OFF detectado')
        lines.append('')
        lines.append('**Razones:**')
        for reason in decision.get('reasons', []):
            lines.append(f'- {reason}')
        lines.append('')

    elif action == 'ROTATE_TO_STANDARD':
        lines.append('**🔄 ROTACIÓN FORZOSA A ACTIVO ESTÁNDAR**')
        lines.append('')
        lines.append(f'- **Desde:** {decision.get("from_ticker")}')
        lines.append(f'- **Hacia:** {decision.get("to_ticker")}')
        lines.append('- **Razón:** Régimen NEUTRAL detectado')
        lines.append('')
        lines.append('**Razones:**')
        for reason in decision.get('reasons', []):
            lines.append(f'- {reason}')
        lines.append('')

    elif action == 'HOLD':
        lines.append(f'**✅ MANTENER {decision["ticker"]}**')
        lines.append('')
        if decision['reasons']:
            for reason in decision['reasons']:
                lines.append(f'- {reason}')

    elif decision['action'] == 'ROTATE':
        lines.append(f'**🔄 ROTAR: {decision["from_ticker"]} → {decision["to_ticker"]}**')
        lines.append('')
        lines.append(f'- **Desde:** {decision["from_ticker"]}')
        lines.append(f'- **Hacia:** {decision["to_ticker"]}')
        lines.append(f'- **Precio candidato:** ${decision["candidate"]["price"]:.2f}')
        lines.append(f'- **Score candidato:** {decision["candidate"]["score"]:.1f}')
        lines.append(
            f'- **Diferencia score:** +{decision["details"]["rotate_check"]["score_diff"]:.1f} pts'
        )
        lines.append(f'- **Ratio R:B:** {decision["details"]["rotate_check"]["rb_ratio"]:.2f}')
        lines.append('')
        lines.append('**Razones:**')
        for reason in decision['reasons']:
            lines.append(f'- {reason}')

    elif decision['action'] == 'HOLD_WITH_WARNINGS':
        lines.append(f'**⚠️  MANTENER {decision["ticker"]} (CON ADVERTENCIAS)**')
        lines.append('')
        for reason in decision['reasons']:
            lines.append(f'- {reason}')

    lines.append('')

    # Top 3 candidatos
    lines.append('## 🏆 Top 3 Candidatos')
    lines.append('')
    lines.append('| Rank | Ticker | Score | Precio | RSI | Ret 20d | ATR% | EMA21 |')
    lines.append('|------|--------|-------|--------|-----|---------|------|-------|')

    for i, candidate in enumerate(ranked_universe[:3]):
        lines.append(
            f'| {candidate["rank"]} | {candidate["ticker"]} | '
            f'{candidate["score"]:.1f} | ${candidate["price"]:.2f} | '
            f'{candidate["RSI14"]:.1f} | {candidate["Ret20D"]:+.2f}% | '
            f'{candidate["ATRpct"]:.2f}% | {"✅" if candidate["AboveEMA21"] else "❌"} |'
        )

    lines.append('')

    # Stop loss Top 3
    lines.append('## 🛑 Stop Loss Top 3')
    lines.append('')
    lines.append('| Ticker | Precio | Stop | Riesgo % | Riesgo MXN | Apto |')
    lines.append('|--------|--------|------|----------|------------|------|')

    capital_mxn = float(portfolio.get('capital', {}).get('current_mxn') or 0)

    for candidate in ranked_universe[:3]:
        ticker = candidate.get('ticker', 'Unknown')
        try:
            price = float(candidate.get('price', 0) or 0)
            atr = float(candidate.get('ATR14', 0) or 0)

            if price <= 0 or atr <= 0:
                lines.append(f'| {ticker} | ${price:.2f} | N/A | N/A | N/A | ❓ |')
                continue

            # Calcular stop con multiplicador por categoría
            from src.risk import calculate_stop_by_category, is_trade_suitable

            stop_price = calculate_stop_by_category(ticker, price, atr)
            risk_pct = (stop_price - price) / price * 100
            risk_mxn = abs(capital_mxn * risk_pct / 100)
            suitable = is_trade_suitable(ticker, price, atr)

            suitable_icon = '✅' if suitable else '❌'

            lines.append(
                f'| {ticker} | ${price:.2f} | ${stop_price:.2f} | {risk_pct:.2f}% | '
                f'{risk_mxn:,.0f} MXN | {suitable_icon} |'
            )
        except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
            logger.warning('Could not compute stop for %s: %s', ticker, exc)
            lines.append(f'| {ticker} | N/A | N/A | N/A | N/A | ❓ |')

    lines.append('')

    # Pitch del candidato líder
    if decision['action'] == 'ROTATE':
        candidate = decision['candidate']
        lines.append('## 💡 Pitch del Candidato')
        lines.append('')
        lines.append(f'**{candidate["ticker"]}** — Score {candidate["score"]:.1f}/100')
        lines.append('')
        lines.append(
            f'- **Momentum:** {candidate["momentum"]:.1f}/100 (Ret 5d: {candidate["Ret5D"]:+.2f}%, Ret 20d: {candidate["Ret20D"]:+.2f}%)'
        )
        lines.append(
            f'- **Tendencia:** {candidate["trend"]:.1f}/100 ({"Sobre" if candidate["AboveEMA21"] else "Bajo"} EMA21)'
        )
        lines.append(
            f'- **Volatilidad:** {candidate["volatility"]:.1f}/100 (ATR: {candidate["ATRpct"]:.2f}%)'
        )
        lines.append(
            f'- **Liquidez:** {candidate["liquidity"]:.1f}/100 (Vol Ratio: {candidate["VolRatio"]:.2f}x)'
        )
        lines.append(
            f'- **Régimen:** {candidate["regime"]:.1f}/100 (RSI: {candidate["RSI14"]:.1f})'
        )
        lines.append('')

        # Stop loss con multiplicador por categoría (2.5x estándar, 3.0x apalancados)
        from src.risk import calculate_stop_by_category

        candidate_price = float(candidate.get('price', 0) or 0)
        candidate_atr = float(candidate.get('ATR14', 0) or 0)
        if candidate_price > 0 and candidate_atr > 0:
            stop_price = calculate_stop_by_category(
                candidate['ticker'], candidate_price, candidate_atr
            )
            risk_pct = (stop_price - candidate_price) / candidate_price * 100
            risk_mxn = abs(capital_mxn * risk_pct / 100)
            lines.append(
                f'**Stop Loss:** ${stop_price:.2f} ({risk_pct:.2f}% / {risk_mxn:,.0f} MXN)'
            )
        else:
            lines.append('**Stop Loss:** N/A (sin ATR válido)')
        lines.append('')

    # Earnings
    if earnings_info:
        lines.append('## 📅 Earnings Próximos')
        lines.append('')
        has_earnings = [t for t, info in earnings_info.items() if info['has_earnings_next_week']]

        if has_earnings:
            for ticker in has_earnings:
                date = earnings_info[ticker]['earnings_date']
                lines.append(f'- **{ticker}:** {date}')
        else:
            lines.append('✅ No hay earnings relevantes esta semana')

        lines.append('')

    # Checklist pre-market
    lines.append('## ✅ Checklist Pre-Market (Lunes/Martes)')
    lines.append('')
    lines.append('- [ ] Verificar pre-market del activo actual (no gap >2% abajo)')
    lines.append('- [ ] Confirmar ausencia de noticias macro adversas')
    lines.append('- [ ] Validar que stop loss esté colocado en bróker')
    if decision['action'] == 'ROTATE':
        lines.append(
            f'- [ ] Ejecutar rotación: vender {decision["from_ticker"]}, comprar {decision["to_ticker"]}'
        )
        lines.append(f'- [ ] Colocar stop loss en {decision["to_ticker"]}')
    lines.append('- [ ] Registrar precio real de ejecución')
    lines.append('')

    # Footer
    lines.append('---')
    lines.append(f'*Generado: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*')

    return '\n'.join(lines)


def _resolve_output_dir(output_dir=None) -> Path:
    """Resolve a configured output directory against the project root."""
    if output_dir is None:
        output_dir = get_config().get('reporting.output_dir', 'output')
    path = Path(output_dir)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def save_report(report_content, week_number=None, output_dir=None):
    """
    Guarda el reporte en output/.

    Args:
        report_content: String con reporte
        week_number: Número de semana (default: actual)
        output_dir: Directorio de salida (default: settings.yaml)

    Returns:
        Path del archivo guardado
    """
    if week_number is None:
        week_number = datetime.now().isocalendar()[1]

    year = datetime.now().year
    output_path = _resolve_output_dir(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    filename = f'report_{year}-W{week_number:02d}.md'
    filepath = output_path / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report_content)

    return filepath


def export_screener_csv(ranked_universe, filename=None, capital_mxn=None, output_dir=None):
    """
    Exporta screener completo a CSV.

    Args:
        ranked_universe: Lista rankeada
        filename: Nombre de archivo (default: screener_YYYY-WW.csv)
        capital_mxn: Capital para calcular el riesgo en MXN
        output_dir: Directorio de salida (default: settings.yaml)

    Returns:
        Path del archivo guardado
    """
    import pandas as pd

    if filename is None:
        year = datetime.now().year
        week_number = datetime.now().isocalendar()[1]
        filename = f'screener_{year}-W{week_number:02d}.csv'

    output_path = _resolve_output_dir(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    filepath = output_path / filename

    # Convertir a DataFrame
    df = pd.DataFrame(ranked_universe)
    if df.empty:
        df.to_csv(filepath, index=False)
        return filepath

    # Calcular stops para cada candidato
    from src.risk import calculate_stop_by_category, is_trade_suitable

    if capital_mxn is None:
        portfolio = load_portfolio()
        if portfolio:
            capital_mxn = portfolio.get('capital', {}).get('current_mxn')
        if capital_mxn is None:
            capital_mxn = get_config().get('capital.initial_mxn', 100000.0)
    capital_mxn = float(capital_mxn or 0)

    stops = []
    risk_pcts = []
    risk_mxn_list = []
    suitability = []

    for _, row in df.iterrows():
        price = float(row.get('price', 0) or 0)
        atr = float(row.get('ATR14', 0) or 0)
        ticker = row.get('ticker')

        if price <= 0 or atr <= 0:
            stops.append(None)
            risk_pcts.append(None)
            risk_mxn_list.append(None)
            suitability.append(False)
            continue

        stop_price = calculate_stop_by_category(ticker, price, atr)
        risk_pct = (stop_price - price) / price * 100
        risk_mxn = abs(capital_mxn * risk_pct / 100)
        suitable = is_trade_suitable(ticker, price, atr)

        stops.append(round(stop_price, 2))
        risk_pcts.append(round(risk_pct, 2))
        risk_mxn_list.append(round(risk_mxn, 0))
        suitability.append(suitable)

    df['stop_loss'] = stops
    df['risk_pct'] = risk_pcts
    df['risk_mxn'] = risk_mxn_list
    df['suitable'] = suitability

    # Seleccionar columnas relevantes
    columns = [
        'rank',
        'ticker',
        'score',
        'momentum',
        'trend',
        'volatility',
        'liquidity',
        'regime',
        'price',
        'RSI14',
        'Ret5D',
        'Ret20D',
        'ATRpct',
        'AboveEMA21',
        'stop_loss',
        'risk_pct',
        'risk_mxn',
        'suitable',
    ]

    df = df[[c for c in columns if c in df.columns]]

    df.to_csv(filepath, index=False)

    return filepath


if __name__ == '__main__':
    # Test: generar reporte de ejemplo
    print('📝 Generando reporte de ejemplo...')

    # Datos de ejemplo (ficticios)
    portfolio = {
        'position': {
            'ticker': 'AAPL',
            'entry_price_usd': 200.00,
            'entry_date': '2026-01-05',
            'stop_loss_usd': 185.00,
        },
        'capital': {'initial_mxn': 100000.0, 'current_mxn': 100000.0, 'return_pct': 0.0},
    }

    decision = {
        'action': 'HOLD',
        'ticker': 'AAPL',
        'reasons': ['✅ Cumple todas las condiciones de Hold'],
    }

    ranked = [
        {
            'rank': 1,
            'ticker': 'AAPL',
            'score': 75.0,
            'price': 200.00,
            'RSI14': 60.0,
            'Ret20D': 4.0,
            'ATRpct': 2.0,
            'AboveEMA21': True,
            'momentum': 70,
            'trend': 80,
            'volatility': 90,
            'liquidity': 80,
            'regime': 75,
        }
    ]

    report = generate_weekly_report(decision, ranked, portfolio)
    filepath = save_report(report)

    print(f'✅ Reporte guardado en: {filepath}')

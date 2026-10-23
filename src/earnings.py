"""
Módulo de filtro de earnings.
Verifica si un activo reporta earnings en la semana entrante.
"""

import logging
from datetime import date, datetime, timedelta

import yfinance as yf

logger = logging.getLogger(__name__)


def _as_date(value):
    """Normalize a datetime/Timestamp/date to a date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, 'date'):
        return value.date()
    return None


def _next_week_bounds(reference_date=None):
    """Return the Monday and Friday of the next calendar week."""
    reference = reference_date or datetime.now()
    if isinstance(reference, datetime):
        reference = reference.date()

    days_ahead = (7 - reference.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    next_monday = reference + timedelta(days=days_ahead)
    next_friday = next_monday + timedelta(days=4)
    return next_monday, next_friday


def _has_earnings_next_week(earnings_date, reference_date=None):
    """True if ``earnings_date`` falls in the next Monday-Friday window."""
    earnings_day = _as_date(earnings_date)
    if earnings_day is None:
        return False
    next_monday, next_friday = _next_week_bounds(reference_date)
    return next_monday <= earnings_day <= next_friday


def get_earnings_date(ticker):
    """
    Obtiene la próxima fecha de earnings de un ticker.
    Compatible con versiones nuevas y viejas de yfinance.

    Args:
        ticker: Símbolo del activo

    Returns:
        Datetime de earnings o None si no se encuentra
    """
    try:
        stock = yf.Ticker(ticker)

        # Intentar obtener de calendar (formato nuevo: dict)
        calendar = stock.calendar
        if calendar is not None:
            # Formato nuevo: dict con 'Earnings Date' como key
            if isinstance(calendar, dict):
                earnings_val = calendar.get('Earnings Date')
                if earnings_val is not None:
                    # Puede ser una lista de fechas o un solo valor
                    if isinstance(earnings_val, list) and len(earnings_val) > 0:
                        val = earnings_val[0]
                        if hasattr(val, 'to_pydatetime'):
                            return val.to_pydatetime()
                        elif isinstance(val, datetime):
                            return val
                    elif hasattr(earnings_val, 'to_pydatetime'):
                        return earnings_val.to_pydatetime()
                    elif isinstance(earnings_val, datetime):
                        return earnings_val
            # Formato viejo: DataFrame
            elif hasattr(calendar, 'empty') and not calendar.empty:
                if 'Earnings Date' in calendar.index:
                    earnings_str = calendar.loc['Earnings Date'].values[0]
                    if isinstance(earnings_str, str):
                        return datetime.strptime(earnings_str, '%Y-%m-%d')
                    elif hasattr(earnings_str, 'to_pydatetime'):
                        return earnings_str.to_pydatetime()

        # Intentar de earnings_dates
        earnings_dates = stock.earnings_dates
        if earnings_dates is not None and not earnings_dates.empty:
            # Buscar fechas futuras
            future_dates = earnings_dates[earnings_dates.index > datetime.now()]
            if not future_dates.empty:
                return future_dates.index[0].to_pydatetime()

        return None

    except Exception as exc:  # noqa: BLE001 - earnings data is optional
        logger.debug('Earnings lookup failed for %s: %s', ticker, exc)
        return None


def is_earnings_next_week(ticker, reference_date=None):
    """
    Verifica si un activo reporta earnings en la semana entrante.

    Args:
        ticker: Símbolo del activo
        reference_date: Fecha de referencia (default: hoy)

    Returns:
        Boolean
    """
    earnings_date = get_earnings_date(ticker)
    return _has_earnings_next_week(earnings_date, reference_date)


def check_earnings_for_universe(tickers, reference_date=None):
    """
    Verifica earnings para todos los tickers del universo.

    Args:
        tickers: Lista de tickers
        reference_date: Fecha de referencia

    Returns:
        Dict {ticker: {has_earnings: bool, date: datetime}}
    """
    results = {}

    for ticker in tickers:
        earnings_date = get_earnings_date(ticker)
        results[ticker] = {
            'has_earnings_next_week': _has_earnings_next_week(earnings_date, reference_date),
            'earnings_date': earnings_date.strftime('%Y-%m-%d') if earnings_date else None,
        }

    return results


def filter_earnings_from_candidates(ranked_universe, reference_date=None):
    """
    Filtra candidatos que reportan earnings próxima semana.

    Args:
        ranked_universe: Lista rankeada
        reference_date: Fecha de referencia

    Returns:
        Lista filtrada (sin earnings próxima semana)
    """
    filtered = []

    for candidate in ranked_universe:
        ticker = candidate['ticker']
        has_earnings = is_earnings_next_week(ticker, reference_date)

        if not has_earnings:
            filtered.append(candidate)

    return filtered


if __name__ == '__main__':
    # Test: verificar earnings de algunos tickers
    test_tickers = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'TQQQ']

    print('📅 Verificando earnings...')
    for ticker in test_tickers:
        earnings_date = get_earnings_date(ticker)
        if earnings_date:
            print(f'  {ticker}: {earnings_date.strftime("%Y-%m-%d")}')
        else:
            print(f'  {ticker}: No encontrado o sin earnings próximos')

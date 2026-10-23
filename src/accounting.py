"""Portfolio accounting helpers.

The strategy mandate charges a 0.20% commission. Depending on configuration
(``costs.charge_on``) the fee can be applied once per ISO week (``weekly``) or
only when a rotation is executed (``rotation``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from config.loader import get_config


def _week_key(moment: Optional[datetime] = None) -> str:
    """Return an ISO week key such as ``2026-W42``."""
    iso = (moment or datetime.now()).isocalendar()
    return f'{iso.year}-W{iso.week:02d}'


def update_return_pct(portfolio: Dict[str, Any]) -> float:
    """Recompute ``capital.return_pct`` from initial and current capital."""
    capital = portfolio.setdefault('capital', {})
    initial = float(capital.get('initial_mxn') or 0.0)
    current = float(capital.get('current_mxn') or 0.0)
    if initial <= 0:
        return 0.0
    return_pct = (current - initial) / initial * 100.0
    capital['return_pct'] = round(return_pct, 2)
    return capital['return_pct']


def apply_commission(capital_mxn: float, commission_pct: float) -> Tuple[float, float]:
    """Deduct a percentage commission from capital.

    Returns
    -------
    tuple[float, float]
        ``(net_capital, fee_mxn)``.
    """
    capital_mxn = float(capital_mxn)
    commission_pct = max(0.0, float(commission_pct))
    if capital_mxn <= 0 or commission_pct == 0:
        return capital_mxn, 0.0
    fee = capital_mxn * commission_pct / 100.0
    return round(capital_mxn - fee, 2), round(fee, 2)


def charge_weekly_fee(
    portfolio: Dict[str, Any],
    commission_pct: Optional[float] = None,
    today: Optional[datetime] = None,
) -> Tuple[Dict[str, Any], float]:
    """Charge the weekly commission at most once per ISO week.

    The portfolio is mutated in place and also returned. ``last_fee_week`` makes
    the operation idempotent when the pipeline is run several times in a week.
    """
    config = get_config()
    if commission_pct is None:
        commission_pct = float(config.get('costs.commission_pct', 0.20))

    week = _week_key(today)
    if portfolio.get('last_fee_week') == week:
        return portfolio, 0.0

    capital = portfolio.setdefault('capital', {})
    current = float(capital.get('current_mxn') or 0.0)
    net, fee = apply_commission(current, commission_pct)

    capital['current_mxn'] = net
    update_return_pct(portfolio)
    portfolio['last_fee_week'] = week
    portfolio.setdefault('fees', []).append(
        {'week': week, 'pct': commission_pct, 'amount_mxn': fee}
    )
    return portfolio, fee


def charge_rotation_fee(
    portfolio: Dict[str, Any],
    commission_pct: Optional[float] = None,
) -> Tuple[Dict[str, Any], float]:
    """Charge the commission on a rotation, if the configured mode is rotation."""
    config = get_config()
    if commission_pct is None:
        commission_pct = float(config.get('costs.commission_pct', 0.20))

    capital = portfolio.setdefault('capital', {})
    current = float(capital.get('current_mxn') or 0.0)
    net, fee = apply_commission(current, commission_pct)

    capital['current_mxn'] = net
    update_return_pct(portfolio)
    portfolio.setdefault('fees', []).append(
        {'date': datetime.now().strftime('%Y-%m-%d'), 'pct': commission_pct, 'amount_mxn': fee}
    )
    return portfolio, fee

"""
Módulo de gestión de riesgo.
Calcula stop loss basado en ATR y valida condiciones de riesgo.
"""


def calculate_stop_loss_atr(entry_price, atr_value, multiplier=2.5):
    """
    Calcula stop loss basado en ATR.

    Args:
        entry_price: Precio de entrada
        atr_value: ATR(14) actual
        multiplier: Multiplicador (default: 2.5, estándar del sistema)

    Returns:
        Stop loss price
    """
    stop = entry_price - (multiplier * atr_value)
    return stop


def calculate_risk_pct(entry_price, stop_price):
    """
    Calcula el riesgo en porcentaje.

    Args:
        entry_price: Precio de entrada
        stop_price: Stop loss

    Returns:
        Riesgo en porcentaje (negativo)
    """
    return (stop_price - entry_price) / entry_price * 100


def calculate_risk_mxn(capital_mxn, risk_pct):
    """
    Calcula el riesgo en MXN.

    Args:
        capital_mxn: Capital total en MXN
        risk_pct: Riesgo en porcentaje

    Returns:
        Riesgo en MXN (positivo, magnitud)
    """
    return abs(capital_mxn * risk_pct / 100)


def get_stop_multiplier(ticker: str) -> float:
    """
    Returns the ATR multiplier based on asset category.

    Args:
        ticker: Symbol of the asset

    Returns:
        Multiplier: 3.0 for leveraged 3x ETFs, 2.5 for standard assets
    """
    from config.loader import get_config

    config = get_config()

    leveraged_tickers = config.get('risk.leveraged_3x_tickers', [])

    if ticker.upper() in [t.upper() for t in leveraged_tickers]:
        return config.get('risk.stop_loss.multipliers.leveraged_3x', 3.0)
    else:
        return config.get('risk.stop_loss.multipliers.standard', 2.5)


def calculate_stop_by_category(ticker: str, price: float, atr: float) -> float:
    """
    Calculates stop loss using category-specific multiplier.

    Args:
        ticker: Symbol of the asset
        price: Current price
        atr: ATR(14) value

    Returns:
        Stop loss price
    """
    multiplier = get_stop_multiplier(ticker)
    stop_price = price - (multiplier * atr)
    return stop_price


def is_trade_suitable(ticker: str, price: float, atr: float, cap_pct: float = None) -> bool:
    """
    Checks if a trade is suitable based on the risk cap.

    Args:
        ticker: Symbol of the asset
        price: Current price
        atr: ATR(14) value
        cap_pct: Maximum allowed risk % (default from config, typically 12%)

    Returns:
        True if risk < cap (trade is suitable), False otherwise
    """
    from config.loader import get_config

    config = get_config()

    if cap_pct is None:
        cap_pct = config.get('risk.stop_loss.max_risk_pct', 12.0)

    stop_price = calculate_stop_by_category(ticker, price, atr)
    risk_pct = calculate_risk_pct(price, stop_price)

    return abs(risk_pct) <= cap_pct


def get_weekly_range(atr: float, multiplier: float = 2.24) -> float:
    """
    Returns the expected weekly range.

    Weekly range ≈ ATR × √5 ≈ 2.24 × ATR

    Args:
        atr: ATR(14) value
        multiplier: Weekly range multiplier (default 2.24 = √5)

    Returns:
        Expected weekly range in price units
    """
    return multiplier * atr


def calculate_risk_reward_ratio(entry_price, stop_price, target_price):
    """
    Calcula ratio riesgo/beneficio.

    Args:
        entry_price: Precio de entrada
        stop_price: Stop loss
        target_price: Precio objetivo

    Returns:
        Ratio R:B (ej: 2.0 = 2:1)
    """
    risk = max(0.0, entry_price - stop_price)
    reward = max(0.0, target_price - entry_price)

    if risk == 0:
        return 0

    return reward / risk


def validate_stop_distance(stop_price, current_price, min_distance_pct=1.0):
    """
    Valida que el stop no esté demasiado cerca del precio actual.

    Args:
        stop_price: Stop loss
        current_price: Precio actual
        min_distance_pct: Distancia mínima aceptable (%)

    Returns:
        Boolean
    """
    if current_price <= 0:
        return False
    distance_pct = abs(stop_price - current_price) / current_price * 100
    return distance_pct >= min_distance_pct


def calculate_weekly_range(atr_value, multiplier=1.5):
    """
    Calcula el rango esperado semanal (legacy, para compatibilidad).

    Args:
        atr_value: ATR(14)
        multiplier: Multiplicador (default: 1.5)

    Returns:
        Rango en unidades de precio
    """
    return multiplier * atr_value


def generate_stop_report(entry_price, atr_value, capital_mxn, multiplier=None, ticker=None):
    """
    Genera reporte completo de stop loss con multiplicador por categoría.

    Args:
        entry_price: Precio de entrada
        atr_value: ATR(14)
        capital_mxn: Capital en MXN
        multiplier: Multiplicador ATR (opcional, se usa el de la categoría si no se provee)
        ticker: Ticker del activo (para determinar multiplicador por categoría)

    Returns:
        Dict con reporte completo incluyendo idoneidad
    """
    from config.loader import get_config

    config = get_config()

    # Determinar multiplicador
    if multiplier is None:
        if ticker is not None:
            multiplier = get_stop_multiplier(ticker)
        else:
            multiplier = config.get('risk.stop_loss.multipliers.standard', 2.5)

    # Buffer de slippage
    slippage_buffer_pct = config.get('risk.stop_loss.slippage_buffer_pct', 0.5) / 100.0
    slippage_amount = entry_price * slippage_buffer_pct

    stop_price = calculate_stop_loss_atr(entry_price, atr_value, multiplier)
    stop_price_with_slippage = stop_price - slippage_amount

    risk_pct = calculate_risk_pct(entry_price, stop_price)
    risk_mxn = calculate_risk_mxn(capital_mxn, risk_pct)
    weekly_range = calculate_weekly_range(atr_value, 2.24)  # Rango semanal real

    # Idoneidad
    cap_pct = config.get('risk.stop_loss.max_risk_pct', 12.0)
    suitable = abs(risk_pct) <= cap_pct

    return {
        'entry_price': entry_price,
        'stop_price': stop_price,
        'stop_price_with_slippage': stop_price_with_slippage,
        'atr': atr_value,
        'multiplier': multiplier,
        'risk_pct': risk_pct,
        'risk_mxn': risk_mxn,
        'remaining_capital': capital_mxn - risk_mxn,
        'weekly_range': weekly_range,
        'weekly_range_pct': weekly_range / entry_price * 100,
        'suitable': suitable,
        'max_risk_pct': cap_pct,
        'slippage_buffer_pct': slippage_buffer_pct * 100,
    }


def check_stop_execution(current_price, stop_price):
    """
    Verifica si se debe ejecutar el stop.

    Args:
        current_price: Precio actual
        stop_price: Stop loss

    Returns:
        Boolean
    """
    return current_price <= stop_price


def update_trailing_stop(current_stop, current_price, atr_value, multiplier=2.5):
    """
    Actualiza stop trailing (solo sube, nunca baja).

    Args:
        current_stop: Stop actual
        current_price: Precio actual
        atr_value: ATR(14)
        multiplier: Multiplicador

    Returns:
        Nuevo stop (puede ser igual o mayor)
    """
    new_stop = calculate_stop_loss_atr(current_price, atr_value, multiplier)

    # Solo subir, nunca bajar
    return max(current_stop, new_stop)

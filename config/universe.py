"""
Universo de activos de alta liquidez (volumen diario > $50M USD)
Dividido por perfil táctico según AGENTS.md sección 4.
"""

UNIVERSE = {
    # 1. Momentum & Mega-Caps (Longs direccionales de alta convicción)
    'MOMENTUM': ['NVDA', 'TSLA', 'META', 'AMZN', 'AAPL', 'MSFT', 'AMD', 'GOOGL', 'NFLX', 'PLTR'],
    # 2. ETFs Sectoriales (Para capturar rotaciones institucionales)
    'SECTORIAL': ['XLF', 'XLE', 'XLK', 'XBI', 'SMH', 'XLU', 'XLI', 'GDX'],
    # 3. Instrumentos Direccionales Asimétricos (Apalancados e Inversos)
    'LEVERAGED_LONG': ['TQQQ', 'SOXL', 'FNGU'],
    'INVERSE_SHORT': ['SQQQ', 'SOXS', 'PSQ', 'SPDN'],
    # 4. Proxy de Efectivo / Modo Defensivo (Volatilidad ~0%)
    'DEFENSIVE_CASH': ['SGOV', 'BIL', 'SHY'],
}


def get_all_tickers():
    """Retorna lista plana de todos los tickers del universo."""
    return [ticker for group in UNIVERSE.values() for ticker in group]


def get_ticker_category(ticker):
    """Retorna la categoría de un ticker dado."""
    for category, tickers in UNIVERSE.items():
        if ticker in tickers:
            return category
    return None

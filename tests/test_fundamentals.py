"""
Tests for fundamentals module.
"""

import pytest

from src.fundamentals import is_etf, valuation_verdict


def test_is_etf():
    """Test ETF detection."""
    # Known ETFs
    assert is_etf('TQQQ')
    assert is_etf('XLF')
    assert is_etf('SOXL')
    assert is_etf('SGOV')

    # Known stocks
    assert not is_etf('AAPL')
    assert not is_etf('NVDA')
    assert not is_etf('TSLA')

    # Case insensitive
    assert is_etf('tqqq')
    assert is_etf('Tqqq')


def test_valuation_verdict():
    """Test valuation verdict logic."""
    # Cheap stock
    cheap = {'type': 'stock', 'pe_ratio': 12, 'pb_ratio': 1.5}
    assert valuation_verdict(cheap) == 'cheap'

    # Expensive stock
    expensive = {'type': 'stock', 'pe_ratio': 35, 'pb_ratio': 6}
    assert valuation_verdict(expensive) == 'expensive'

    # Fair value
    fair = {'type': 'stock', 'pe_ratio': 20, 'pb_ratio': 3}
    assert valuation_verdict(fair) == 'fair'

    # ETF should return N/A
    etf = {'type': 'etf'}
    assert valuation_verdict(etf) == 'N/A (ETF)'

    # Missing data
    unknown = {'type': 'stock', 'pe_ratio': None, 'pb_ratio': None}
    assert valuation_verdict(unknown) == 'unknown'

    # Partial data
    partial = {'type': 'stock', 'pe_ratio': 15, 'pb_ratio': None}
    assert valuation_verdict(partial) == 'unknown'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

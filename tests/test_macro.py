"""
Tests for macro module.
"""

import pytest

from src.macro import (
    calculate_market_regime,
    get_regime_recommendation,
    is_inverse_etf_allowed,
    is_leveraged_etf_allowed,
)


def test_is_leveraged_etf_allowed():
    """Test leveraged ETF allowance by regime."""
    assert is_leveraged_etf_allowed('RISK_ON') is True
    assert is_leveraged_etf_allowed('NEUTRAL') is False
    assert is_leveraged_etf_allowed('RISK_OFF') is False


def test_is_inverse_etf_allowed():
    """Test inverse ETF allowance by regime."""
    assert is_inverse_etf_allowed('RISK_ON') is False
    assert is_inverse_etf_allowed('NEUTRAL') is False
    assert is_inverse_etf_allowed('RISK_OFF') is True


@pytest.mark.integration
def test_calculate_market_regime_structure():
    """Test that regime calculation returns proper structure."""
    regime = calculate_market_regime()

    assert 'regime' in regime
    assert 'confidence' in regime
    assert 'indicators' in regime
    assert 'details' in regime

    assert regime['regime'] in ['RISK_ON', 'NEUTRAL', 'RISK_OFF']
    assert 0 <= regime['confidence'] <= 1


@pytest.mark.integration
def test_get_regime_recommendation_structure():
    """Test that regime recommendation returns proper structure."""
    result = get_regime_recommendation()

    assert 'regime' in result
    assert 'recommendations' in result

    rec = result['recommendations']
    assert 'description' in rec
    assert 'leveraged_etfs' in rec
    assert 'inverse_etfs' in rec
    assert 'cash_proxy' in rec
    assert 'strategy' in rec
    assert 'position_size' in rec


@pytest.mark.integration
def test_regime_recommendations_consistency():
    """Test that recommendations are consistent with regime."""
    result = get_regime_recommendation()
    regime = result['regime']
    rec = result['recommendations']

    if regime == 'RISK_ON':
        assert rec['leveraged_etfs'] is True
        assert rec['inverse_etfs'] is False
    elif regime == 'RISK_OFF':
        assert rec['leveraged_etfs'] is False
        assert rec['inverse_etfs'] is True
    else:  # NEUTRAL
        assert rec['leveraged_etfs'] is False
        assert rec['inverse_etfs'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

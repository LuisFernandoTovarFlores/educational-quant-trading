"""
Tests para Fase H: Capa completa de reporte ejecutivo.
Incluye tests para narrative.py, executive_report.py y report.py.
"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def sample_portfolio(tmp_path):
    """Crea un portfolio.json de prueba."""
    portfolio = {
        'position': {
            'ticker': 'AAPL',
            'entry_price_usd': 150.0,
            'entry_date': '2026-10-01',
            'stop_loss_usd': 145.0,
        },
        'capital': {'current_mxn': 95000.0, 'initial_mxn': 100000.0, 'return_pct': -5.0},
        'history': [],
    }

    portfolio_path = tmp_path / 'portfolio.json'
    with open(portfolio_path, 'w') as f:
        json.dump(portfolio, f)

    return str(portfolio_path)


@pytest.fixture
def sample_regime_data():
    """Datos de régimen de ejemplo."""
    return {
        'regime': 'RISK_ON',
        'confidence': 0.75,
        'details': {'vix': 15.31, 'spy_vs_200ma': 7.34, 'yield_curve': -0.35, 'dxy': 101.93},
        'recommendations': {
            'allow_leveraged_etfs': True,
            'allow_inverse_etfs': False,
            'allow_cash_proxy': False,
        },
    }


@pytest.mark.integration
class TestNarrativeModule:
    """Tests para narrative.py."""

    def test_generate_dossier_structure(self, sample_portfolio):
        """Test: generate_dossier() retorna estructura correcta."""
        from src.narrative import generate_dossier

        dossier = generate_dossier(portfolio_path=sample_portfolio)

        # Verificar estructura básica
        assert 'date' in dossier
        assert 'generated_at' in dossier
        assert 'position' in dossier
        assert 'capital' in dossier
        assert 'technicals' in dossier
        assert 'advanced' in dossier
        assert 'fundamentals' in dossier
        assert 'macro' in dossier
        assert 'news' in dossier
        assert 'decision' in dossier

    def test_generate_dossier_position_data(self, sample_portfolio):
        """Test: generate_dossier() incluye datos de posición."""
        from src.narrative import generate_dossier

        dossier = generate_dossier(portfolio_path=sample_portfolio)

        # Verificar datos de posición
        position = dossier['position']
        assert position['ticker'] == 'AAPL'
        assert position['entry_price'] == 150.0
        assert position['stop_loss'] == 145.0

    def test_generate_dossier_technical_data(self, sample_portfolio):
        """Test: generate_dossier() incluye datos técnicos."""
        from src.narrative import generate_dossier

        dossier = generate_dossier(portfolio_path=sample_portfolio)

        # Verificar datos técnicos básicos
        technicals = dossier['technicals']
        assert 'ema21' in technicals
        assert 'rsi' in technicals
        assert 'atr' in technicals
        assert 'atr_pct' in technicals

        # Verificar datos técnicos avanzados
        advanced = dossier['advanced']
        assert 'macd' in advanced
        assert 'adx' in advanced
        assert 'bb_percent_b' in advanced
        assert 'supertrend' in advanced

    def test_generate_dossier_macro_data(self, sample_portfolio):
        """Test: generate_dossier() incluye datos macro."""
        from src.narrative import generate_dossier

        dossier = generate_dossier(portfolio_path=sample_portfolio)

        # Verificar datos macro
        macro = dossier['macro']
        assert 'vix' in macro
        assert 'spy_vs_200ma' in macro
        assert 'yield_curve' in macro
        assert 'dxy' in macro

    def test_generate_dossier_news_data(self, sample_portfolio):
        """Test: generate_dossier() incluye datos de noticias."""
        from src.narrative import generate_dossier

        dossier = generate_dossier(portfolio_path=sample_portfolio)

        # Verificar datos de noticias
        news = dossier['news']
        assert 'total_articles' in news
        assert 'sentiment' in news
        assert 'articles' in news

        # Verificar estructura de sentimiento
        sentiment = news['sentiment']
        assert 'positive' in sentiment
        assert 'negative' in sentiment
        assert 'neutral' in sentiment
        assert 'average_sentiment' in sentiment
        assert 'sentiment_label' in sentiment


@pytest.mark.integration
class TestExecutiveReportModule:
    """Tests para executive_report.py."""

    def test_generate_executive_report_creates_file(self, sample_portfolio, tmp_path):
        """Test: generate_executive_report() crea archivo de salida."""
        from src.executive_report import generate_executive_report

        output_dir = str(tmp_path / 'output')
        Path(output_dir).mkdir()

        report_path = generate_executive_report(
            portfolio_path=sample_portfolio, output_dir=output_dir
        )

        assert Path(report_path).exists()
        assert report_path.endswith('.md')

    def test_generate_executive_report_content_structure(self, sample_portfolio, tmp_path):
        """Test: generate_executive_report() genera contenido con estructura correcta."""
        from src.executive_report import generate_executive_report

        output_dir = str(tmp_path / 'output')
        Path(output_dir).mkdir()

        report_path = generate_executive_report(
            portfolio_path=sample_portfolio, output_dir=output_dir
        )

        with open(report_path, 'r') as f:
            content = f.read()

        # Verificar secciones principales
        assert '# Reporte Ejecutivo' in content
        assert '## 📊 Resumen Ejecutivo' in content
        assert '## 📈 Análisis Técnico' in content
        assert '## 💰 Análisis Fundamental' in content
        assert '## 🌍 Contexto Macro' in content
        assert '## 📰 Noticias y Sentimiento' in content
        assert '## 🎯 Recomendación' in content

    def test_generate_executive_report_creates_dossier(self, sample_portfolio, tmp_path):
        """Test: generate_executive_report() también crea dossier.json."""
        from src.executive_report import generate_executive_report

        output_dir = tmp_path / 'output'
        output_dir.mkdir()

        generate_executive_report(portfolio_path=sample_portfolio, output_dir=str(output_dir))

        # Verificar que el dossier también se generó
        dossier_path = output_dir / 'dossier.json'
        assert dossier_path.exists()

        with open(dossier_path, 'r') as f:
            dossier = json.load(f)

        assert 'technicals' in dossier
        assert 'macro' in dossier
        assert 'news' in dossier


class TestWeeklyReportWithRegime:
    """Tests para report.py con integración de régimen."""

    def test_generate_weekly_report_with_regime(self, sample_regime_data):
        """Test: generate_weekly_report() incluye régimen correctamente."""
        from src.report import generate_weekly_report

        # Datos de ejemplo
        decision = {'action': 'HOLD', 'ticker': 'AAPL', 'reasons': ['✅ Precio sobre EMA21']}

        ranked_universe = [
            {
                'ticker': 'AAPL',
                'score': 85.0,
                'rank': 1,
                'price': 150.0,
                'RSI14': 60.0,
                'Ret20D': 5.0,
                'ATRpct': 2.5,
                'AboveEMA21': True,
            }
        ]

        portfolio = {
            'position': {
                'ticker': 'AAPL',
                'entry_price_usd': 150.0,
                'entry_date': '2026-10-01',
                'stop_loss_usd': 145.0,
            },
            'capital': {'current_mxn': 95000.0, 'initial_mxn': 100000.0, 'return_pct': -5.0},
        }

        earnings_info = {}

        report = generate_weekly_report(
            decision, ranked_universe, portfolio, earnings_info, regime_data=sample_regime_data
        )

        # Verificar que el reporte incluye régimen
        assert '## 🌍 Régimen de Mercado' in report
        assert 'RISK_ON' in report
        assert 'ETFs apalancados' in report

    def test_generate_weekly_report_rotate_to_cash_proxy(self):
        """Test: generate_weekly_report() maneja ROTATE_TO_CASH_PROXY."""
        from src.report import generate_weekly_report

        decision = {
            'action': 'ROTATE_TO_CASH_PROXY',
            'from_ticker': 'TQQQ',
            'to_ticker': 'SGOV',
            'reasons': ['⚠️ Régimen RISK_OFF detectado', '✅ Rotación forzada a cash proxy SGOV'],
        }

        ranked_universe = []
        portfolio = {
            'position': {
                'ticker': 'TQQQ',
                'entry_price_usd': 100.0,
                'entry_date': '2026-10-01',
                'stop_loss_usd': 95.0,
            },
            'capital': {'current_mxn': 50000.0, 'return_pct': -5.0},
        }
        earnings_info = {}
        regime_data = {
            'regime': 'RISK_OFF',
            'confidence': 0.85,
            'details': {},
            'recommendations': {
                'allow_leveraged_etfs': False,
                'allow_inverse_etfs': False,
                'allow_cash_proxy': True,
            },
        }

        report = generate_weekly_report(
            decision, ranked_universe, portfolio, earnings_info, regime_data=regime_data
        )

        # Verificar que el reporte incluye la rotación forzada
        assert '🛡️ ROTACIÓN FORZOSA A CASH PROXY' in report
        assert '**Desde:** TQQQ' in report
        assert '**Hacia:** SGOV' in report


@pytest.mark.integration
class TestIntegration:
    """Tests de integración completa."""

    def test_full_pipeline(self, sample_portfolio, tmp_path):
        """Test: Pipeline completo desde portfolio.json hasta reporte final."""
        from src.executive_report import generate_executive_report

        output_dir = tmp_path / 'output'
        output_dir.mkdir()

        # Generar reporte ejecutivo
        report_path = generate_executive_report(
            portfolio_path=sample_portfolio, output_dir=str(output_dir)
        )

        # Verificar que el archivo existe
        assert Path(report_path).exists()

        # Verificar contenido básico
        with open(report_path, 'r') as f:
            content = f.read()

        assert '# Reporte Ejecutivo' in content
        assert 'AAPL' in content

        # Verificar que el dossier también se generó
        dossier_path = output_dir / 'dossier.json'
        assert dossier_path.exists()

        with open(dossier_path, 'r') as f:
            dossier = json.load(f)

        assert 'technicals' in dossier
        assert 'macro' in dossier
        assert 'news' in dossier


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

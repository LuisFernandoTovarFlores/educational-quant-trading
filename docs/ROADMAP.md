# Roadmap

> Prioridades orientativas. Abre un issue o una discusión antes de empezar una
> tarea grande.

## v0.1.0 — Open source release (actual)

- [x] Licencia MIT.
- [x] README bilingüe (EN/ES).
- [x] Documentación de arquitectura, estrategia y limitaciones.
- [x] CI (lint + tests offline), pre-commit y Dependabot.
- [x] Ejemplos de portafolio, reporte y screener.
- [x] Correcciones críticas: precio actual en el dossier, stop por categoría,
  capital/FX configurables, ventana de earnings, escaneo de candidatos,
  comisiones, rutas ancladas y logs sin tokens.
- [x] Motor de decisión único reutilizado por el reporte ejecutivo.

## v0.2.0 — Backtesting

- [ ] `src/backtest.py` con walk-forward.
- [ ] Comisiones, slippage y FX en las métricas.
- [ ] Benchmark SPY/QQQ; CAGR, Sharpe, Sortino, max drawdown, win rate.
- [ ] Curva de equity y reporte HTML/Markdown.
- [ ] Tests con datos sintéticos y sin red.
- [ ] Documento `docs/BACKTESTING.md` con supuestos y resultados.

## v0.3.0 — Contabilidad de cartera

- [ ] Ledger de operaciones (entry, exit, fees, FX).
- [ ] P&L realizado/no realizado.
- [ ] Rebalanceo automático del estado desde un CSV del bróker.
- [ ] Comisión semanal opcional según calendario ISO.
- [ ] Tests de contabilidad con casos límite.

## v0.4.0 — Empaquetado y CLI

- [ ] Renombrar `src/` a `swing_trading/` (paquete instalable).
- [ ] Entrypoints `swing-trading init`, `run`, `report`, `backtest`.
- [ ] `--offline` con datos cacheados.
- [ ] Dockerfile reproducible.
- [ ] Publicación en PyPI (opcional).

## v0.5.0 — Calidad de tests

- [ ] Mockear yfinance y HTTP con `responses`/`unittest.mock`.
- [ ] Convertir los tests de integración en offline.
- [ ] Cobertura mínima del 80% en CI.
- [ ] Tests de propiedades para scoring y stops.
- [ ] Fixtures de datos sintéticos reutilizables.

## v1.0.0 — Validación

- [ ] Resultados walk-forward documentados y reproducibles.
- [ ] Análisis de sensibilidad de parámetros.
- [ ] Stress test 2020, 2022 y 2024.
- [ ] Revisión independiente de la lógica.
- [ ] Guía de paper trading.

## Ideas no priorizadas

- Relative strength vs SPY.
- Volatilidad implícita vs realizada.
- Detección de patrones (VCP, breakout).
- Alertas por email/Telegram.
- Integración con bróker (paper trading).
- Dashboard web.
- Traducción completa de docs al inglés.

## No-goals

- Garantizar rentabilidad.
- Ejecutar órdenes con dinero real sin supervisión.
- Sustituir asesoría financiera profesional.
- Distribuir datos de mercado de terceros.

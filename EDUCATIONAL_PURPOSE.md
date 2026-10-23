# Educational Purpose / Propósito educativo

This repository is an **educational and research project**. It exists to study
how a rules-based quantitative swing-trading pipeline is designed, tested and
documented. It is not a product, a signal service or a recommendation engine.

## What this project is for

- Learning quantitative finance and technical analysis in a transparent codebase.
- Practising software engineering: data ingestion, testing, CI, packaging and
  documentation.
- Exploring market-regime filters, scoring models and risk rules.
- Providing a reproducible base for future backtesting experiments.

## What this project is not

- **Not financial advice.** Nothing here is a personalized recommendation.
- **Not a production trading system.** It does not connect to a broker and does
  not place orders.
- **Not a validated strategy.** There is no backtest proving that the parameters
  generate alpha. Past or simulated results do not guarantee future returns.
- **Not a promise of returns.** The +10% in 8 weeks reference is a design
  objective, not a forecast or a guarantee.

## Risk warning

Trading involves a substantial risk of loss. Concentrating 100% of capital in a
single asset, especially 3x leveraged ETFs, can produce severe drawdowns and
permanent capital loss. Never trade with money you cannot afford to lose.

Before using any idea from this repository with real money:

1. Read [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).
2. Build and run your own backtest with commissions, slippage and FX.
3. Paper trade for several weeks.
4. Consult a licensed professional if needed.

## Data and third-party services

Market data comes from `yfinance`, which is not an official exchange feed. News,
fundamentals and macro data may come from Finnhub, Marketaux and FRED. Their
terms of service apply. This repository does not redistribute market data.

## License

The code is released under the [MIT License](LICENSE). The license includes a
warranty disclaimer. The educational purpose statement does not replace it.

---

## Español

Este repositorio es un **proyecto educativo y de investigación**. Su objetivo es
estudiar cómo se diseña, prueba y documenta un pipeline cuantitativo de swing
trading basado en reglas. No es un producto, un servicio de señales ni un motor
de recomendaciones.

- **No es asesoría financiera.** Nada de lo aquí publicado constituye una
  recomendación personalizada.
- **No es un sistema de producción.** No se conecta a un bróker ni envía órdenes.
- **No es una estrategia validada.** No hay un backtest que demuestre que los
  parámetros generan alpha.
- **No garantiza rendimientos.** El objetivo de +10% en 8 semanas es un supuesto
  de diseño, no una promesa.

Operar en bolsa implica un riesgo sustancial de pérdida. La concentración del
100% en un solo activo, especialmente ETFs apalancados 3x, puede producir
drawdowns severos y pérdida permanente de capital. No operes con dinero que no
puedas permitirte perder.

Antes de usar cualquier idea de este repositorio con dinero real:

1. Lee [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).
2. Construye y ejecuta tu propio backtest con comisiones, slippage y FX.
3. Haz paper trading durante varias semanas.
4. Consulta a un profesional licenciado si es necesario.

Los datos de mercado provienen de `yfinance`, que no es un feed oficial de bolsa.
Las noticias, fundamentales y datos macro pueden venir de Finnhub, Marketaux y
FRED; aplican sus términos de servicio. Este repositorio no redistribuye datos de
mercado.

El código se publica bajo la [Licencia MIT](LICENSE), que incluye una cláusula de
no garantía. Este documento no sustituye esa licencia.

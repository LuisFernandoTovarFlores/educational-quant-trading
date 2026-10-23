# Changelog

Todos los cambios relevantes de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
el proyecto usa [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

### Added

- Backtesting walk-forward (planificado).
- Mocking completo de los tests de integración (planificado).

## [0.1.0] — 2026-10-22

Primera versión pública. El objetivo de esta release es la **higiene open
source** y la **corrección de bugs críticos**, no una validación de rentabilidad.

### Added

- Licencia MIT.
- `EDUCATIONAL_PURPOSE.md` con el propósito educativo y el descargo de responsabilidad.
- `README.md` en inglés y `README.es.md` en español.
- Documentación: arquitectura, estrategia, limitaciones, roadmap, decisiones
  (ADR), guía de usuario en español y guía de publicación.
- `pyproject.toml` con metadata, dependencias, extras `dev`/`fred`, scripts
  `swing-trading` y `swing-trading-report`, configuración de `pytest`, `ruff` y
  cobertura.
- `requirements-dev.txt`, `Makefile`, `.editorconfig`, `.gitattributes` y
  `.pre-commit-config.yaml`.
- CI de GitHub Actions (Python 3.10–3.13), CodeQL y Dependabot.
- Plantillas de issue/PR y `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`,
  `SECURITY.md`.
- Ejemplos: `examples/portfolio.example.json`, `examples/report.example.md` y
  `examples/screener.example.csv`.
- `src/paths.py` para anclar rutas a la raíz del proyecto.
- `src/accounting.py` con comisiones configurables (`weekly` o `rotation`) y
  cálculo de retorno.
- `src/pipeline.py` para compartir ingesta, indicadores y ranking.
- Tests de regresión offline (`tests/test_regressions.py`).
- Marcador `integration` y configuración para excluir tests de red por defecto.
- Documento `docs/OPEN_SOURCE_AUDIT.md` con la auditoría previa a la publicación.
- Documento `docs/PUBLISHING.md` con el procedimiento de historial limpio.

### Changed

- `README` reescrito como presentación de proyecto open source, con quickstart,
  arquitectura, configuración, CLI, testing y disclaimer.
- `AGENTS.md` saneado: 28 activos, comisiones configurables, reglas alineadas con
  el código y mapa de módulos.
- El reporte ejecutivo reutiliza `src.decision.make_decision` en lugar de
  duplicar reglas.
- `run_weekly.py` usa `src.pipeline`, acepta flags CLI y calcula la comisión
  semanal de forma idempotente.
- `report.py` acepta el capital como parámetro y usa el multiplicador ATR por
  categoría en el pitch.
- `narrative.py` incluye el precio actual en los indicadores básicos.
- `secrets.py` no sobrescribe variables de entorno y admite comillas/`export`.
- `scoring.py`, `risk.py` y `decision.py` leen sus parámetros de
  `config/settings.yaml`.
- `news.py` y `fundamentals.py` envían el token de Finnhub en cabecera y evitan
  filtrarlo en logs.

### Fixed

- **Dossier:** el stop calculado usaba el precio de entrada en lugar del precio
  actual.
- **Stop del candidato:** `generate_stop_report` no recibía el ticker y aplicaba
  el multiplicador estándar a ETFs 3x.
- **Pitch:** el stop usaba `1.5×ATR` hardcodeado.
- **Capital:** `export_screener_csv` usaba un capital personal hardcodeado.
- **FX:** el reporte ejecutivo usaba un tipo de cambio fijo `/ 20`.
- **Earnings:** la ventana de la semana entrante era demasiado amplia y se
  consultaba dos veces por ticker.
- **Rotación:** solo se evaluaba el primer candidato; si fallaba, no se probaban
  los siguientes.
- **Comisiones:** no se aplicaban en ninguna parte.
- **Riesgo:** `remaining_capital` sumaba el riesgo en lugar de restarlo.
- **NaN:** indicadores y scores podían producir valores artificialmente altos.
- **Rutas:** los scripts dependían del directorio de trabajo.
- **Logs:** un error HTTP de Finnhub podía incluir el token en la URL.
- **División por cero:** en el sizing del reporte ejecutivo y en la validación de
  stops.
- **Excepciones:** se reemplazaron `except:` desnudos por capturas concretas.

### Removed

- `MANUAL.md` (reemplazado por `docs/USER_GUIDE.es.md`).
- `MEMORY.md` (reemplazado por `CHANGELOG.md` y `docs/DECISIONS.md`; el
  historial privado se conserva fuera del repositorio público).
- `QUANTITATIVE_STRATEGIES_RESEARCH.md` movido a `docs/STRATEGY_RESEARCH.md`.

### Security

- Se verificó que las claves reales de `.env` no aparecen en ningún commit.
- Se añadieron `SECURITY.md`, `detect-private-key` y `gitleaks` a pre-commit.
- Se recomienda rotar las claves antes de publicar y activar secret scanning en
  GitHub.

---

## Notas de la versión 0.1.0

- **No es una estrategia validada.** No hay backtest ni resultados de
  rentabilidad.
- El pipeline **no ejecuta órdenes**.
- El historial público es limpio; el repositorio privado se conserva como
  archivo.

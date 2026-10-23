# Auditoría para publicar el proyecto como Open Source

**Fecha:** 2026-10-22  
**Alcance:** árbol de trabajo completo, historial de Git, configuración, tests, documentación y seguridad de secretos.  
**Objetivo:** convertir el repositorio en un proyecto open source publicable, mantenible y seguro.

---

## 1. Veredicto general

El proyecto **tiene una base técnica sólida**: arquitectura modular, 79 tests, separación de capas, configuración YAML y documentación abundante. Sin embargo, **todavía no está listo para publicarse como open source**. Los bloqueadores no son de estrategia: son de licencia, datos personales, reproducibilidad y documentación.

| Área | Estado | Comentario |
|---|---|---|
| Legal / licencia | 🔴 0/5 | No existe `LICENSE`. Sin licencia, el código es "todos los derechos reservados". |
| Privacidad | 🔴 1/5 | Capital, posiciones, rutas personales y email universitario en el árbol **y en el historial**. |
| Seguridad de secretos | 🟢 4/5 | `.env` ignorado y **sin claves reales en el historial** (verificado). Falta escaneo automatizado. |
| Reproducibilidad | 🔴 1/5 | `requirements.txt` incompleto; 23 tests dependen de red; un clone limpio no arranca. |
| Documentación | 🟡 2/5 | Mucha, pero desactualizada, contradictoria y con datos personales. |
| Calidad de código | 🟡 3/5 | Buena estructura; hay bugs concretos y duplicación de lógica. |
| CI / automatización | 🔴 0/5 | Sin GitHub Actions, lint, pre-commit ni Dependabot. |
| Experiencia de contribución | 🔴 1/5 | Sin `CONTRIBUTING`, `CODE_OF_CONDUCT`, plantillas de issues/PR ni guía de arquitectura. |
| Empaquetado / CLI | 🔴 1/5 | No hay `pyproject.toml`, entrypoint ni instalación `pip install -e .`. |
| Validación cuantitativa | 🔴 1/5 | No hay backtest, ni comisiones, ni slippage, ni benchmark. Los parámetros no están calibrados. |

**Conclusión:** se puede publicar, pero primero hay que ejecutar una fase de "higiene open source" (P0) y una fase de corrección de bugs/documentación (P1). El backtesting y la validación estadística son un roadmap posterior, no un requisito para publicar.

---

## 2. Lo que ya está bien (no tocar sin motivo)

1. **Secretos fuera de Git.** `.env` está en `.gitignore` y se verificó con `git rev-list --all` + `git grep` que los valores reales de `FINNHUB_API_KEY`, `MARKETAUX_API_KEY` y `FRED_API_KEY` **no aparecen en ningún commit**.
2. **Datos y artefactos ignorados.** `data/`, `output/`, `state/portfolio.json`, `__pycache__/`, `.pytest_cache/` y `.DS_Store` no están versionados.
3. **Arquitectura clara.** `ingest → indicators → scoring → decision → risk → report`, más capas de macro, noticias, fundamentales y reporte ejecutivo.
4. **Tests reales.** 79 tests, de los cuales 56 son offline y pasan en ~5 s. Hay tests de indicadores, scoring, decisión, riesgo, régimen y utilidades.
5. **Configuración externalizada.** `config/settings.yaml` y `config/universe.py` permiten ajustar parámetros sin tocar lógica.
6. **Documento de investigación.** `QUANTITATIVE_STRATEGIES_RESEARCH.md` es un buen activo divulgativo: estrategias, fundamentos académicos y roadmap.
7. **Separación multi-proveedor.** `yfinance` para precios, Finnhub/Marketaux para noticias, FRED con fallback. La degradación sin claves es razonable.

---

## 3. Bloqueadores P0 (antes de hacer público)

### P0-1. No hay licencia

Sin `LICENSE`, GitHub no puede mostrar una licencia y nadie puede reutilizar el código legalmente. Es el bloqueador más simple y el más importante.

**Acción:** elegir MIT (recomendada para máxima adopción), Apache-2.0 (patentes) o GPL-3.0 (copyleft). Añadir `LICENSE` y el campo `license` en `pyproject.toml`/README.

### P0-2. Datos personales en el árbol y en el historial

El repositorio privado contiene información que no debería publicarse:

| Dónde | Qué expone |
|---|---|
| `README.md` (sección "Estado Actual") | Capital real, posición, retorno acumulado y stop. |
| `MEMORY.md` | Capital inicial/actual, historial de operaciones, fechas y decisiones personales. |
| `MANUAL.md` | Rutas absolutas del equipo, usuario de GitHub y ejemplos con capital real. |
| `state/portfolio.json` (no versionado) | Mismos datos financieros. |
| Historial de Git | `MEMORY.md` y `README.md` ya fueron commiteados con esos datos; **sanear el archivo actual no borra el historial**. |
| Autor de los commits | Email universitario personal, visible en cualquier repo público. |

**Acción:** decidir entre (a) publicar con historial limpio (nueva rama huérfana / repo nuevo) y conservar el privado como archivo, o (b) sanear solo el árbol actual y aceptar que el historial conserva los datos. La opción (a) es la recomendable.

Además, reemplazar los datos reales por un `examples/portfolio.example.json` neutro y un reporte de ejemplo con cifras ficticias.

### P0-3. `requirements.txt` incompleto

Solo declara:

```txt
yfinance>=0.2.31
pandas>=2.0.0
numpy>=1.24.0
pyyaml>=6.0
```

Pero el código importa:

- `requests` (`src/news.py`, `src/fundamentals.py`) → **falta**.
- `jinja2` (`src/executive_report.py`) → **falta**.
- `fredapi` (`src/macro.py`, import opcional dentro de función) → **falta como extra opcional**.
- `python-dotenv` está documentado en `MANUAL.md`, pero **el código no lo usa** (hay un parser propio en `config/secrets.py`).

**Consecuencia:** un `pip install -r requirements.txt` en un entorno limpio falla al ejecutar el reporte ejecutivo o las noticias.

**Acción:** añadir dependencias, separar `requirements-dev.txt` (pytest, pytest-cov, ruff, pre-commit) y declarar extras opcionales (`fredapi`) en `pyproject.toml`.

### P0-4. Tests no reproducibles: 23 dependen de red

Los tests offline (56) pasan. Los otros 23 hacen llamadas reales:

- `tests/test_macro.py` → `calculate_market_regime()` descarga VIX, SPY, treasuries y DXY.
- `tests/test_news.py` → `get_news_summary()` llama Finnhub/Marketaux.
- `tests/test_phase_h_full_integration.py` → `generate_dossier()` y `generate_executive_report()` descargan yfinance, macro y noticias.

En un entorno sin red (o sin claves) el suite se cuelga o falla de forma intermitente. En CI es inservible tal cual.

**Acción:** marcar esos tests con `@pytest.mark.integration` y excluirlos por defecto (`-m "not integration"`), y en una segunda fase mockear yfinance/HTTP para convertirlos en tests herméticos.

### P0-5. Documentación desactualizada y contradictoria

Ejemplos concretos:

| Documento | Problema |
|---|---|
| `README.md:10,22,141` | Dice stop `1.5×ATR`; el sistema usa `2.5×` (estándar) y `3.0×` (apalancados 3x). |
| `AGENTS.md:51` | Dice "35 activos"; el universo real tiene **28** (`config/universe.py`). |
| `AGENTS.md:12` vs `MEMORY.md:11` | Una dice comisión "por rebalanceo"; la otra, "semanal siempre". El código no aplica ninguna. |
| `MANUAL.md:74` | `from config.loader import load_env` → **esa función no existe**. |
| `MANUAL.md:88-93` | Dice que el pipeline genera 3 reportes (incluido el ejecutivo); `run_weekly.py` **nunca llama** a `executive_report.py`. |
| `README.md` | Estructura incompleta: no menciona `macro.py`, `news.py`, `fundamentals.py`, `technicals_deep.py`, `narrative.py`, `executive_report.py`, `templates/`. |
| `MANUAL.md` | Rutas absolutas de una máquina concreta y URL de un repo privado (404). |
| `README.md` | Se presenta como proyecto personal con capital real; no como proyecto open source. |

**Acción:** reescribir README, sanear MANUAL, corregir AGENTS/MEMORY o retirarlos, y unificar la fuente de verdad de parámetros en `config/settings.yaml`.

### P0-6. Un clone limpio no arranca

`run_weekly.py:38-41` exige `state/portfolio.json` y aborta si no existe. Ese archivo está ignorado y no hay plantilla ni comando de inicialización.

**Acción:** añadir `examples/portfolio.example.json`, un comando `init` (o auto-creación desde el ejemplo) y documentar el primer arranque.

### P0-7. Sin CI

No hay `.github/workflows/`. Para un proyecto open source, el CI es la garantía mínima de que un PR no rompe nada.

**Acción:** workflow de lint + tests offline en Python 3.10–3.13, y un job opcional de integración manual.

---

## 4. Bugs y deuda técnica P1 (corregir antes o justo después de publicar)

| ID | Severidad | Archivo | Problema | Fix propuesto |
|---|---|---|---|---|
| C1 | 🔴 Alta | `src/narrative.py:53-62,195` | `basic_values` no incluye `price`, pero se lee `position_data['basic'].get('price', entry)`. **Siempre** usa el precio de entrada para el stop calculado del dossier. | Añadir `'price': basic.get('price', 0)` a `basic_values`. |
| C2 | 🔴 Alta | `src/run_weekly.py:129-133` | `generate_stop_report(...)` se llama sin `ticker`; TQQQ usa el multiplicador estándar `2.5×` en vez de `3.0×`. | Pasar `ticker=candidate['ticker']`. |
| C3 | 🔴 Alta | `src/report.py:204` | El pitch calcula el stop con `1.5×ATR` hardcodeado, ignorando la categoría. | Usar `calculate_stop_by_category` (ya se usa en la tabla Top 3). |
| C4 | 🟡 Media | `src/report.py:307` | Capital personal hardcodeado como fallback. | Recibir `capital_mxn` por parámetro; fallback a config/ejemplo, nunca a una cifra personal. |
| C5 | 🟡 Media | `src/executive_report.py:200` | Tipo de cambio USD/MXN hardcodeado (`/ 20`). | Configurar `fx.usd_mxn` o descargar `MXN=X`; documentar el supuesto. |
| C6 | 🟡 Media | `src/earnings.py:86-91,108-109` | Ventana de earnings mal calculada (hasta ~12 días) y `get_earnings_date` se llama **dos veces** por ticker. | Calcular lunes-viernes de la semana siguiente con `date.weekday()`; reutilizar la fecha ya obtenida. |
| C7 | 🔴 Alta | `src/decision.py:149-159` | Solo evalúa el **primer** candidato distinto al actual. Si el rank 1 falla el hurdle, no prueba el rank 2, aunque cumpla. | Iterar todos los candidatos ordenados y quedarse con el primero que cumpla hurdle, EMA21, R:B e idoneidad. |
| C8 | 🔴 Alta | `src/decision.py:323-379` | La comisión del `0.20%` no se aplica en ninguna parte. `execute_rotation` ignora comisiones y no usa el `-0.20%` del mandato. | Aplicar comisión de entrada/salida (según se defina) y registrarla en el historial. |
| C9 | 🟡 Media | `src/risk.py:231` | `remaining_capital = capital_mxn + risk_mxn`; si salta el stop, el capital **baja**, no sube. | `capital_mxn - risk_mxn`. |
| C10 | 🟡 Media | `src/scoring.py:157-164` | Los pesos del scoring están duplicados en código; `config/settings.yaml` no se lee. Cambiar el YAML no cambia el resultado. | Cargar pesos/rangos desde `config.loader`. |
| C11 | 🟡 Media | `src/scoring.py:24-32,79-89` | Si un indicador es `NaN` (histórico insuficiente), el score puede dar 100 o 0 de forma silenciosa. | Validar `pd.isna` y devolver un score neutro/None; descartar activos sin datos mínimos. |
| C12 | 🟡 Media | `src/news.py:40-48,71` | Finnhub recibe el token en la URL y `raise_for_status()` puede incluir esa URL en el log de error → **fuga de API key en logs**. | Usar cabecera `X-Finnhub-Token` cuando sea posible y loggear mensajes saneados. |
| C13 | 🟡 Media | `src/executive_report.py:60,103,150`; `src/report.py:312` | `except:` desnudos y `except Exception: pass`. Ocultan fallos de red y de datos. | Capturar excepciones concretas, loggear y degradar con valores por defecto. |
| C14 | 🟡 Media | `src/ingest.py:72,97,118`; `src/report.py:261`; `src/decision.py:14`; etc. | Rutas relativas al CWD. Ejecutar desde otro directorio rompe `data/`, `output/` y `state/`. | Constante `PROJECT_ROOT = Path(__file__).resolve().parent.parent` y rutas derivadas. |
| C15 | 🟡 Media | `src/executive_report.py:27-162` | Duplica el motor de decisión (`determine_decision`) con reglas distintas: no aplica régimen RISK_OFF/cash proxy, no aplica idoneidad y usa `1.5×ATR`. | Reutilizar `src.decision.make_decision` como única fuente de verdad. |
| C16 | 🟡 Media | `src/narrative.py:126-147` | Accede a `position_data['basic']` sin comprobar que `get_position_data` devolvió `{}`; si falla la red, `KeyError`. | Guardas y defaults; marcar el dossier como incompleto. |
| C17 | 🟢 Baja | `src/run_weekly.py:14,126` | Imports sin usar (`download_weekly_data`, `load_ticker_data`, `get_top_n`) y numeración de pasos duplicada (dos "7"). | Limpiar imports y renumerar. |
| C18 | 🟢 Baja | `src/executive_report.py:201` | `int(capital_usd / candidate_price)` divide por cero si el candidato no tiene precio. | Validar `candidate_price > 0`. |
| C19 | 🟢 Baja | `src/secrets.py:37` | El parser sobrescribe `os.environ` y no maneja comillas/`export`; puede pisar variables del sistema. | `os.environ.setdefault`, `strip('"\'')`, o usar `python-dotenv`. |
| C20 | 🟢 Baja | `src/risk.py:9,165,254` | Defaults `1.5×ATR` inconsistentes con la configuración `2.5/3.0`. | Unificar el default o eliminarlo. |
| C21 | 🟢 Baja | `src/earnings.py:61-63` | Excepción silenciada sin log; difícil diagnosticar. | `logger.debug(...)` con el ticker. |
| C22 | 🟢 Baja | `src/indicators.py:216-233` | `float(last.get(...))` puede lanzar si la columna no existe; `last` es una Serie y `.get` funciona, pero los `NaN` se propagan. | Validar columnas y `dropna` antes de extraer. |

---

## 5. Brechas de calidad open source (P1/P2)

### 5.1 Estructura y automatización

- [ ] `pyproject.toml` con metadata, dependencias, extras `dev`, `[tool.ruff]`, `[tool.pytest.ini_options]`, `[tool.coverage]`.
- [ ] `ruff` (lint + format) y `pre-commit` (ruff, trailing-whitespace, end-of-file, check-yaml, detect-secrets).
- [ ] CI en GitHub Actions: matriz 3.10–3.13, lint, tests offline, cobertura.
- [ ] `dependabot.yml` para pip y GitHub Actions.
- [ ] CodeQL o `bandit` para seguridad.
- [ ] `Makefile` con `install`, `test`, `lint`, `format`, `run`.
- [ ] `Dockerfile` opcional (reproducibilidad).
- [ ] `requirements.txt` completo + `requirements-dev.txt`, o solo `pyproject.toml`.

### 5.2 Comunidad y gobernanza

- [ ] `LICENSE`.
- [ ] `CONTRIBUTING.md` (setup, tests, estilo, PRs).
- [ ] `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1).
- [ ] `SECURITY.md` (reporte de vulnerabilidades y manejo de API keys).
- [ ] `CHANGELOG.md` (Keep a Changelog).
- [ ] `.github/ISSUE_TEMPLATE/bug_report.yml` y `feature_request.yml`.
- [ ] `.github/PULL_REQUEST_TEMPLATE.md`.
- [ ] `docs/ARCHITECTURE.md` y `docs/STRATEGY.md`.
- [ ] `CITATION.cff` si se quiere citar académicamente.

### 5.3 Documentación de producto

- [ ] README en inglés (alcance global) + `README.es.md` (español).
- [ ] Badges: CI, licencia, Python, cobertura.
- [ ] Diagrama de arquitectura (Mermaid) y flujo semanal.
- [ ] Quickstart de 5 comandos, con `examples/portfolio.example.json`.
- [ ] Captura o ejemplo de reporte generado.
- [ ] Tabla de configuración (`settings.yaml`) con valores por defecto.
- [ ] Sección de limitaciones y disclaimer financiero fuerte.
- [ ] Roadmap público (backtesting, comisiones, FX, validación).

### 5.4 Empaquetado y UX

- [ ] Instalación `pip install -e .`.
- [ ] Entrypoint `swing-trading` (o `python -m swing_trading`).
- [ ] Comando `init` para crear `state/portfolio.json` desde el ejemplo.
- [ ] Flags `--offline`, `--dry-run`, `--ticker`, `--output-dir`.
- [ ] Logging configurable en lugar de `print` (mantener salida humana en CLI).
- [ ] Manejo claro de errores cuando faltan API keys o datos.

---

## 6. Riesgos de estrategia y validación (importante para el README)

El proyecto **no es un sistema validado**. Es un motor de reglas con parámetros no calibrados. Antes de presentarlo como "sistema cuantitativo", el README debe declarar:

1. **Sin backtest.** No hay evidencia histórica de que la combinación de pesos, hurdle de 15 puntos, ATR 2.5/3.0 y filtro de régimen genere alpha.
2. **Sin comisiones ni slippage en las métricas.** El `0.20%` está en la documentación, pero no en el código.
3. **Sin FX.** Capital en MXN, activos en USD; el riesgo USD/MXN no se modela (y el reporte ejecutivo usa un tipo de cambio fijo).
4. **Concentración 100% en un activo + ETFs 3x.** El riesgo de ruina es material; el stop no protege contra gaps.
5. **Sesgo de supervivencia y de selección.** El universo son 28 activos elegidos a mano, todos ganadores recientes de liquidez/momentum.
6. **Sobreajuste plausible.** Muchos parámetros (pesos, rangos ideales, cap 12%, hurdle 15) sin validación out-of-sample.
7. **Datos de yfinance.** No garantizados, sujetos a cambios de API y a los términos de Yahoo. No redistribuir datos descargados.

**Recomendación:** posicionarlo como **framework educativo de investigación y automatización**, no como asesor financiero ni como estrategia probada. Añadir un disclaimer prominente y un `docs/LIMITATIONS.md`.

---

## 7. Inventario de datos personales

| Archivo | Dato | Acción |
|---|---|---|
| `README.md` | Capital, posición, retorno, stop, fecha | Reemplazar por ejemplo ficticio o eliminar sección. |
| `MEMORY.md` | Capital, operaciones, fechas y decisiones | No publicar; convertir en `CHANGELOG.md` sanitizado o `docs/PROJECT_LOG.md` sin cifras. |
| `MANUAL.md` | Rutas absolutas, usuario GitHub, capital de ejemplo | Generalizar rutas (`$PWD`, `~/proyecto`) y usar cifras ficticias. |
| `AGENTS.md` | Referencias al contexto del curso | Generalizar a "operador" / "revisión semanal". |
| `state/portfolio.json` | Datos reales | Ya ignorado; crear `examples/portfolio.example.json`. |
| Historial Git | Todo lo anterior | Reescribir historia o publicar historia limpia. |
| Autor de commits | Email universitario | Configurar email noreply de GitHub para commits públicos. |

---

## 8. Estructura objetivo propuesta

```text
educational-quant-trading/
├── .github/
│   ├── workflows/ci.yml
│   ├── workflows/codeql.yml
│   ├── ISSUE_TEMPLATE/{bug_report,feature_request}.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── dependabot.yml
├── docs/
│   ├── ARCHITECTURE.md
│   ├── STRATEGY.md
│   ├── LIMITATIONS.md
│   ├── ROADMAP.md
│   ├── OPEN_SOURCE_AUDIT.md
│   └── assets/                 # diagramas e imágenes
├── examples/
│   ├── portfolio.example.json
│   └── report.example.md
├── src/                        # se mantiene (o se renombra a swing_trading/ en una fase posterior)
├── config/
├── tests/
├── templates/
├── .editorconfig
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── CHANGELOG.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
├── Makefile
├── README.md                   # inglés
├── README.es.md                # español
├── SECURITY.md
├── pyproject.toml
└── requirements-dev.txt
```

> Nota: renombrar `src/` a `swing_trading/` es lo correcto para empaquetar, pero toca imports, tests y docs. Se puede posponer a una fase posterior si se quiere publicar rápido.

---

## 9. Plan por fases

### Fase 0 — Decisiones (30 min)
- Licencia, idioma, política de historial, alcance.

### Fase 1 — Higiene y privacidad (2–4 h)
- `LICENSE`, `pyproject.toml`, deps completas.
- Sanear README/MANUAL/AGENTS/MEMORY.
- `examples/portfolio.example.json`.
- `.gitignore` afinado, `.editorconfig`, `.gitattributes`.
- Historia limpia si se elige esa opción.

### Fase 2 — Documentación y comunidad (4–6 h)
- README EN + ES, arquitectura, estrategia, limitaciones, roadmap.
- CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, CHANGELOG.
- Plantillas de issues/PR.

### Fase 3 — CI y calidad (2–4 h)
- GitHub Actions, ruff, pre-commit, pytest markers, cobertura.
- Dependabot, CodeQL.
- Tests offline por defecto.

### Fase 4 — Correcciones de código (1–2 días)
- C1–C22 priorizados: primero C1, C2, C3, C7, C8, C12, C15.
- Añadir tests de regresión para cada fix.

### Fase 5 — Publicación (1 h)
- Repo público, descripción, topics, licencia visible.
- Release `v0.1.0`, tag, release notes.
- Activar secret scanning, Dependabot alerts, private vulnerability reporting.
- Verificar CI en verde y README renderizado.

### Fase 6 — Roadmap (post-publicación)
- Backtesting walk-forward con comisiones/slippage/FX.
- Benchmark vs SPY/QQQ.
- Refactor de paquete `swing_trading/` + CLI.
- Mock completo de red en tests de integración.

---

## 10. Decisiones tomadas y estado de ejecución

**Decisiones (2026-10-22):**

1. **Licencia:** MIT.
2. **Idioma:** bilingüe (README EN + `README.es.md`; documentación técnica en español).
3. **Historial:** historia limpia (rama huérfana `public-release`; el privado se conserva como archivo).
4. **Alcance:** higiene open source + correcciones críticas (C1–C9, C12, C15 y mejoras relacionadas).

**Estado:**

- [x] Fase 0 — Decisiones.
- [x] Fase 1 — Licencia, empaquetado, dependencias, sanitización, ejemplos.
- [x] Fase 2 — README bilingüe, arquitectura, estrategia, limitaciones, roadmap, comunidad.
- [x] Fase 3 — CI, CodeQL, Dependabot, pre-commit, tests offline por defecto.
- [x] Fase 4 — Correcciones C1–C9, C12, C15; tests de regresión.
- [ ] Fase 5 — Publicación en GitHub (requiere crear el repo público y hacer push).
- [ ] Fase 6 — Backtesting y validación (roadmap).

Las tareas de la Fase 5 se documentan paso a paso en [`PUBLISHING.md`](PUBLISHING.md).

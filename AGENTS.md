# AGENTS.md — Contexto para agentes de IA

Este documento define el contexto operativo, las reglas de negocio y las
restricciones del proyecto para cualquier agente de IA que lo modifique. No es
documentación de usuario; para eso consulta `README.md` y `docs/`.

> **Aviso:** este repositorio es un framework educativo de investigación. No es
> asesoría financiera, no garantiza rendimientos y puede perder capital.

---

## 1. Mandato y parámetros de referencia

- **Objetivo de referencia:** +10.0% neto acumulado en 8 semanas.
  - Rendimiento semanal neto requerido: `(1 + 0.10)^(1/8) - 1 ≈ 1.19%`.
- **Estructura de capital:** 100% en un solo activo a la vez (restricción del
  diseño original). No hay diversificación simultánea.
- **Costo transaccional:** 0.20% configurable en `costs.commission_pct`.
  - `costs.charge_on: "weekly"` (default): se cobra una vez por semana ISO.
  - `costs.charge_on: "rotation"`: se cobra solo al ejecutar una rotación.
- **Efectivo sintético:** para una postura defensiva se usa un ETF de
  ultra-baja volatilidad y renta fija corta (`SGOV`, `BIL` o `SHY`).
- **Universo:** 28 activos de alta liquidez definidos en `config/universe.py`
  (10 momentum, 8 sectoriales, 3 apalancados, 4 inversos, 3 defensivos).
- **Fuente de precios:** cierre ajustado de `yfinance`.

---

## 2. Cronograma semanal

| Momento | Tarea |
| --- | --- |
| **Viernes (cierre)** | Se consolidan las velas diarias y semanales. |
| **Sábado** | Se ejecuta `python -m src.run_weekly`: ingesta, indicadores, scoring, régimen y decisión. |
| **Domingo** | Revisión de catalizadores, earnings de la semana entrante y reporte ejecutivo. |
| **Lunes / martes** | Verificación pre-market y ejecución manual de la orden si procede. |

El pipeline **no envía órdenes**. Solo genera recomendaciones y reportes.

---

## 3. Algoritmo de decisión (Hold vs Rotate)

### Condición de mantenimiento (HOLD)

- El activo está por encima de `EMA21` en D1.
- No reporta earnings de lunes a viernes de la semana entrante.
- Su score compuesto está en el top `decision.hold.min_score_percentile`
  (default 30%).
- El activo es apto: el stop requerido no supera `risk.stop_loss.max_risk_pct`
  (default 12%).

### Condición de rotación (ROTATE)

- El activo actual incumple alguna condición de HOLD, **o** el régimen de
  mercado obliga a rotar.
- Se recorre el ranking completo (no solo el líder) y se elige el primer
  candidato que cumpla:
  - `score_candidato - score_actual >= decision.rotate.score_hurdle_points`
    (default 15).
  - Precio sobre `EMA21`.
  - Stop requerido dentro del cap de riesgo.
  - Ratio riesgo/beneficio `>= decision.rotate.min_risk_reward_ratio`
    (default 2:1).

### Salida de dos niveles

1. **Salida blanda:** si el cierre del viernes queda por debajo de `EMA21`, se
   evalúa rotar en la revisión semanal.
2. **Stop duro en reposo:** orden stop en el bróker a:
   - `2.5 × ATR14` para acciones/ETFs estándar.
   - `3.0 × ATR14` para ETFs apalancados 3x (`TQQQ`, `SOXL`, `FNGU`,
     `SQQQ`, `SOXS`).

---

## 4. Universo

```python
UNIVERSE = {
    'MOMENTUM': ['NVDA', 'TSLA', 'META', 'AMZN', 'AAPL', 'MSFT', 'AMD', 'GOOGL', 'NFLX', 'PLTR'],
    'SECTORIAL': ['XLF', 'XLE', 'XLK', 'XBI', 'SMH', 'XLU', 'XLI', 'GDX'],
    'LEVERAGED_LONG': ['TQQQ', 'SOXL', 'FNGU'],
    'INVERSE_SHORT': ['SQQQ', 'SOXS', 'PSQ', 'SPDN'],
    'DEFENSIVE_CASH': ['SGOV', 'BIL', 'SHY'],
}
```

La fuente de verdad es `config/universe.py`. No dupliques esta lista en código
nuevo; importa `get_all_tickers()`.

---

## 5. Mapa de código

| Archivo | Responsabilidad |
| --- | --- |
| `src/ingest.py` | Descarga OHLCV de `yfinance` y valida columnas. |
| `src/indicators.py` | EMA, ATR, RSI, retornos, volatilidad y distancias. |
| `src/scoring.py` | Score compuesto 0–100 y ranking. |
| `src/decision.py` | Motor único HOLD/ROTATE y rotaciones forzadas por régimen. |
| `src/risk.py` | Stops por ATR, idoneidad y R:B. |
| `src/macro.py` | Régimen `RISK_ON` / `NEUTRAL` / `RISK_OFF`. |
| `src/earnings.py` | Ventana de earnings de la semana entrante. |
| `src/news.py` | Noticias y sentimiento (Finnhub / Marketaux). |
| `src/fundamentals.py` | Fundamentales de acciones y ETFs. |
| `src/report.py` | Reporte semanal, screener CSV y pitch. |
| `src/narrative.py` | Dossier para el reporte ejecutivo. |
| `src/executive_report.py` | Reporte ejecutivo Markdown (Jinja2). |
| `src/accounting.py` | Comisiones y retorno acumulado. |
| `src/pipeline.py` | Helpers compartidos de ingesta + ranking. |
| `src/paths.py` | Rutas ancladas a la raíz del proyecto. |
| `config/loader.py` | Carga `settings.yaml` (singleton). |
| `config/secrets.py` | Carga `.env` sin sobrescribir variables del sistema. |

---

## 6. Reglas de contribución para agentes

1. **No introduzcas secretos** ni valores de cartera reales. Usa
   `examples/portfolio.example.json` y `.env.example`.
2. **No hardcodees rutas absolutas.** Usa `src/paths.py`.
3. **No dupliques el motor de decisión.** `src/executive_report.py` debe
   reutilizar `src.decision.make_decision`.
4. **Configura antes de codificar.** Los parámetros numéricos van en
   `config/settings.yaml`, no en funciones.
5. **Añade tests offline** para cada cambio de lógica. Los tests que llaman a
   red deben marcarse con `@pytest.mark.integration`.
6. **No prometas rentabilidad.** Cualquier texto público debe incluir el
   disclaimer de `docs/LIMITATIONS.md`.
7. Ejecuta `python -m pytest -q` y `ruff check .` antes de cerrar un cambio.

---

## 7. Comandos

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp examples/portfolio.example.json state/portfolio.json
python -m src.run_weekly --skip-earnings
python -m src.executive_report
python -m pytest -q
ruff check .
```

# Guía de usuario (ES)

> Esta guía asume que ya clonaste el repositorio. Para la visión general, ver
> [`README.es.md`](../README.es.md). Para la arquitectura, ver
> [`ARCHITECTURE.md`](ARCHITECTURE.md).

> **Aviso:** herramienta educativa. No es asesoría financiera. No opera con
> dinero real ni garantiza resultados.

---

## 1. Requisitos

- Python 3.10 o superior.
- Conexión a internet para descargar datos de mercado.
- Opcional: claves de Finnhub, Marketaux y FRED para noticias, fundamentales y
  macro.

## 2. Instalación

```bash
git clone https://github.com/LuisFernandoTovarFlores/educational-quant-trading.git
cd educational-quant-trading

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Verifica:

```bash
python -m pytest -q
python -m src.run_weekly --help
```

## 3. Configuración

### 3.1 Claves de API (opcional)

```bash
cp .env.example .env
```

Edita `.env`:

```env
FINNHUB_API_KEY=tu_clave
MARKETAUX_API_KEY=tu_clave
FRED_API_KEY=tu_clave
```

- Sin Finnhub, no hay fundamentales ni noticias de empresa.
- Sin Marketaux, no hay sentimiento de noticias.
- Sin FRED, el régimen usa el fallback de yfinance para tasas.
- El pipeline de precios funciona sin ninguna clave.

### 3.2 Parámetros

Edita `config/settings.yaml`:

```yaml
costs:
  commission_pct: 0.20
  charge_on: "weekly"     # o "rotation"

decision:
  hold:
    min_score_percentile: 30
  rotate:
    score_hurdle_points: 15
    min_risk_reward_ratio: 2.0

risk:
  stop_loss:
    multipliers:
      standard: 2.5
      leveraged_3x: 3.0
    max_risk_pct: 12.0

fx:
  usd_mxn: 20.0
```

El universo se edita en `config/universe.py`.

### 3.3 Portafolio

El pipeline necesita `state/portfolio.json`. Créalo desde el ejemplo:

```bash
cp examples/portfolio.example.json state/portfolio.json
```

Edita el archivo con tu posición y capital reales (o ficticios para probar). No
lo commitees: está en `.gitignore`.

Estructura mínima:

```json
{
  "position": {
    "ticker": "AAPL",
    "entry_price_usd": 200.0,
    "entry_date": "2026-01-05",
    "stop_loss_usd": 185.0
  },
  "capital": {
    "initial_mxn": 100000.0,
    "current_mxn": 100000.0,
    "return_pct": 0.0
  },
  "history": [],
  "last_fee_week": null,
  "fees": []
}
```

## 4. Ejecución

### 4.1 Pipeline semanal

```bash
python -m src.run_weekly
```

Pasos:

1. Carga el portafolio y cobra la comisión semanal si corresponde.
2. Descarga datos de los 28 activos.
3. Calcula indicadores y ranking.
4. Detecta el régimen de mercado.
5. Consulta earnings de la semana entrante.
6. Toma la decisión HOLD/ROTATE.
7. Genera el reporte y el screener.

Opciones:

```bash
python -m src.run_weekly --period 6mo
python -m src.run_weekly --skip-earnings
python -m src.run_weekly --no-save-data
python -m src.run_weekly --no-commission
```

### 4.2 Reporte ejecutivo

```bash
python -m src.executive_report
```

Genera `output/executive_YYYY-WW.md` y `output/dossier.json` con fundamentales,
noticias, macro y la decisión del motor único.

Opciones:

```bash
python -m src.executive_report --portfolio state/portfolio.json --output-dir output
```

### 4.3 Automatización semanal

Con cron (macOS/Linux), desde la raíz del repo:

```cron
0 10 * * 6 cd "$HOME/educational-quant-trading" && .venv/bin/python -m src.run_weekly >> output/cron.log 2>&1
```

Ajusta la ruta y el entorno. En Windows, usa el Programador de tareas.

> El pipeline **no ejecuta órdenes**. Solo genera reportes.

## 5. Interpretación de resultados

### 5.1 Acciones de decisión

| Acción | Significado |
| --- | --- |
| `HOLD` | Mantener la posición actual. |
| `ROTATE` | Rotar a un candidato que supera el hurdle. |
| `HOLD_WITH_WARNINGS` | Mantener, pero alguna condición falla y no hay candidato válido. Revisar manualmente. |
| `ROTATE_TO_CASH_PROXY` | Régimen `RISK_OFF`: mover a `SGOV`/`BIL`/`SHY`. |
| `ROTATE_TO_STANDARD` | Régimen `NEUTRAL`: salir de apalancados/inversos. |

### 5.2 Reporte semanal

`output/report_YYYY-WW.md` incluye:

- Régimen de mercado y restricciones.
- Estado del portafolio.
- Decisión y razones.
- Top 3 candidatos.
- Tabla de stops con riesgo % y MXN.
- Earnings de la semana.
- Checklist pre-market.

### 5.3 Screener

`output/screener_YYYY-WW.csv` contiene el universo completo:

| Columna | Significado |
| --- | --- |
| `rank` | Posición en el ranking. |
| `ticker` | Símbolo. |
| `score` | Score compuesto 0–100. |
| `momentum`, `trend`, `volatility`, `liquidity`, `regime` | Componentes. |
| `price` | Último cierre. |
| `RSI14` | RSI de 14 días. |
| `Ret5D`, `Ret20D` | Retornos porcentuales. |
| `ATRpct` | ATR como % del precio. |
| `AboveEMA21` | Tendencia de corto plazo. |
| `stop_loss` | Stop recomendado según categoría. |
| `risk_pct` | Riesgo % del stop (negativo). |
| `risk_mxn` | Riesgo en MXN. |
| `suitable` | `True` si el riesgo ≤ cap (12%). |

### 5.4 Régimen

| Régimen | Interpretación | Restricción |
| --- | --- | --- |
| `RISK_ON` | VIX bajo, SPY sobre medias, curva positiva. | Permite apalancados; excluye cash proxy. |
| `NEUTRAL` | Señales mixtas. | Solo activos estándar. |
| `RISK_OFF` | VIX alto, SPY bajo medias, curva invertida. | Solo cash proxy. |

La confianza es una normalización, no una probabilidad.

### 5.5 Stops

- **2.5 × ATR** para acciones/ETFs 1x.
- **3.0 × ATR** para `TQQQ`, `SOXL`, `FNGU`, `SQQQ`, `SOXS`.
- Si el stop implica más de 12% de riesgo, el activo es **no apto**.
- El stop duro no protege de gaps; puede haber slippage.

## 6. Solución de problemas

### `ModuleNotFoundError: No module named 'yfinance'`

```bash
pip install -e ".[dev]"
```

### `No se encontró state/portfolio.json`

```bash
cp examples/portfolio.example.json state/portfolio.json
```

### `API key not configured` / noticias vacías

Revisa que `.env` exista y tenga las claves. Es opcional; el pipeline de precios
funciona sin ellas.

### `No module named 'fredapi'`

```bash
pip install -e ".[fred]"
```

Si no lo instalas, `macro.py` usa el fallback de yfinance.

### `No data returned by yfinance`

- Verifica la conexión.
- Algunos tickers pueden estar temporalmente sin datos.
- El pipeline continúa con los demás; revisa los warnings.

### El reporte no se genera

- Verifica que `output/` sea escribible.
- Revisa el log; el pipeline devuelve código 1 si falla la carga del portafolio.
- Ejecuta con `python -m src.run_weekly` desde la raíz del repo.

### Los tests se cuelgan

Estás ejecutando tests de integración. Usa:

```bash
python -m pytest -q                    # offline
python -m pytest -q -m integration     # red, más lento
```

### `ValueError: Missing OHLCV columns`

El proveedor devolvió un DataFrame incompleto. Revisa el ticker o reintenta más
tarde. El pipeline excluye ese activo y sigue.

## 7. Flujo semanal recomendado

1. **Viernes:** se consolidan los datos de cierre.
2. **Sábado:** ejecuta `python -m src.run_weekly`.
3. **Domingo:** ejecuta `python -m src.executive_report` y revisa catalizadores.
4. **Lunes/martes:** valida pre-market y ejecuta manualmente si procede.
5. **Registra** el precio real y actualiza `state/portfolio.json`.

## 8. Preguntas frecuentes

**¿Puedo usar otro bróker o mercado?**
Sí, pero el universo y los tickers están pensados para EE. UU. Adapta
`config/universe.py` y verifica que yfinance devuelva datos.

**¿Puedo cambiar el número de activos?**
Sí. El pipeline es agnóstico al tamaño del universo. Mantén la liquidez.

**¿Dónde se guardan mis datos?**
`state/portfolio.json`, `data/raw/` y `output/`. Todo está en `.gitignore`.

**¿El sistema envía órdenes?**
No. Solo genera reportes y recomendaciones.

**¿Sirve para dinero real?**
No sin backtesting, paper trading y una revisión independiente. Ver
[`LIMITATIONS.md`](LIMITATIONS.md).

# Estrategia

> Documento técnico en español. Describe las reglas **tal como están
> implementadas**; la fuente de verdad numérica es `config/settings.yaml`.

## 1. Objetivo y supuestos

El diseño original busca **+10% neto acumulado en 8 semanas** (~1.19% semanal)
con:

- 100% del capital en un solo activo a la vez.
- Comisión de 0.20% (semanal o por rotación, configurable).
- Horizonte de swing de 1 a 8 semanas.
- Activos líquidos de EE. UU. (acciones, ETFs, apalancados e inversos).

> **Esto es una hipótesis de diseño, no una estrategia validada.** No hay
> backtest ni calibración out-of-sample. Ver `LIMITATIONS.md`.

## 2. Universo

`config/universe.py` define 28 tickers en cinco grupos:

| Grupo | Tickers | Rol |
| --- | --- | --- |
| `MOMENTUM` | NVDA, TSLA, META, AMZN, AAPL, MSFT, AMD, GOOGL, NFLX, PLTR | Direccional de alta convicción |
| `SECTORIAL` | XLF, XLE, XLK, XBI, SMH, XLU, XLI, GDX | Rotación sectorial |
| `LEVERAGED_LONG` | TQQQ, SOXL, FNGU | Beta apalancada 3x |
| `INVERSE_SHORT` | SQQQ, SOXS, PSQ, SPDN | Cobertura / dirección inversa |
| `DEFENSIVE_CASH` | SGOV, BIL, SHY | Cash proxy de baja volatilidad |

El universo es una elección discrecional; no hay filtro automático de liquidez.
Para añadir un activo, edita `config/universe.py` y añádelo a la categoría
correcta (la categoría determina el multiplicador de stop si es 3x).

## 3. Indicadores

Se calculan sobre velas diarias (`1d`):

| Indicador | Fórmula / ventana |
| --- | --- |
| `EMA9`, `EMA21` | Media exponencial (`ewm`, `adjust=False`) |
| `ATR14` | True Range con suavizado de Wilder (`alpha=1/14`) |
| `RSI14` | Wilder; 50 si no hay ganancias ni pérdidas |
| `Ret1D`, `Ret5D`, `Ret20D` | `pct_change(n) * 100` |
| `Vol20D` | Desviación estándar de retornos × √252 × 100 |
| `DistHigh20` | `(close - rolling_max_20) / rolling_max_20 * 100` (≤ 0) |
| `DistLow20` | `(close - rolling_min_20) / rolling_min_20 * 100` (≥ 0) |
| `VolRatio` | `volumen / media_20` |
| `ATRpct` | `ATR14 / close * 100` |
| `AboveEMA21` | `close > EMA21` |

Los valores NaN se sustituyen por defaults (`0`, RSI 50, volumen 1.0) para que
un histórico corto no produzca scores artificialmente altos.

## 4. Scoring compuesto

Cada componente devuelve 0–100 y el score final es una suma ponderada:

```text
score = 0.30*momentum + 0.25*trend + 0.20*volatility
      + 0.10*liquidity + 0.15*regime
```

### 4.1 Momentum

```text
raw = Ret5D * 0.4 + Ret20D * 0.6
momentum = clip(50 + raw * 2, 0, 100)
```

`50` es neutro; ±1% de retorno ponderado mueve ~2 puntos.

### 4.2 Tendencia

```text
trend = (50 if AboveEMA21 else 0) + clip(50 + DistHigh20 * 5, 0, 50)
```

Estar sobre EMA21 vale 50 puntos; estar en máximos de 20 días vale hasta 50
puntos adicionales.

### 4.3 Volatilidad

```text
si 2 <= ATRpct <= 5:       100
si ATRpct < 2:             max(0, ATRpct * 50)
si ATRpct > 5:             max(0, 100 - (ATRpct - 5) * 10)
```

El rango ideal 2–5% favorece activos con movimiento suficiente para cubrir
costos sin volatilidad extrema.

### 4.4 Liquidez

```text
si 0.8 <= VolRatio <= 1.5: 100
si VolRatio < 0.8:         max(0, VolRatio * 125)
si VolRatio > 1.5:         max(0, 100 - (VolRatio - 1.5) * 20)
```

Busca volumen normal/alto sin picos de capitulación.

### 4.5 Régimen (RSI)

```text
si 50 <= RSI <= 70:  100
si RSI < 50:         max(0, RSI * 2)
si RSI > 70:         max(0, 100 - (RSI - 70) * 2)
```

Evita sobrecompra extrema y penaliza sobreventa.

### 4.6 Ranking y top 30%

`rank_universe` ordena por score descendente y asigna `rank`. El corte del top
`p`% usa `cutoff = max(1, int(n * p / 100))`; un activo está dentro si su índice
es menor que `cutoff`.

## 5. Régimen de mercado

`calculate_market_regime` puntúa cuatro bloques:

| Bloque | Señal | Puntos |
| --- | --- | --- |
| VIX | < 15 / < 20 / < 25 / < 30 / ≥ 30 | +2 / +1 / 0 / −1 / −2 (risk_off) |
| SPY | > 50d y > 200d / > 200d / < 200d y < 50d / resto | +2 / +1 / −2 / −1 |
| Curva 10Y–2Y | > 1.0 / > 0 / > −0.5 / resto | +2 / +1 / 0 / −2 |
| DXY | tendencia 20d < −2% / > +2% | +1 / −1 |

Regla de clasificación:

- `RISK_ON` si `risk_on_score >= 3`.
- `RISK_OFF` si `risk_off_score >= 3` y no se cumple lo anterior.
- `NEUTRAL` en otro caso.

La confianza se normaliza por `total_indicadores * 2`. Si falta un bloque, se
omite y baja el denominador.

### 5.1 Rotaciones forzadas

- **`RISK_OFF`:** si la posición no es cash proxy, se fuerza la rotación al mejor
  cash proxy (`ROTATE_TO_CASH_PROXY`).
- **`NEUTRAL`:** si la posición es apalancada o inversa, se fuerza la rotación a
  un activo estándar (`ROTATE_TO_STANDARD`).
- **`RISK_ON`:** se permite todo excepto cash proxy.

## 6. Decisión Hold / Rotate

### 6.1 HOLD

Se mantiene solo si se cumplen **todas**:

1. `AboveEMA21 == True`.
2. Sin earnings de lunes a viernes de la semana entrante.
3. Score en el top `min_score_percentile` (30%).
4. Activo apto: `abs(risk_pct) <= max_risk_pct` (12%).

Si falla una, se evalúa rotación. Si no hay candidato válido, la acción es
`HOLD_WITH_WARNINGS`.

### 6.2 ROTATE

Se recorre el ranking completo (no solo el líder) y se elige el **primer**
candidato que cumpla:

1. No es la posición actual.
2. Precio y ATR válidos (> 0).
3. `AboveEMA21 == True`.
4. `is_trade_suitable(ticker, price, atr) == True`.
5. `score_candidato - score_actual >= 15`.
6. `R:B = (target - price) / (price - stop) >= 2.0`.

El ranking está ordenado, así que si un candidato no alcanza el hurdle, los
siguientes tampoco; el bucle se detiene.

`target` se aproxima con el máximo de 20 días implícito:

```text
target = price * (1 + abs(DistHigh20) / 100)
```

Si el activo está exactamente en máximos (`DistHigh20 == 0`), el target es el
precio actual y el R:B es 0: no se rota. Es una aproximación conservadora, no
una proyección.

## 7. Riesgo y stops

### 7.1 Stop por ATR

```text
stop = price - multiplier * ATR14
```

| Categoría | Multiplicador |
| --- | --- |
| Acciones y ETFs 1x | 2.5 |
| ETFs apalancados 3x (`TQQQ`, `SOXL`, `FNGU`, `SQQQ`, `SOXS`) | 3.0 |

### 7.2 Idoneidad

```text
risk_pct = (stop - price) / price * 100
suitable = abs(risk_pct) <= 12.0
```

Si el stop requerido implica más de 12% de riesgo, el activo no es apto para
este mandato concentrado. Ejemplo: un ETF con ATR 7.5% y multiplicador 3.0
implica −22.5% → no apto.

### 7.3 Rango semanal esperado

```text
weekly_range = 2.24 * ATR14     # ≈ √5 * ATR diario
```

Se usa como referencia de movimiento esperado, no como garantía.

### 7.4 Salida de dos niveles

1. **Blanda:** cierre del viernes < EMA21 → se evalúa rotar en la revisión.
2. **Dura:** stop en reposo a 2.5x/3.0x ATR, para proteger ante gaps.

El stop duro no evita un gap: es una orden límite/stop que puede ejecutarse con
slippage.

## 8. Costos y contabilidad

`costs.commission_pct` (0.20%) se aplica según `costs.charge_on`:

- **`weekly` (default):** una vez por semana ISO. `last_fee_week` evita cobrar
  dos veces si el pipeline se ejecuta varias veces en la misma semana.
- **`rotation`:** solo cuando se llama a `execute_rotation`.

La comisión se descuenta del capital y se registra en `portfolio["fees"]`. El
retorno acumulado se recalcula como:

```text
return_pct = (current_mxn - initial_mxn) / initial_mxn * 100
```

## 9. Ejemplo numérico

Supongamos:

- Posición actual: score 60, sobre EMA21, sin earnings, top 30%, apta.
- Candidato: score 78, precio 100, ATR 2, `DistHigh20 = -10`.

```text
score_diff = 78 - 60 = 18 >= 15          ✅
stop       = 100 - 2.5*2 = 95            ✅
risk_pct   = (95-100)/100*100 = -5%      ✅ (<= 12%)
target     = 100 * (1 + 10/100) = 110
R:B        = (110-100)/(100-95) = 2.0    ✅ (>= 2.0)
```

La posición actual cumple HOLD, así que el sistema **mantiene** (el HOLD tiene
prioridad). Si fallara EMA21, rotaría al candidato.

## 10. Qué no modela

- Slippage, spread, impacto de mercado.
- Gap risk y liquidez intraday.
- Impuestos, FX, comisiones del bróker distintas de la configurada.
- Correlación entre activos (solo hay uno a la vez).
- Volatility decay de ETFs apalancados.
- Supervivencia del universo ni sesgo de selección.
- Ejecución real: el sistema solo recomienda.

## 11. Referencias

- `docs/STRATEGY_RESEARCH.md`: revisión de estrategias y fundamentos académicos.
- `docs/ENGINEERING_REVIEW_2026-10.md`: revisión técnica y roadmap de mejoras.
- `docs/LIMITATIONS.md`: riesgos y advertencias.

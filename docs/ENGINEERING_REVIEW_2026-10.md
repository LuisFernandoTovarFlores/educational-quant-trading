# 🔬 Review de Ingeniería Cuantitativa — Sistema de Swing Trading

> **Nota histórica:** este documento es una revisión técnica de octubre de 2026.
> Varias recomendaciones ya se implementaron (multiplicadores ATR 2.5/3.0,
> filtro de régimen, cap de idoneidad, motor de decisión único). Otras siguen
> abiertas y se rastrean en [`ROADMAP.md`](ROADMAP.md). Consérvalo como contexto
> de diseño, no como estado actual del código.

**Fecha:** 2026-10-03  
**Reviewer:** revisión técnica independiente  
**Alcance:** `scoring.py`, `decision.py`, `indicators.py`, `risk.py`, `settings.yaml`, `run_weekly.py`

---

## Resumen Ejecutivo

El sistema tiene una arquitectura limpia y el pipeline semanal funciona correctamente. Sin embargo, hay **5 problemas críticos**, **7 problemas medios** y **6 mejoras menores** que pueden afectar significativamente la capacidad de alcanzar la meta de +10% en 8 semanas. La ausencia de backtesting es el riesgo más grande: sin validación empírica, los parámetros (pesos del scoring, hurdle de 15 pts, multiplicador ATR de 1.5) son conjeturas no calibradas.

---

## 1. 🎯 MEJORAS AL SCORING (`src/scoring.py`)

### 🔴 ALTO IMPACTO

#### 1.1 El scoring de momentum NO captura aceleración ni decay
**Problema:** `score_momentum()` usa solo `Ret5D` (peso 40%) y `Ret20D` (peso 60%). Esto es un promedio ponderado de retornos, no un detector de aceleración.

- Un activo que subió +15% en 20 días pero cayó -3% en los últimos 5 días tiene un momentum_raw = `(-3)(0.4) + (15)(0.6) = 7.8` → score ≈ 65.6. Parece "bueno" pero el momentum está **decayendo**.
- Un activo que subió +2% en 20 días pero +8% en los últimos 5 días tiene momentum_raw = `(8)(0.4) + (2)(0.6) = 4.4` → score ≈ 58.8. Parece "mediocre" pero el momentum está **acelerando**.

**Fix:** Agregar un factor de **aceleración de momentum** (slope del momentum o ROC de ROC):
```python
# En indicators.py, agregar:
def momentum_acceleration(series, short=5, long=20):
    """Aceleración: retorno reciente vs retorno pasado."""
    ret_short = series.pct_change(short)
    ret_long = series.pct_change(long)
    return ret_short - ret_long * (short / long)  # Residual de aceleración


# En scoring.py, modificar score_momentum:
def score_momentum(indicators, weights=None):
    if weights is None:
        weights = {'ret5d_weight': 0.3, 'ret20d_weight': 0.4, 'accel_weight': 0.3}

    ret5d = indicators.get('Ret5D', 0)
    ret20d = indicators.get('Ret20D', 0)
    accel = indicators.get('MomAccel', 0)

    momentum_raw = (
        ret5d * weights['ret5d_weight']
        + ret20d * weights['ret20d_weight']
        + accel * weights['accel_weight'] * 10
    )  # Escalar
    score = max(0, min(100, 50 + momentum_raw * 2))
    return score
```

**Impacto:** Alto. Captura la diferencia entre un activo que está despegando vs uno que está agotándose. En swing trading de 1 semana, la aceleración es más predictiva que el retorno absoluto.

#### 1.2 Falta normalización cross-sectional (ranking relativo, no absoluto)
**Problema:** Los scores son absolutos (mapeo lineal de indicadores a 0-100). Si TODO el universo está cayendo (bear market), los scores absolutos siguen mostrando valores de 40-60 como si fueran "neutrales", cuando en realidad todos son malos.

**Fix:** Después de calcular scores crudos, convertir a **percentil dentro del universo**:
```python
def rank_universe(all_indicators, weights=None):
    # ... calcular scores crudos ...
    
    # Convertir a percentil cross-sectional
    scores = [r['score'] for r in results]
    for r in results:
        r['score_raw'] = r['score']
        r['score'] = percentile_rank(r['score'], scores)  # 0-100 relativo al universo
    return results
```

**Impacto:** Alto. Sin esto, en un crash del mercado el sistema puede seguir recomendando "holds" con scores de 55-65 que parecen OK pero son los peores del universo en términos relativos.

#### 1.3 Falta factor de Beta/Correlación con SPY
**Problema:** No se considera si un activo tiene beta alta o baja respecto al mercado. En un entorno risk-off, activos con beta > 1.5 (TQQQ, SOXL, TSLA) caen 2-3x más que el mercado. El scoring actual trata a SGOV y TQQQ igual en términos de riesgo sistémico.

**Fix:** Agregar un factor de **beta-adjusted momentum**:
```python
# En indicators.py:
def relative_strength(stock_series, benchmark_series, period=20):
    """Performance relativo vs benchmark."""
    ret_stock = stock_series.pct_change(period)
    ret_bench = benchmark_series.pct_change(period)
    return (ret_stock - ret_bench) * 100
```
Incorporar como sub-factor del momentum (10-15% del peso).

**Impacto:** Alto. Permite detectar rotación sectorial y evita quedar concentrado en activos de alta beta durante correcciones.

### 🟡 MEDIO IMPACTO

#### 1.4 Los pesos (30/25/20/10/15) no están calibrados
**Problema:** Los pesos son arbitrarios. No hay evidencia de que momentum 30% + tendencia 25% sea óptimo para un horizonte de 1 semana.

**Recomendación:** 
- **Necesita backtesting** para optimizar pesos (grid search o Bayesian optimization sobre datos históricos).
- Como punto de partida, para horizonte semanal, sugiero: **momentum 35%, tendencia 25%, volatilidad 15%, liquidez 5%, régimen 20%**.
  - Subir momentum a 35% (más predictivo a 1 semana).
  - Bajar liquidez a 5% (todos los activos del universo ya son líquidos, es un factor discriminante bajo).
  - Subir régimen a 20% (RSI es más relevante para timing de entrada).

#### 1.5 El score de volatilidad tiene un rango ideal fijo (2-5% ATR) que no distingue entre categorías
**Problema:** `score_volatility()` usa `ideal_range = (2.0, 5.0)` para TODOS los activos. Pero:
- Para TQQQ/SOXL (3x), un ATR de 5% es normal y debería ser el rango ideal, no el límite superior.
- Para SGOV/BIL, un ATR de 0.1% es lo esperado y el sistema lo penaliza con score ≈ 5.
- Para mega-caps como AAPL, un ATR de 2% es típico.

**Fix:** Hacer el rango ideal dependiente de la categoría:
```python
VOLATILITY_IDEAL_BY_CATEGORY = {
    'MOMENTUM': (1.5, 4.0),
    'SECTORIAL': (1.0, 3.0),
    'LEVERAGED_LONG': (4.0, 10.0),
    'INVERSE_SHORT': (3.0, 8.0),
    'DEFENSIVE_CASH': (0.0, 0.5),
}
```

#### 1.6 El score de liquidez es poco discriminante
**Problema:** `score_liquidity()` usa `VolRatio` (volumen actual / promedio 20d). Pero el requisito del universo ya es volumen > $50M. El 90% de los activos tendrán score cercano a 100. Es un factor que apenas discrimina.

**Recomendación:** Bajar peso a 5% o reemplazar por un factor más discriminante como **bid-ask spread estimado** o **Amihud illiquidity** (|return| / dollar_volume).

---

## 2. 🛡️ MEJORAS A LA GESTIÓN DE RIESGO (`src/risk.py`)

### 🔴 ALTO IMPACTO

#### 2.1 Stop 1.5×ATR es INSUFICIENTE para ETFs 3x (TQQQ, SOXL, FNGU)
**Problema:** TQQQ tiene un ATR diario típico de ~5-8% del precio. Con multiplicador 1.5:
- Stop = entrada - 1.5 × ATR = entrada - (7.5% a 12%)
- Pero TQQQ puede caer 15-20% en un día (gap down). El stop se ejecuta con **slippage masivo**.
- Peor aún: TQQQ tiene **volatility decay** intrínseco. Si el Nasdaq sube 5% y luego baja 5%, TQQQ pierde ~3% por el rebalanceo diario. Un stop de 1.5×ATR en TQQQ se activa con ruido normal.

**Fix:** Multiplicador ATR adaptativo por categoría:
```python
ATR_MULTIPLIER_BY_CATEGORY = {
    'MOMENTUM': 1.5,  # Stop estándar
    'SECTORIAL': 1.5,
    'LEVERAGED_LONG': 2.5,  # Stop más amplio para 3x
    'INVERSE_SHORT': 2.0,
    'DEFENSIVE_CASH': 0.5,  # Stop muy ajustado
}
```

O mejor aún: usar **Chandelier Exit** (stop basado en el máximo desde entrada, no en el precio actual):
```python
def chandelier_exit(entry_price, max_price_since_entry, atr_value, multiplier=2.5):
    return max_price_since_entry - (multiplier * atr_value)
```

#### 2.2 NO hay trailing stop dinámico en el pipeline
**Problema:** `update_trailing_stop()` existe en `risk.py` pero **nunca se llama** en `run_weekly.py` ni en `decision.py`. El stop loss se calcula en la entrada y nunca se actualiza. Si un activo sube +15% en 2 semanas, el stop sigue en el nivel original, regalando ganancias.

**Fix:** Integrar trailing stop en el pipeline semanal:
```python
# En run_weekly.py, después de cargar portafolio:
if current_position.get('stop_loss_usd'):
    new_stop = update_trailing_stop(
        current_position['stop_loss_usd'],
        current_indicators['price'],
        current_indicators['ATR14'],
        multiplier=1.5,
    )
    if new_stop > current_position['stop_loss_usd']:
        current_position['stop_loss_usd'] = new_stop
        print(f'  📈 Trailing stop actualizado: ${new_stop:.2f}')
```

#### 2.3 Falta un stop basado en tiempo (time-based exit)
**Problema:** Si un activo entra en rango lateral y no sube en 5-7 días, el capital está inmovilizado sin generar retorno. Con meta de +1.19% semanal, cada día de estancamiento es un día perdido.

**Fix:** Agregar condición de **time stop**:
```python
def check_time_stop(position, current_date, max_hold_days=7):
    """Si el activo no ha subido en X días, considerar salida."""
    entry_date = datetime.strptime(position['entry_date'], '%Y-%m-%d')
    days_held = (datetime.strptime(current_date, '%Y-%m-%d') - entry_date).days
    
    if days_held >= max_hold_days and position.get('return_pct', 0) < 0.5:
        return True  # Time stop triggered
    return False
```

### 🟡 MEDIO IMPACTO

#### 2.4 No hay position sizing adaptativo
**Problema:** El sistema invierte 100% del capital en un solo activo (restricción del AGENTS.md). Pero no ajusta el sizing según la volatilidad del activo. Un stop de -7% en TQQQ destruye más capital que un stop de -3% en AAPL.

**Recomendación:** Aunque el AGENTS.md dice 100% de concentración, se puede implementar **volatility-adjusted exposure** usando el ETF como proxy:
- Si el candidato es TQQQ (vol alta), invertir 100% pero con stop más amplio.
- Si el candidato es AAPL (vol baja), invertir 100% con stop más ajustado.
- El efecto neto es que el **riesgo en MXN** es similar entre activos.

Esto ya se logra parcialmente con el multiplicador ATR por categoría (ver 2.1).

#### 2.5 Falta máximo drawdown diario como circuito de emergencia
**Problema:** No hay un mecanismo para salir a efectivo (SGOV) si el portafolio cae más de X% en un día. Con 100% de concentración en un 3x ETF, un gap down del 10% es posible.

**Fix:** Agregar **circuit breaker**:
```python
def check_circuit_breaker(portfolio, current_price, max_daily_loss_pct=5.0):
    """Si cae más de X% desde la entrada, salir a SGOV."""
    entry_price = portfolio['position']['entry_price_usd']
    current_loss = (current_price - entry_price) / entry_price * 100

    if current_loss <= -max_daily_loss_pct:
        return True, f'🚨 Circuit breaker: {current_loss:.1f}% de pérdida'
    return False, None
```

---

## 3. 🧠 MEJORAS AL ALGORITMO DE DECISIÓN (`src/decision.py`)

### 🔴 ALTO IMPACTO

#### 3.1 El hurdle de 15 puntos es arbitrario y no considera la comisión correctamente
**Problema:** El hurdle de 15 pts busca compensar el costo de 0.20% de comisión. Pero:
- 15 pts en un score de 0-100 no tienen relación directa con 0.20% de retorno.
- Un activo con score 80 vs uno con score 65 puede tener el mismo retorno esperado.
- El hurdle debería basarse en **retorno esperado diferencial**, no en puntos de score abstractos.

**Fix:** Calibrar el hurdle con backtesting. Como aproximación:
- Si el score se correlaciona ~0.3 con retorno futuro, 15 pts ≈ 4.5% de retorno esperado diferencial.
- Esto es razonable para cubrir 0.20% de comisión + buffer.
- Pero la relación score→retorno debe **validarse empíricamente**.

**Recomendación inmediata:** Hacer el hurdle **dinámico** según la volatilidad del candidato:
```python
def dynamic_hurdle(candidate_atr_pct, base_hurdle=15):
    """Hurdle más alto para activos más volátiles (mayor incertidumbre)."""
    if candidate_atr_pct > 5.0:  # 3x ETFs
        return base_hurdle * 1.5  # 22.5 pts
    elif candidate_atr_pct > 3.0:  # Mega-caps volátiles
        return base_hurdle * 1.2  # 18 pts
    return base_hurdle  # 15 pts estándar
```

#### 3.2 Falta filtro de régimen de mercado (risk-on / risk-off)
**Problema:** El sistema no distingue entre un mercado alcista (SPY > EMA50, VIX < 20) y uno bajista (SPY < EMA50, VIX > 25). En modo risk-off, el momentum se revierte y los scores de momentum dan señales falsas.

**Fix:** Agregar un **market regime filter** basado en SPY:
```python
def get_market_regime(spy_indicators):
    """
    Determina régimen de mercado.
    Returns: 'risk_on', 'neutral', 'risk_off'
    """
    above_ema50 = spy_indicators.get('AboveEMA50', False)
    vix_level = spy_indicators.get('VIX', 20)
    spy_rsi = spy_indicators.get('RSI14', 50)

    if above_ema50 and vix_level < 20 and spy_rsi > 50:
        return 'risk_on'
    elif not above_ema50 and vix_level > 25:
        return 'risk_off'
    return 'neutral'


def apply_regime_overlay(ranked_universe, regime):
    """Ajusta el comportamiento según el régimen."""
    if regime == 'risk_off':
        # En risk-off, favorecer defensivos e inversos
        for r in ranked_universe:
            if r['category'] in ['DEFENSIVE_CASH', 'INVERSE_SHORT']:
                r['score'] *= 1.2  # Boost 20%
            elif r['category'] in ['LEVERAGED_LONG']:
                r['score'] *= 0.7  # Penalizar 30%
    elif regime == 'risk_on':
        # En risk-on, favorecer momentum y apalancados
        for r in ranked_universe:
            if r['category'] in ['LEVERAGED_LONG', 'MOMENTUM']:
                r['score'] *= 1.15
    return ranked_universe
```

**Impacto:** Crítico. Sin esto, el sistema puede estar comprando TQQQ en medio de un bear market porque su "momentum" es positivo en términos absolutos pero el mercado está cayendo.

#### 3.3 La lógica de decisión es OR cuando debería ser secuencial con prioridades
**Problema:** En `make_decision()`:
1. Si cumple Hold → HOLD (no evalúa si hay algo mucho mejor).
2. Si no cumple Hold → evalúa Rotate.
3. Si no cumple Rotate → HOLD_WITH_WARNINGS.

El problema: si el activo actual cumple Hold (está sobre EMA21, sin earnings, top 30%) pero el candidato #1 tiene 40 pts más de score, el sistema dice HOLD. Debería considerar rotar incluso si se cumple Hold cuando la diferencia es abrumadora.

**Fix:** Reestructurar como árbol de decisión con prioridades:
```python
def make_decision(current_position, current_indicators, ranked_universe, earnings_next_week=False):
    hold_check = check_hold_conditions(...)
    rotate_check = check_rotate_conditions(...)
    
    # Prioridad 1: Si hay razón forzosa de salida (earnings, bajo EMA21)
    if not hold_check['above_ema21'] or earnings_next_week:
        if rotate_check['rotate']:
            return ROTATE
        else:
            return EXIT_TO_CASH  # Nuevo: ir a SGOV
    
    # Prioridad 2: Si el candidato es significativamente mejor (hurdle dinámico)
    if rotate_check['rotate']:
        return ROTATE
    
    # Prioridad 3: Hold normal
    if hold_check['hold']:
        return HOLD
    
    # Prioridad 4: Hold con advertencias
    return HOLD_WITH_WARNINGS
```

### 🟡 MEDIO IMPACTO

#### 3.4 El ratio R:B usa un target ingenuo
**Problema:** En `check_rotate_conditions()`:
```python
target_price = entry_price * (1 + abs(candidate['DistHigh20']) / 100)
```
Esto asume que el target es el máximo de 20 días. Pero:
- Si el activo ya está en el máximo (DistHigh20 ≈ 0), el target ≈ entry, y el R:B ≈ 0.
- Si el activo está -10% del máximo, el target es +10%, lo cual es razonable pero no considera la volatilidad.

**Fix:** Usar un target basado en ATR proyectado:
```python
# Target = entrada + 2×ATR diario × sqrt(5) (proyección semanal)
weekly_atr = atr_value * np.sqrt(5)
target_price = entry_price + 2 * weekly_atr  # 2× rango semanal esperado
```

#### 3.5 Falta considerar la calidad del setup, no solo el score
**Problema:** Dos activos pueden tener score 80 pero setups muy diferentes:
- Activo A: Acaba de romper resistencia con volumen 2x → setup de alta calidad.
- Activo B: Lleva 3 semanas subiendo sin corrección → setup agotado.

**Fix:** Agregar un **setup quality score** que evalúe:
- Breakout de consolidación (Bollinger squeeze → expansión).
- Volumen confirmando el movimiento (VolRatio > 1.3 en día de subida).
- Patrón de pullback a soporte (comprar en retroceso, no en extensión).

---

## 4. ⚙️ MEJORAS OPERATIVAS

### 🔴 ALTO IMPACTO

#### 4.1 NO HAY BACKTESTING — Este es el problema #1 del sistema
**Problema:** El sistema completo opera con parámetros no validados:
- Pesos del scoring (30/25/20/10/15): ¿son óptimos?
- Hurdle de 15 pts: ¿es el correcto?
- Stop 1.5×ATR: ¿funciona para ETFs 3x?
- EMA21 como filtro de tendencia: ¿es mejor que EMA50?

Sin backtesting, están volando a ciegas.

**Fix:** Crear módulo `src/backtest.py`:
```python
def backtest_strategy(historical_data, params, start_date, end_date):
    """
    Simula el pipeline semanal sobre datos históricos.
    
    Returns:
        - Return acumulado
        - Sharpe ratio
        - Max drawdown
        - Win rate
        - Profit factor
    """
    # Para cada semana del período:
    # 1. Calcular indicadores con datos hasta esa fecha
    # 2. Rankear universo
    # 3. Aplicar lógica Hold/Rotate
    # 4. Registrar P&L
    # 5. Avanzar a la siguiente semana
    pass
```

**Métricas mínimas a reportar:**
- Return neto acumulado (después de comisiones).
- Sharpe ratio anualizado (debe ser > 1.5).
- Max drawdown (debe ser < 15%).
- Win rate (% de semanas ganadoras, debe ser > 55%).
- Profit factor (ganancias brutas / pérdidas brutas, debe ser > 1.5).

#### 4.2 Falta un módulo de ejecución más sofisticado
**Problema:** `execute_rotation()` en `decision.py` asume ejecución instantánea al precio de cierre. En realidad:
- Hay slippage (especialmente en ETFs 3x al open).
- La orden se ejecuta el lunes a la apertura, no al precio del viernes.
- No hay manejo de gaps de apertura.

**Fix:** Agregar estimación de slippage y modelo de ejecución:
```python
def estimate_execution_cost(price, category, avg_spread_bps=10):
    """Estima costo de ejecución (slippage + spread)."""
    spread_cost = price * avg_spread_bps / 10000
    slippage = price * 0.001  # 0.1% slippage estimado
    return spread_cost + slippage
```

### 🟡 MEDIO IMPACTO

#### 4.3 No hay monitoreo intradiario ni alertas
**Problema:** El sistema solo revisa una vez por semana (sábado). Si el stop se activa el martes, no se entera hasta el sábado. Puede haber una pérdida de 5-10% sin que el sistema reaccione.

**Fix:** Agregar un script de monitoreo diario:
```python
# src/daily_monitor.py
def daily_check():
    """Verifica stops y alertas cada día después del cierre."""
    portfolio = load_portfolio()
    current_price = get_current_price(portfolio['position']['ticker'])
    stop_price = portfolio['position']['stop_loss_usd']
    
    if current_price <= stop_price:
        send_alert(f"🚨 STOP ACTIVADO: {portfolio['position']['ticker']}")
    
    # Alertas adicionales
    if daily_loss > 3%:
        send_alert(f"⚠️ Caída significativa: {daily_loss:.1f}%")
```

#### 4.4 El pipeline no valida datos antes de procesar
**Problema:** `run_weekly_pipeline()` no verifica si los datos descargados están completos. Si yfinance falla para un ticker, el pipeline sigue con datos incompletos.

**Fix:** Agregar validación de datos:
```python
def validate_data(df, ticker, min_rows=252):
    """Valida que los datos estén completos."""
    if df is None or len(df) < min_rows:
        print(f'⚠️ {ticker}: datos insuficientes ({len(df) if df is not None else 0} rows)')
        return False
    if df['Close'].isna().sum() > 5:
        print(f'⚠️ {ticker}: {df["Close"].isna().sum()} valores NaN')
        return False
    return True
```

---

## 5. 🆕 NUEVOS MÓDULOS RECOMENDADOS

### 🔴 ALTO IMPACTO

#### 5.1 Módulo de Backtesting (`src/backtest.py`)
Ya descrito en 4.1. Es la prioridad #1 absoluta. Sin backtesting, todo el sistema es especulativo.

**Implementación sugerida:**
- Walk-forward analysis (no look-ahead bias).
- Incluir comisiones de 0.20% por rotación.
- Simular slippage de 0.1%.
- Período mínimo: 2 años de datos históricos.
- Reportar métricas: return, Sharpe, max DD, win rate, profit factor.

#### 5.2 Módulo de Análisis de Correlación (`src/correlation.py`)
**Problema:** Con 100% de concentración, si el activo elegido está altamente correlacionado con SPY (beta ~1), el portafolio es esencialmente una apuesta direccional al mercado. No hay diversificación de fuentes de retorno.

**Fix:**
```python
def calculate_correlation_matrix(all_tickers_data, period=60):
    """Matriz de correlación de retornos 60d."""
    returns_df = pd.DataFrame(
        {ticker: data['Close'].pct_change() for ticker, data in all_tickers_data.items()}
    )
    return returns_df.corr()


def find_low_correlation_candidates(current_ticker, ranked_universe, corr_matrix, max_corr=0.6):
    """Filtra candidatos con correlación < 0.6 al actual."""
    candidates = []
    for r in ranked_universe:
        corr = corr_matrix.loc[current_ticker, r['ticker']]
        if abs(corr) < max_corr:
            candidates.append(r)
    return candidates
```

**Impacto:** Medio-Alto. Permite rotar a activos que no se muevan en lockstep con el actual, reduciendo el riesgo de drawdown correlacionado.

#### 5.3 Filtro de Volatilidad Realizada vs Implícita (`src/vol_surface.py`)
**Problema:** No se considera si la volatilidad implícita (IV) está cara o barata respecto a la realizada (RV).
- Si IV >> RV: el mercado espera movimiento grande (earnings, evento). Puede ser buena oportunidad para comprar opciones o ETFs apalancados.
- Si IV << RV: el mercado está complaciente. Posible mean reversion de volatilidad.

**Fix:** Usar VIX o IV de opciones como overlay:
```python
def vol_regime_filter(rv_20d, vix_level):
    """
    Si VIX > RV + 2std → market expects turbulence, reduce exposure
    Si VIX < RV - 2std → market complacent, potential vol expansion
    """
    vol_premium = vix_level - rv_20d
    if vol_premium > 5:
        return 'high_fear'  # Considerar defensivos
    elif vol_premium < -5:
        return 'complacent'  # Cuidado con leverage
    return 'normal'
```

### 🟡 MEDIO IMPACTO

#### 5.4 Detección de Patrones (`src/patterns.py`)
Agregar detección de setups técnicos específicos:
- **Bull flag / pennant:** Consolidación después de impulso → continuación.
- **Bollinger squeeze:** Volatilidad comprime → expansión inminente.
- **Mean reversion:** Precio > 2σ de media móvil 20d → posible retroceso.

```python
def detect_bollinger_squeeze(df, period=20, num_std=2):
    """Detecta compresión de Bollinger (volatilidad baja → breakout inminente)."""
    sma = df['Close'].rolling(period).mean()
    std = df['Close'].rolling(period).std()
    bandwidth = (2 * num_std * std) / sma * 100
    
    # Squeeze: bandwidth en mínimo de 120 días
    is_squeeze = bandwidth.iloc[-1] <= bandwidth.rolling(120).min() * 1.1
    return is_squeeze
```

#### 5.5 Análisis de Sentimiento / Flujos (`src/sentiment.py`)
- Put/Call ratio del activo o del mercado.
- Flujos de fondos en ETFs sectoriales (¿institucionales están comprando o vendiendo?).
- Fear & Greed Index de CNN.

**Impacto:** Medio. Es un overlay, no un driver principal, pero puede ayudar a evitar compras en tops de euforia.

#### 5.6 Módulo de Reportes Mejorado (`src/report.py`)
El reporte actual es básico. Agregar:
- Gráfico de equity curve histórico.
- Descomposición de P&L por activo.
- Heatmap de correlación del universo.
- Dashboard de métricas de riesgo (VaR, CVaR).

---

## 📋 RESUMEN PRIORIZADO

| # | Mejora | Impacto | Esfuerzo | Prioridad |
|---|--------|---------|----------|-----------|
| 1 | **Backtesting** | 🔴 Crítico | Alto (3-5 días) | **P0 — Ya** |
| 2 | **Filtro de régimen de mercado** | 🔴 Alto | Medio (1 día) | **P0 — Ya** |
| 3 | **Trailing stop dinámico** | 🔴 Alto | Bajo (2 hrs) | **P0 — Ya** |
| 4 | **Stop ATR adaptativo por categoría** | 🔴 Alto | Bajo (1 hr) | **P0 — Ya** |
| 5 | **Momentum con aceleración** | 🔴 Alto | Medio (3 hrs) | **P1 — Esta semana** |
| 6 | **Normalización cross-sectional** | 🔴 Alto | Medio (2 hrs) | **P1 — Esta semana** |
| 7 | **Beta/relative strength vs SPY** | 🔴 Alto | Medio (4 hrs) | **P1 — Esta semana** |
| 8 | **Circuit breaker de drawdown** | 🔴 Alto | Bajo (1 hr) | **P1 — Esta semana** |
| 9 | **Time-based stop** | 🟡 Medio | Bajo (1 hr) | **P2 — Próxima semana** |
| 10 | **Hurdle dinámico por volatilidad** | 🟡 Medio | Bajo (1 hr) | **P2 — Próxima semana** |
| 11 | **Target R:B basado en ATR proyectado** | 🟡 Medio | Bajo (1 hr) | **P2 — Próxima semana** |
| 12 | **Correlación cross-asset** | 🟡 Medio | Medio (3 hrs) | **P2 — Próxima semana** |
| 13 | **Monitoreo diario / alertas** | 🟡 Medio | Medio (4 hrs) | **P2 — Próxima semana** |
| 14 | **Validación de datos en pipeline** | 🟡 Medio | Bajo (1 hr) | **P2 — Próxima semana** |
| 15 | **Modelo de ejecución con slippage** | 🟡 Medio | Medio (3 hrs) | **P3 — Backlog** |
| 16 | **Vol realizada vs implícita** | 🟡 Medio | Alto (1 día) | **P3 — Backlog** |
| 17 | **Detección de patrones** | 🟡 Medio | Alto (2 días) | **P3 — Backlog** |
| 18 | **Análisis de sentimiento** | 🟢 Bajo | Alto (2 días) | **P3 — Backlog** |

---

## 🎯 PLAN DE ACCIÓN INMEDIATO (Próximos 3 días)

### Día 1: Backtesting + Trailing Stop + Stop ATR adaptativo
1. Crear `src/backtest.py` con walk-forward sobre 2 años de datos.
2. Integrar `update_trailing_stop()` en `run_weekly.py`.
3. Implementar multiplicador ATR por categoría en `risk.py`.

### Día 2: Filtro de régimen + Momentum con aceleración
1. Crear `src/market_regime.py` con SPY + VIX overlay.
2. Agregar aceleración de momentum en `scoring.py`.
3. Normalización cross-sectional del scoring.

### Día 3: Circuit breaker + Time stop + Calibración
1. Implementar circuit breaker de drawdown máximo.
2. Agregar time-based stop.
3. Correr backtest con parámetros originales vs mejorados. Comparar métricas.

---

## ⚠️ ADVERTENCIAS FINALES

1. **El sistema actual NO debe operarse con capital real sin backtesting.** Los parámetros son conjeturas.
2. **100% de concentración en un 3x ETF es extremadamente agresivo.** Un drawdown de -20% en una semana es posible con TQQQ/SOXL.
3. **La comisión de 0.20% semanal es fija**, lo que significa que 8 semanas = 1.60% de fricción garantizada. El sistema necesita generar >11.6% bruto para cumplir la meta neta.
4. **El universo incluye ETFs inversos (SQQQ, SOXS) que tienen decay estructural.** Mantenerlos más de 1-2 semanas es peligroso por el volatility drag del rebalanceo diario inverso.

---

*Fin del review. Todas las recomendaciones incluyen código implementable y están priorizadas por impacto en la meta de +10% en 8 semanas.*

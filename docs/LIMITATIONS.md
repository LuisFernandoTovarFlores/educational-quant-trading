# Limitaciones y advertencias

> **Este software es investigación educativa. No es asesoría financiera.**
> No garantiza rendimientos, no ha sido validado con un backtest y puede perder
> capital. No lo uses con dinero real sin validación independiente.

## 1. Falta de validación

- **No hay backtest.** No existe evidencia histórica de que la combinación de
  pesos, hurdle, ATR y filtro de régimen genere alpha.
- **No hay validación out-of-sample.** Los parámetros (30/25/20/10/15, hurdle
  +15, R:B 2:1, cap 12%) son hipótesis de diseño.
- **Riesgo de sobreajuste.** El universo y los umbrales se eligieron a mano
  mirando el comportamiento reciente.
- **Sin benchmark.** No se compara con SPY, QQQ ni una cartera 60/40.

## 2. Costos y ejecución

- **Slippage no modelado:** el precio de ejecución real puede diferir del cierre.
- **Spread, impacto de mercado y comisiones del bróker** no se incluyen; solo la
  comisión configurada.
- **Gap risk:** un stop en reposo no garantiza el precio de salida. Un gap a la
  baja puede ejecutar mucho peor.
- **FX:** el capital puede estar en MXN y los activos en USD; `fx.usd_mxn` es un
  supuesto, no una cobertura.
- **Impuestos:** no se modelan.

## 3. Datos

- **`yfinance` no es un feed oficial.** Puede tener errores, retrasos, splits mal
  ajustados o cambios de API.
- **Datos ajustados vs no ajustados:** el pipeline usa el cierre que entrega
  yfinance; no audita dividendos ni splits.
- **Sin validación cruzada** contra otra fuente.
- **No se redistribuyen datos.** Respeta los términos de Yahoo/yfinance.
- **Calendario de earnings** puede estar incompleto o desactualizado.

## 4. Sesgos del universo

- **Sesgo de selección:** 28 activos elegidos a mano, en su mayoría ganadores
  recientes de liquidez y momentum.
- **Sesgo de supervivencia:** no se incluyen activos que quebraron o salieron
  del índice.
- **Concentración sectorial:** mega-caps tecnológicas y semiconductores dominan.
- **Sesgo de familiaridad:** el universo refleja una tesis, no un muestreo
  sistemático.

## 5. Riesgo de cartera

- **100% en un solo activo:** no hay diversificación; un evento idiosincrático
  puede destruir una parte importante del capital.
- **ETFs 3x:** beta ~3, volatility decay, riesgo de gap y de cierre del fondo.
- **Stop cap del 12%:** en un activo con ATR alto, el sistema puede declararlo
  "no apto" y quedarse sin candidatos.
- **Rotaciones forzadas:** el filtro de régimen puede forzar una venta en un mal
  momento (whipsaw).
- **Sin circuito de drawdown global:** no hay un kill switch de cartera.

## 6. Modelo de régimen y scoring

- **Umbrales discrecionales:** VIX 15/20/25/30, spread 1.0/0/−0.5, DXY ±2% no
  están calibrados.
- **Confianza del régimen** es una normalización simple, no una probabilidad.
- **Régimen `NEUTRAL`** puede bloquear apalancados justo cuando la tendencia es
  favorable.
- **El RSI como "régimen"** es una simplificación; el RSI no mide régimen de
  mercado.
- **Target R:B** usa el máximo de 20 días; en máximos históricos el R:B es 0.
- **Sin correlación/relative strength** contra el mercado.

## 7. Operación

- **No ejecuta órdenes.** No hay integración con bróker.
- **No hay paper trading** ni simulación de fills.
- **No hay alertas** ni monitoreo diario.
- **Ejecución semanal:** no captura oportunidades intradía.
- **Dependencia de un humano** para validar pre-market y colocar stops.

## 8. Legal y regulatorio

- No es una recomendación de inversión personalizada.
- No considera tu situación fiscal, tolerancia al riesgo ni horizonte.
- El uso de datos de mercado puede estar sujeto a términos de terceros.
- Si distribuyes el software, conserva el disclaimer y la licencia MIT.

## 9. Antes de usar dinero real

1. Escribe y ejecuta un backtest walk-forward con comisiones y slippage.
2. Compara contra un benchmark simple.
3. Haz paper trading durante al menos 8–12 semanas.
4. Define un límite de drawdown y un plan de salida.
5. Empieza con una fracción pequeña del capital que puedas perder.
6. Consulta a un profesional licenciado.

## 10. Descargo de responsabilidad

El software se proporciona "tal cual", sin garantía de ningún tipo. Los autores y
contribuidores no son responsables de pérdidas financieras, errores de datos,
interrupciones o daños derivados del uso del proyecto. Ver `LICENSE`.

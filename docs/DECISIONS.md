# Registro de decisiones (ADR)

Decisiones de diseño que no deberían reabrirse sin una razón sólida. Formato
ligero inspirado en Architecture Decision Records.

---

## ADR-001 — Un solo motor de decisión

**Fecha:** 2026-10-22  
**Estado:** Aceptada

**Contexto:** `executive_report.py` duplicaba reglas de HOLD/ROTATE con umbrales
distintos (ATR 1.5, sin filtro de régimen, sin idoneidad).

**Decisión:** `src/decision.py` es la única fuente de verdad. El reporte
ejecutivo construye el ranking con `src/pipeline.py` y llama a `make_decision`.

**Consecuencias:** menos divergencia y tests más simples. El reporte ejecutivo
descarga el universo completo si no recibe un ranking precalculado.

---

## ADR-002 — Configuración como fuente de verdad

**Fecha:** 2026-10-22  
**Estado:** Aceptada

**Contexto:** había pesos, multiplicadores y capital hardcodeados en varios
módulos; cambiar `settings.yaml` no siempre cambiaba el comportamiento.

**Decisión:** los parámetros numéricos viven en `config/settings.yaml` y se leen
con `config.loader.get_config()`. El universo vive en `config/universe.py`.

**Consecuencias:** más legibilidad y reproducibilidad. Los defaults de las
funciones siguen existiendo por compatibilidad, pero deben coincidir con el YAML.

---

## ADR-003 — Historial público limpio

**Fecha:** 2026-10-22  
**Estado:** Aceptada

**Contexto:** el historial privado contiene datos de cartera, rutas personales y
un email universitario en los commits.

**Decisión:** publicar una rama huérfana `public-release` con un único commit
inicial. El repositorio privado se conserva como archivo.

**Consecuencias:** no se puede `git pull` del historial público al privado sin
un merge deliberado. El email de los commits públicos debe ser el noreply de
GitHub.

---

## ADR-004 — Licencia MIT

**Fecha:** 2026-10-22  
**Estado:** Aceptada

**Contexto:** el proyecto no tenía licencia; sin ella no es open source.

**Decisión:** MIT, por simplicidad y máxima adopción. Incluye cláusula de no
garantía.

**Consecuencias:** se permite uso comercial y modificaciones; se debe conservar
el aviso de copyright.

---

## ADR-005 — Documentación bilingüe

**Fecha:** 2026-10-22  
**Estado:** Aceptada

**Contexto:** el equipo trabaja en español, pero el alcance open source es global.

**Decisión:** `README.md` en inglés, `README.es.md` en español; documentación
técnica interna en español. Las traducciones al inglés son bienvenidas.

**Consecuencias:** duplicación de mantenimiento en los README. Mantener ambos
sincronizados es parte del checklist de PR.

---

## ADR-006 — Comisión configurable

**Fecha:** 2026-10-22  
**Estado:** Aceptada

**Contexto:** la documentación decía "semanal" y "por rebalanceo" a la vez; el
código no aplicaba ninguna.

**Decisión:** `costs.commission_pct` + `costs.charge_on` (`weekly` o `rotation`).
En modo `weekly`, `last_fee_week` garantiza una sola cobro por semana ISO.

**Consecuencias:** el pipeline muta `state/portfolio.json` al cobrar la comisión
semanal; se puede desactivar con `--no-commission`.

---

## ADR-007 — Tests offline por defecto

**Fecha:** 2026-10-22  
**Estado:** Aceptada

**Contexto:** 23 tests dependían de yfinance/Finnhub y colgaban el suite sin red.

**Decisión:** los tests de red se marcan con `@pytest.mark.integration` y se
excluyen por defecto en `pyproject.toml`. CI corre solo offline.

**Consecuencias:** la cobertura de red se ejecuta manualmente o en un job
programado. El objetivo es mockearla en v0.5.

---

## ADR-008 — Tokens en cabeceras

**Fecha:** 2026-10-22  
**Estado:** Aceptada

**Contexto:** Finnhub recibía el token en la URL; un error HTTP podía filtrarlo
en logs.

**Decisión:** usar `X-Finnhub-Token` en cabeceras y loggear solo el código HTTP
para Marketaux (cuyo token va en query string).

**Consecuencias:** los logs son seguros por defecto. No imprimir URLs de API en
mensajes de error.

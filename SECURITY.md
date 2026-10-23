# Política de seguridad

## Versiones soportadas

| Versión | Soportada |
| --- | --- |
| 0.1.x | Sí |
| < 0.1 | No |

## Reportar una vulnerabilidad

**No abras un issue público.** Usa el reporte privado de vulnerabilidades de
GitHub:

1. Ve a la pestaña **Security** del repositorio.
2. Pulsa **Report a vulnerability**.
3. Incluye una descripción, pasos para reproducir y el impacto estimado.

Si el reporte privado no está disponible, contacta al propietario del
repositorio por GitHub y evita publicar detalles explotables.

### Qué incluir

- Versión del proyecto y de Python.
- Sistema operativo.
- Descripción del problema y vector de ataque.
- Pasos mínimos para reproducir.
- Impacto (por ejemplo, fuga de API keys, ejecución de código, path traversal).
- Cualquier mitigación sugerida.

### Qué esperar

- Acuse de recibo en un plazo orientativo de 3 días hábiles.
- Evaluación y plan de corrección en un plazo orientativo de 14 días.
- Crédito en el release notes si lo deseas.

## Alcance

Son especialmente relevantes:

- Fuga de claves de API en logs, URLs o reportes.
- Lectura/escritura arbitraria de archivos mediante tickers o rutas.
- Ejecución de código a través de datos de mercado o plantillas Jinja2.
- Dependencias con vulnerabilidades conocidas.
- Exposición de `state/portfolio.json` o `.env`.

## Manejo de secretos

- `.env` está en `.gitignore` y **nunca** debe commitearse.
- `state/portfolio.json`, `data/` y `output/` también están ignorados.
- No pegues claves en issues, PRs ni capturas de pantalla.
- Si una clave se expone, **revócala y regénerala**; borrar el commit no es
  suficiente.
- El proyecto envía el token de Finnhub en cabecera (`X-Finnhub-Token`) y evita
  imprimir URLs de Marketaux con token.

## Buenas prácticas para usuarios

- Ejecuta el proyecto en un entorno virtual.
- Revisa los cambios antes de ejecutar código de terceros.
- No uses capital real sin backtesting y paper trading.
- Mantén las dependencias actualizadas (Dependabot está configurado).

## Divulgación

Coordinaremos contigo la fecha de divulgación pública. Pedimos un plazo
razonable para publicar una corrección antes de hacer públicos los detalles.

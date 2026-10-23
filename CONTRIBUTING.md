# Contribuir

¡Gracias por tu interés! Este proyecto es un framework de investigación; las
contribuciones de código, tests, documentación y revisión son bienvenidas.

Al participar, aceptas el [Código de Conducta](CODE_OF_CONDUCT.md).

---

## 1. Configuración del entorno

```bash
git clone https://github.com/LuisFernandoTovarFlores/educational-quant-trading.git
cd educational-quant-trading

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install

cp examples/portfolio.example.json state/portfolio.json
```

No necesitas claves de API para los tests offline.

---

## 2. Flujo de trabajo

1. Abre un issue o una discusión antes de cambios grandes.
2. Crea una rama desde `main`:
   ```bash
   git checkout -b feat/nombre-corto
   ```
3. Haz cambios pequeños y enfocados.
4. Añade o actualiza tests.
5. Ejecuta:
   ```bash
   python -m pytest -q
   ruff check .
   ruff format .
   ```
6. Actualiza `CHANGELOG.md` si el cambio es visible.
7. Abre un PR con la plantilla.

Usamos mensajes de commit tipo [Conventional Commits](https://www.conventionalcommits.org/):

```text
feat(scoring): add relative strength factor
fix(decision): scan all candidates before giving up
docs(readme): clarify commission modes
test(report): cover TQQQ stop multiplier
```

---

## 3. Estructura y convenciones

- **Configuración antes que código:** los parámetros numéricos van en
  `config/settings.yaml`, no hardcodeados.
- **Rutas:** usa `src/paths.py`; nunca rutas absolutas.
- **Motor de decisión:** `src/decision.py` es la única fuente de verdad.
  `executive_report.py` debe reutilizarlo.
- **Errores:** captura excepciones concretas; no uses `except:` desnudo.
- **Red:** los tests que descargan datos o llaman APIs deben marcarse con
  `@pytest.mark.integration`.
- **Secretos:** nunca commitees `.env`, claves ni `state/portfolio.json`.
- **Datos personales:** usa `examples/portfolio.example.json` y cifras ficticias.
- **Docstrings:** en español o inglés, pero claros y con tipos cuando aporten.
- **Formato:** `ruff format` (línea de 100 caracteres).

---

## 4. Tests

```bash
# Suite offline (la que corre CI)
python -m pytest -q

# Tests de integración (requieren internet)
python -m pytest -q -m integration

# Cobertura
python -m pytest --cov=src --cov=config --cov-report=term-missing
```

Un PR debe incluir tests para la lógica nueva o modificada. Si el cambio es
puramente documental, no es necesario.

---

## 5. Áreas donde ayudar

- **Backtesting:** walk-forward, comisiones, slippage y benchmark.
- **Tests:** mockear yfinance/HTTP para eliminar la dependencia de red.
- **Documentación:** traducir `docs/` al inglés, mejorar ejemplos.
- **Datos:** validación de splits, dividendos y calidad de datos.
- **Riesgo:** circuit breaker de drawdown, sizing por volatilidad.
- **Accesibilidad:** mensajes de error más claros, salida JSON.

Busca issues con `good first issue` o `help wanted`.

---

## 6. Checklist de PR

- [ ] El cambio está enfocado y explicado.
- [ ] `python -m pytest -q` pasa.
- [ ] `ruff check .` pasa.
- [ ] Añadí tests para la lógica nueva.
- [ ] No incluí secretos, datos reales ni rutas absolutas.
- [ ] Actualicé documentación/CHANGELOG si aplica.
- [ ] Respeté el Código de Conducta.

---

## 7. Reportar bugs

Abre un issue con la plantilla de bug. Incluye:

- Versión de Python y del proyecto.
- Sistema operativo.
- Pasos para reproducir.
- Salida/log **sin claves ni datos reales**.
- Qué esperabas y qué ocurrió.

Para vulnerabilidades, **no abras un issue público**: ver [SECURITY.md](SECURITY.md).

---

## 8. Licencia de las contribuciones

Al enviar un PR aceptas que tu contribución se publique bajo la licencia MIT del
proyecto.

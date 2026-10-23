# Publicación en GitHub

Checklist para publicar el proyecto con un historial limpio. La rama
`public-release` se crea como **huérfana** (un solo commit, sin el historial
privado). El repositorio privado se conserva como archivo.

> **Importante:** el historial privado contiene datos de cartera y un email
> personal en los commits. No publiques `main` directamente.

---

## 1. Verificación previa

Desde la raíz del repo:

```bash
# 1. Que no haya secretos ni datos de cartera en el árbol
git status --short
git ls-files | grep -Ei '\.env$|portfolio\.json|data/|output/'

# 2. Que no haya claves reales en la rama pública
git grep -nE 'FINNHUB_API_KEY=[A-Za-z0-9]{20,}|MARKETAUX_API_KEY=[A-Za-z0-9]{20,}|FRED_API_KEY=[a-f0-9]{32}' public-release || true

# 3. Que no haya rutas personales
git grep -nE '/Users/|/home/|C:\\\\' public-release || true

# 4. Tests offline
python -m pytest -q
```

Debe devolver vacío en los greps y todos los tests en verde.

---

## 2. Crear el repositorio público

> Si publicas bajo otro usuario u otro nombre de repo, actualiza las URLs en
> `README.md`, `README.es.md`, `pyproject.toml` y `.github/ISSUE_TEMPLATE/config.yml`.

**Opción recomendada: repositorio nuevo.** Conserva el privado como archivo y
evita reescribir la historia del remoto.

1. Crea un repo vacío en GitHub, por ejemplo `educational-quant-trading`.
2. No inicialices con README, licencia ni `.gitignore`.
3. Anota la URL: `https://github.com/<usuario>/<repo>.git`.

**Opción alternativa: reutilizar el repo existente.** Solo si aceptas que el
historial privado desaparezca del remoto (force-push). Haz un bundle antes:

```bash
git bundle create ../educational-quant-trading-private.bundle --all
```

---

## 3. Publicar la rama huérfana

Si la rama `public-release` ya existe:

```bash
# Verifica que estás en la rama y que tiene un solo commit
git checkout public-release
git log --oneline

# Añade el remoto público (si es un repo nuevo)
git remote add public https://github.com/<usuario>/<repo>.git

# Publica como main
git push public public-release:main
```

Si aún no existe, créala desde el árbol actual:

```bash
git checkout --orphan public-release
git add -A
git -c user.name="Luis Fernando Tovar Flores" \
    -c user.email="LuisFernandoTovarFlores@users.noreply.github.com" \
    commit -m "Initial public release v0.1.0"
```

Verifica que el commit no incluya `state/`, `data/`, `output/` ni `.env`:

```bash
git show --stat --oneline HEAD
git ls-tree -r --name-only HEAD | grep -Ei '\.env$|portfolio\.json|data/|output/'
```

---

## 4. Configuración del repositorio en GitHub

- [ ] Descripción: "Rules-based quantitative swing-trading research framework
      for liquid US equities and ETFs (educational, not financial advice)."
- [ ] Topics: `quantitative-finance`, `swing-trading`, `algorithmic-trading`,
      `technical-analysis`, `python`, `backtesting`, `yfinance`.
- [ ] Licencia visible: MIT.
- [ ] Web: URL de la documentación (si existe).
- [ ] Activar **Issues** y **Discussions**.
- [ ] Desactivar **Wiki** si no se usa.
- [ ] Activar **Secret scanning** y **Push protection**.
- [ ] Activar **Dependabot alerts** y **security updates**.
- [ ] Activar **Private vulnerability reporting**.
- [ ] Proteger `main`: PR obligatorio, CI en verde, revisión.
- [ ] Añadir release `v0.1.0` con notas de `CHANGELOG.md`.
- [ ] Social preview (imagen 1280×640) opcional.

---

## 5. Claves de API

Aunque `.env` nunca se commiteó, rota las claves si existía alguna posibilidad
de exposición:

1. Revoca y regenera en Finnhub, Marketaux y FRED.
2. Actualiza tu `.env` local.
3. No pegues claves en issues, PRs ni logs.

---

## 6. Verificación posterior

```bash
git clone https://github.com/<usuario>/<repo>.git /tmp/educational-quant-trading-public
cd /tmp/educational-quant-trading-public
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp examples/portfolio.example.json state/portfolio.json
python -m pytest -q
python -m src.run_weekly --help
```

Comprueba en GitHub:

- El README renderiza badges y Mermaid.
- `LICENSE` aparece como MIT.
- CI está en verde.
- No hay archivos de datos ni cartera.
- El historial tiene un solo commit (o los commits que decidas).

---

## 7. Archivar el repositorio privado

En GitHub: **Settings → General → Danger Zone → Archive this repository**.
Conserva el bundle local:

```bash
git bundle create ../educational-quant-trading-private.bundle --all
```

---

## 8. Si algo sale mal

- **Se publicó un secreto:** revócalo inmediatamente, no solo lo borres del
  commit. GitHub conserva objetos en caché.
- **Se publicó una rama equivocada:** elimina la rama en el remoto y fuerza el
  push correcto; rota claves si aplica.
- **El CI falla:** revisa el log del workflow; los tests offline no necesitan
  red.

# Proyecto: Noticias de Portabilidad Móvil con EDA + RAG + LLM

Genera **noticias breves, estilo institucional (OSIPTEL)** a partir de:

1) **EDA local** en Python sobre el Excel de portabilidad (Punku).
2) **RAG** con un mini-corpus de noticias históricas (2024–2025) indexadas en Qdrant.
3) **LLM** vía **GitHub Models** (chat completions) para redactar la narrativa.
4) **HTML estático** con **Chart.js + Tailwind** para visualizar (barras mensuales, tabla por operador y, si aplica, línea del **neto por operador**).

> Todas las **cifras** se calculan localmente (EDA). El LLM **no** calcula datos; solo redacta y organiza el ángulo de la nota con apoyo de RAG.

---

## Problemática que resuelve

**Problema**
- Cada mes se publican notas de portabilidad móvil. Producirlas manualmente implica: limpiar y agregar datos, calcular KPIs (MoM/YoY y neto por operador), decidir el ángulo (mensual/trimestral/semestral/anual), redactar con tono consistente y maquetar gráficos/tablas.
- Riesgos: errores de cifras, variaciones de estilo entre autores, baja trazabilidad, y uso ingenuo de LLM que puede **alucinar** números si no se controla. Además, mandar “todo” al modelo encarece en **tokens**.

**Solución**
- Un pipeline reproducible **EDA → RAG → LLM → HTML** con responsabilidades claras:
  - **EDA (determinístico)** en Python: todas las cifras y agregados se calculan localmente.
  - **RAG** (Qdrant + embeddings): aporta tono/estructura institucional recuperando párrafos de notas históricas (enero del año previo, mes previo, cierres).
  - **LLM** (GitHub Models): solo **redacta** y organiza; devuelve JSON estructurado. No toca el cálculo ni el JS/CSS.
  - **HTML estático**: plantilla controlada (Tailwind + Chart.js). La UI siempre respeta el mismo estándar.
  - **Evaluación**: similitud TF‑IDF con la nota oficial y verificación de números (toda cifra del texto debe existir en el EDA).
- **Eficiencia de tokens**: se envía un **EDA mínimo** (últimos 16 meses + tabla del mes + comparativas) y snippets RAG **truncados**.

**Beneficios**
- Consistencia y ahorro de tiempo en redacción y maquetación.
- Cifras confiables (cero alucinaciones numéricas) y trazabilidad completa.
- Coste controlado de LLM (prompt acotado) y fácil auditoría.
- Extensible a otros dominios de EDA con el mismo esqueleto.

**Alcance**
- Entrada: Excel Punku (8.1 Portabilidad), corpus 2024–2025.
- Salida: noticia HTML con gráfico(s) y tabla, estilo institucional en español.
- Reglas de corte: **Mensual**.
- Fuera de alcance: scraping automático continuo, predicción/forecast, integración CMS.

**Usuarios objetivo**
- Analistas de telecom/reguladores, comunicaciones corporativas, consultores, periodismo de datos.

**Métricas de éxito sugeridas**
- Desviación de cifras vs EDA: **0**.
- Tokens totales por nota: **≤ 2k** (objetivo) con EDA mínimo + RAG truncado.
- Similitud TF‑IDF con la nota oficial del mismo periodo: **≥ 0.4** (ajustable por equipo).

---

## Características

- **EDA reproducible**:
  - Serie mensual total.
  - Variaciones **MoM/YoY**.
  - **Neto por operador** (ganadas – perdidas) por mes y su serie temporal.
  - Cortes **trimestral (mar/sep)**, **semestral (jun)** y **anual (dic)**.
- **RAG period-aware**:
  - Para cada mes objetivo, recupera:
    - **Mismo mes del año previo** (p. ej., ene-2024 para ene-2025).
    - **Mes previo** (p. ej., dic-2024 para ene-2025).
    - **Cierre** (anual/semestral) si aplica.
- **Redacción con LLM** (REST "chat completions") devolviendo **JSON estructurado** `{title, subhead, bullets[], paragraph, flags}`.
- **Plantilla HTML determinística**: el LLM solo aporta texto; **tabla** y **gráficos** se construyen con datos del **EDA** (evita alucinaciones).
- **Comparador** con la nota oficial: similitud **TF-IDF** y verificación de **números** (toda cifra del texto debe existir en el EDA JSON).

---

## Estructura del repositorio

```
llm-news/
├─ run_news.py                 # Orquestación: EDA → RAG → LLM → HTML (+comparación opcional)
├─ build_page.py               # Render estático (Tailwind CDN + Chart.js)
├─ eda/
│  └─ portabilidad.py          # EDA y reglas de layout (mensual/trimestral/semestral/anual)
├─ rag/
│  ├─ __init__.py
│  ├─ qdrant_init.py           # Colección local (Qdrant en disco o server)
│  ├─ embed_client.py          # /inference/embeddings en GitHub Models
│  ├─ ingest_osiptel.py        # URLs → Markdown (MarkItDown) → chunks → embeddings → Qdrant
│  ├─ read_links.py            # Cargador de data/raw_links.csv
│  └─ retrieve.py              # retrieve() y retrieve_for_month() (period-aware)
├─ writer/
│  ├─ __init__.py
│  └─ generate_news.py         # LLM (chat completions) con response_format=json
├─ eval/
│  └─ compare_official.py      # TF-IDF cosine + verificador de números
├─ data/
│  ├─ raw_links.csv            # URLs (2024–2025) con date=YYYY-MM-01
│  └─ eda/                     # eda_YYYY-MM.json (salidas EDA)
└─ logs/                       # (opcional) uso de tokens / costes
```

---

## Tecnologías

- **GitHub Models**: REST `chat/completions` y `embeddings`.
- **Embeddings**: `cohere/Cohere-embed-v3-multilingual` (vector de 1024 dims, multilingüe).
- **Qdrant**: base vectorial (`size=1024`, `distance=Cosine`) en **modo path local** o **servidor**.
- **MarkItDown**: HTML → Markdown (para ingesta de prensa OSIPTEL).
- **Chart.js** (CDN) + **Tailwind Play CDN** para el HTML estático.
- **pandas**: series temporales y `resample` con frecuencias nuevas (`QE-DEC`, `2QE-DEC`, `YE-DEC`).

---

## Requisitos

```
pip install -r requirements.txt
```

**requirements.txt** sugerido:

```
pandas
python-dotenv
requests
qdrant-client
markitdown[all]
scikit-learn
```

---

## Configuración

Crea un archivo `.env` en la raíz:

```env
GITHUB_TOKEN=tu_pat_con_models_read
MODEL_ID=openai/gpt-4.1
EMBEDDING_MODEL=cohere/Cohere-embed-v3-multilingual
# QDRANT_URL=http://localhost:6333      # opcional: servidor
QDRANT_LOCAL_PATH=./qdrant_data          # persistencia local
```

> El PAT **fine-grained** debe incluir permiso **Models: read**.

---

## Datos de entrada

- **Excel Punku**: `8.1. PORTABILIDAD MÓVIL.xlsx` (hoja `Dataset`), con columnas originales transformadas a: `Cedente, Receptor, Mod_Cedente, Mod_Receptor, Mes, Lineas`.
- **Corpus OSIPTEL**: `data/raw_links.csv` con cabeceras: `period,date,url`.
  
Ejemplo de primera fila:
```csv
period,date,url
ene_2024,2024-01-01,https://www.osiptel.gob.pe/portal-del-usuario/noticias/.../enero-de-2024/
```

---

## Flujo de trabajo (end-to-end)

1) **Ingesta RAG** (URLs → Markdown → chunks → embeddings → Qdrant):
   ```bash
   python -m rag.ingest_osiptel
   ```

2) **EDA + Noticia + HTML (y comparación opcional)**:
   ```bash
   python run_news.py --excel "8.1. PORTABILIDAD MÓVIL.xlsx" --target-month 2025-01-01 --compare
   ```
   - `eda/portabilidad.py` genera `data/eda/eda_2025-01.json` con:
     - mensual (líneas, MoM, YoY),
     - tabla **ganadas/perdidas/neto** (operadoras principales),
     - series de **neto por operador**,
     - reglas de **layout**: mar/sep (trimestral), jun (semestral), dic (anual), y recomendación de **gráfico de neto** (p. ej., ene-2025).
   - `rag/retrieve.py` usa `retrieve_for_month()` para traer párrafos ancla (mismo mes año previo, mes previo y/o cierre).
   - `writer/generate_news.py` llama al LLM y obtiene un **JSON de narrativa**.
   - `build_page.py` arma el **HTML** final (barras últimos 16 meses, tabla neto del mes, y opcionalmente línea de neto por operador).
   - `eval/compare_official.py` calcula **TF-IDF** con la nota oficial y valida que cada número del texto esté en el EDA.

---

## Detalles de implementación

### EDA (resumen)
- **Agregación mensual** con `to_period('M') → to_timestamp()`.
- **MoM** y **YoY**: `pct_change()` con `periods=1` y `12`.
- **Rollups**:
  - Trimestral: `resample('QE-DEC')`.
  - Semestral: `resample('2QE-DEC')`.
  - Anual: `resample('YE-DEC')`.
- **Neto por operador**: pivot `Mes × Empresa` con columnas `[CLARO, ENTEL, BITEL, MOVISTAR]`.
- **Recomendación de gráfico** (boolean): muestra la línea de neto si hay **pico** (|neto| alto) o si el mes es **enero**.

### RAG (retrieve)
- `retrieve(query,k,max_chars)` para vector search genérico con truncado de texto.
- `retrieve_for_month(target_month)` para contexto **period-aware**:
  - `YYYY-01-01`: añade cierre **anual** del año previo.
  - Si no hay coincidencia exacta por `date`, fallback a vector search por texto.
  - Devuelve 2–4 trozos **recortados** (para ahorrar tokens).

### LLM (generate_news)
- Endpoint: `POST /inference/chat/completions`.
- `response_format={"type":"json_object"}` para forzar estructura.
- Prompt envía un **EDA mínimo**: `chart_last16`, `operators_current`, `comparatives`, `layout`, `recommendations` (no envía arrays largos innecesarios).
- Control de tokens: `max_tokens` moderado y contexto RAG truncado.

### HTML (build_page)
- **Tailwind Play CDN** + **Chart.js CDN**.
- Gráfico de **barras** (últimos 16 meses) + **tabla** del mes objetivo.
- **Línea** de neto por operador **opcional** según `flags`/`recommendations`.
- Formateo numérico en navegador: `Intl.NumberFormat('es-PE')`.

---

## Comandos rápidos

```bash
# 1) Ingerir/actualizar corpus RAG
python -m rag.ingest_osiptel

# 2) Generar noticia (enero 2025) y comparar con la oficial
python run_news.py --excel "8.1. PORTABILIDAD MÓVIL.xlsx" --target-month 2025-01-01 --compare

# 3) Abrir el HTML generado
open reports/noticia_portabilidad_2025-01.html
```

---

## Extensiones futuras

- **UI** (Streamlit): subir Excel → EDA → titulares → exportar HTML.
- **Streaming** del LLM con `include_usage` para medir tokens en tiempo real.
- **Costeo** por request (logs y reporte mensual).
- **Más dominios**: reusar el pipeline con otros EDA (esquema JSON común).


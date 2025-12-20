# build_page.py
import json, pandas as pd
from pathlib import Path

MESES_ABR = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
MESES_FULL = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

def mes_abr(ts: pd.Timestamp) -> str:
    return f"{MESES_ABR[ts.month-1]}’{str(ts.year)[2:]}"

def mes_full(ts: pd.Timestamp) -> str:
    return f"{MESES_FULL[ts.month-1]} {ts.year}"

def range_title_from_labels(label_dates: list[str]) -> str:
    """Recibe fechas 'YYYY-MM-DD' o ya strings tipo '2025-01-01'; devuelve 'Oct’23 a Ene’25'."""
    dts = [pd.to_datetime(x) for x in label_dates]
    return f"{mes_abr(min(dts))} a {mes_abr(max(dts))}"

def last_n_months_from_monthly_total(eda, n: int):
    series = sorted(eda["monthly_total"], key=lambda x: x["period"])
    n = max(6, min(int(n), 24))  # 6..24 meses
    series = series[-n:]
    labels_dates = [s["period"] for s in series]                    # para el título
    labels = [pd.to_datetime(s["period"]).strftime("%b-%y").title() for s in series]
    values = [int(s["lines"]) for s in series]
    return labels, values, labels_dates

def last_12m_neto_timeseries(eda):
    latest = pd.to_datetime(eda["latest_period"])
    cut = latest - pd.DateOffset(months=11)
    idx = pd.to_datetime(eda["neto_timeseries"]["index"])
    mask = idx >= cut
    out = {
        "index": [d.strftime("%b-%y").title() for d in idx[mask]],
        "index_dates": [d.strftime("%Y-%m-%d") for d in idx[mask]]  # para título
    }
    for op in ("CLARO","ENTEL","BITEL","MOVISTAR"):
        arr = pd.Series(eda["neto_timeseries"][op], index=idx)
        out[op] = [int(x) for x in arr[mask].tolist()]
    return out

def render_html(eda:dict, narrative:dict):
    # 1) Barras: ventana sugerida por el LLM (capada a 24)
    bar_n = narrative.get("flags", {}).get("bar_months", 16)
    bar_labels, bar_values, bar_label_dates = last_n_months_from_monthly_total(eda, bar_n)
    bar_title_range = range_title_from_labels(bar_label_dates)
    #bar_labels_js = json.dumps(bar_labels, ensure_ascii=False)
    #bar_values_js = json.dumps(bar_values)

    # 2) Neto por operadora: SIEMPRE últimos 12 meses si hay datos suficientes
    neto12 = last_12m_neto_timeseries(eda)
    show_neto = len(neto12["index"]) >= 2  # dibuja si hay ≥2 puntos
    neto_title_range = range_title_from_labels(neto12["index_dates"])

    # 3) Título para la tabla (mes objetivo en español)
    latest = pd.to_datetime(eda["latest_period"])
    table_title = f"Resultado neto — {mes_full(latest)}"

    # 4) Filas de la tabla (ya solo último mes)
    ops_rows = "".join([
        f"<tr><td class='font-semibold'>{op['name']}</td>"
        f"<td>{op['won']:,}</td><td>{op['lost']:,}</td>"
        f"<td class='{'text-green-700' if op['net']>=0 else 'text-red-600'} font-semibold'>{op['net']:,}</td></tr>"
        for op in eda["operators_current"]
    ])

    # 5) Bloque opcional del neto (12m)
    neto_block = ""
    if show_neto:
        neto_block = f"""
        <div class="col-span-12 card mt-6">
          <h3 class="font-semibold mb-2">Resultado neto por operadora ({neto_title_range})</h3>
          <div class="h-80"><canvas id="netoChart"></canvas></div>
          <p class="text-sm text-gray-500 mt-2"><small>Fuente: PUNKU-OSIPTEL (fecha de corte: {mes_full(latest)})</small></p>
        </div>
        """
    bar_labels_js = json.dumps(bar_labels, ensure_ascii=False)
    bar_values_js = json.dumps(bar_values)
    neto_idx_js   = json.dumps(neto12["index"], ensure_ascii=False)
    neto_ds_js    = json.dumps({
        "CLARO":   neto12.get("CLARO", []),
        "ENTEL":   neto12.get("ENTEL", []),
        "BITEL":   neto12.get("BITEL", []),
        "MOVISTAR":neto12.get("MOVISTAR", []),
        })

    # 6) HTML (solo cambio los títulos h3)
    return f"""<!doctype html>
<html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{narrative['title']}</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>.slide{{width:1280px;min-height:720px;margin:0 auto}}.card{{border:1px solid #e5e7eb;border-radius:14px;padding:20px}}</style>
</head><body class="text-gray-900">
<div class="slide">
  <div class="bg-gray-800 text-white p-6">
    <h1 class="text-2xl font-bold">{narrative['title']}</h1>
    <p class="opacity-80">{narrative['subhead']}</p>
  </div>

  <div class="grid grid-cols-12 gap-6 p-6">
    <div class="col-span-7 card">
      <h3 class="font-semibold mb-2">Evolución de líneas móviles portadas ({bar_title_range})</h3>
      <div class="h-80"><canvas id="barChart"></canvas></div>
      <p class="text-sm text-gray-500 mt-2"><small>Fuente: PUNKU-OSIPTEL (fecha de corte: {mes_full(latest)})</small></p>
    </div>

    <div class="col-span-5 card">
      <ul class="list-disc pl-5 mb-3">
        {"".join([f"<li>{b}</li>" for b in narrative.get('bullets',[])])}
      </ul>
      <p>{narrative['paragraph']}</p>
    </div>

    <div class="col-span-12 card">
      <h3 class="font-semibold mb-2">{table_title}</h3>
      <div class="overflow-x-auto"><table class="min-w-full text-center">
        <thead><tr class="bg-gray-100"><th>Operadora</th><th>Ganadas</th><th>Perdidas</th><th>Neto</th></tr></thead>
        <tbody>{ops_rows}</tbody></table></div>
    </div>

    {neto_block}
  </div>
</div>

<script>
  window.addEventListener('DOMContentLoaded', () => {{
    const nf = new Intl.NumberFormat('es-PE');

    // --- BARRAS (ventana reciente, <=24m) ---
    const labels = {bar_labels_js};
    const values = {bar_values_js};
    const ctxBar = document.getElementById('barChart');
    if (ctxBar) {{
      new Chart(ctxBar.getContext('2d'), {{
        type:'bar',
        data:{{ labels, datasets:[{{ label:'Líneas portadas', data:values, borderWidth:0, backgroundColor:'#0076CE', barThickness:36 }}]}},
        options:{{
          responsive:true, maintainAspectRatio:false,
          plugins:{{ legend:{{display:false}}, tooltip:{{ callbacks:{{ label:(c)=> nf.format(c.parsed.y)+' líneas' }} }} }},
          scales:{{ y:{{ beginAtZero:true, ticks:{{ callback:(v)=> nf.format(v) }} }}, x:{{ grid:{{ display:false }} }} }}
        }}
      }});
    }}

    // --- NETO (últimos 12m) ---
    const idx = {neto_idx_js};
    const ds  = {neto_ds_js};
    const ctxNeto = document.getElementById('netoChart');
    if (ctxNeto && idx.length >= 2) {{
      new Chart(ctxNeto.getContext('2d'), {{
        type:'line',
        data:{{ labels: idx, datasets:[
          {{label:'CLARO', data: ds.CLARO, borderWidth:2}},
          {{label:'ENTEL', data: ds.ENTEL, borderWidth:2}},
          {{label:'BITEL', data: ds.BITEL, borderWidth:2}},
          {{label:'MOVISTAR', data: ds.MOVISTAR, borderWidth:2}},
        ]}},
        options:{{ responsive:true, maintainAspectRatio:false }}
      }});
    }}
  }});
</script>
</body></html>"""

def write_page(eda_path, narrative, outdir="reports"):
    eda = json.loads(Path(eda_path).read_text(encoding="utf-8"))
    html = render_html(eda, narrative)
    Path(outdir).mkdir(exist_ok=True, parents=True)
    out = Path(outdir)/f"noticia_portabilidad_{eda['latest_period'][:7]}.html"
    out.write_text(html, encoding="utf-8")
    return out
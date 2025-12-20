# eda/portabilidad.py
import pandas as pd, json
from pathlib import Path

BRAND_MAP = {
  "América Móvil Perú S.A.C.": "CLARO",
  "Entel Perú S.A.": "ENTEL",
  "Viettel Perú S.A.C.": "BITEL",
  "Telefónica del Perú S.A.A.": "MOVISTAR",
}
OPERADORAS = ["CLARO","ENTEL","BITEL","MOVISTAR"]
MES_ABR = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

def month_label(ts): return f"{MES_ABR[ts.month-1]}-{str(ts.year)[2:]}"

def load_excel(path:str):
    df = pd.read_excel(path, sheet_name="Dataset", header=3, usecols="B:G", parse_dates=["Mes"])
    df.columns = ["Cedente","Receptor","Mod_Cedente","Mod_Receptor","Mes","Lineas"]
    df["Cedente_b"]  = df["Cedente"].map(BRAND_MAP).fillna(df["Cedente"])
    df["Receptor_b"] = df["Receptor"].map(BRAND_MAP).fillna(df["Receptor"])
    return df

def compute_monthly(df):
    return (df.groupby(df["Mes"].dt.to_period("M"))["Lineas"]
              .sum().to_timestamp().sort_index())

def compute_neto_por_operador(df):
    g = (df.groupby([df["Mes"].dt.to_period("M").dt.to_timestamp(), "Receptor_b"])["Lineas"]
           .sum().reset_index().rename(columns={"Lineas":"Ganadas","Receptor_b":"Empresa"}))
    p = (df.groupby([df["Mes"].dt.to_period("M").dt.to_timestamp(), "Cedente_b"])["Lineas"]
           .sum().reset_index().rename(columns={"Lineas":"Perdidas","Cedente_b":"Empresa"}))
    neto = pd.merge(g, p, on=["Mes","Empresa"], how="outer").fillna(0.0)
    neto["Neto"] = neto["Ganadas"] - neto["Perdidas"]
    piv = neto.pivot_table(index="Mes", columns="Empresa", values="Neto", aggfunc="sum").fillna(0.0)
    for e in OPERADORAS:
        if e not in piv.columns: piv[e]=0.0
    return piv[OPERADORAS].sort_index()

def rollups(monthly):
    df = monthly.to_frame("lines").sort_index()
    df["mom"] = df["lines"].pct_change()
    df["yoy"] = df["lines"].pct_change(12)
    # trimestral / semestral / anual (suma de líneas portadas)
    q = df["lines"].resample("QE-DEC").sum().to_frame("lines_q")
    h = df["lines"].resample("2QE-DEC").sum().to_frame("lines_h")
    y = df["lines"].resample("YE-DEC").sum().to_frame("lines_y")
    return df, q, h, y

def recommend_layout(target):
    m = target.month
    if m in (3, 9):  return "trimestral"
    if m == 6:       return "semestral"
    if m == 12:      return "anual"
    return "mensual"

def recommend_neto_chart(neto_piv, target):
    # muestra el gráfico de neto si el mes tiene señal fuerte (pico en abs)
    row = neto_piv.loc[target]
    return bool((row.abs().max() >= 10000) or (target.month == 1))

def build_eda(path_excel:str, target_month:str|None=None, outdir="data/eda"):
    df = load_excel(path_excel)
    monthly = compute_monthly(df)
    target = pd.Timestamp(target_month) if target_month else monthly.index.max()

    neto_piv = compute_neto_por_operador(df)
    # Tabla mensual (ganadas/perdidas/neto)
    g_mes = (df[df["Mes"]==target].groupby("Receptor_b")["Lineas"].sum())
    p_mes = (df[df["Mes"]==target].groupby("Cedente_b")["Lineas"].sum())
    tabla = []
    for op in OPERADORAS:
        won  = int(g_mes.reindex([op]).fillna(0).iloc[0])
        lost = int(p_mes.reindex([op]).fillna(0).iloc[0])
        tabla.append({"name":op,"won":won,"lost":lost,"net":won-lost})

    # rollups
    df_roll, q, h, y = rollups(monthly)

    eda = {
      "topic":"portabilidad_movil_peru",
      "latest_period": str(target.date()),
      "layout": recommend_layout(target),
      "comparatives":{
        "mom_delta_pct": float(df_roll.loc[target,"mom"]) if target in df_roll.index else None,
        "yoy_delta_pct": float(df_roll.loc[target,"yoy"]) if target in df_roll.index else None
      },
      "monthly_total":[{"period":str(ts.date()),"lines":int(v)} for ts,v in monthly.items()],
      "chart_last16":{
        "labels":[month_label(ts) for ts in monthly.tail(16).index],
        "values":[int(v) for v in monthly.tail(16).values]
      },
      "operators_current": tabla,
      "neto_timeseries":{
        "index":[str(ts.date()) for ts in neto_piv.index],
        "CLARO":   [int(x) for x in neto_piv["CLARO"].tolist()],
        "ENTEL":   [int(x) for x in neto_piv["ENTEL"].tolist()],
        "BITEL":   [int(x) for x in neto_piv["BITEL"].tolist()],
        "MOVISTAR":[int(x) for x in neto_piv["MOVISTAR"].tolist()],
      },
      "recommendations":{
        "include_neto_timeseries": recommend_neto_chart(neto_piv, target)
      }
    }
    Path(outdir).mkdir(parents=True, exist_ok=True)
    yyyymm = target.strftime("%Y-%m")
    out = Path(outdir)/f"eda_{yyyymm}.json"
    out.write_text(json.dumps(eda, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
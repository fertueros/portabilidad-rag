# writer/generate_news.py
import os, json, requests
from dotenv import load_dotenv
from rag.retrieve import retrieve
load_dotenv()

BASE="https://models.github.ai"
HEADERS={
  "Accept":"application/vnd.github+json",
  "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
  "X-GitHub-Api-Version":"2022-11-28",
  "Content-Type":"application/json",
}
MODEL=os.getenv("MODEL_ID","openai/gpt-4.1")

def _minify_eda(eda: dict) -> dict:
    # Solo lo necesario para redactar
    keep = {
        "topic": eda.get("topic"),
        "latest_period": eda.get("latest_period"),
        "layout": eda.get("layout"),
        "comparatives": eda.get("comparatives"),
        "chart_last16": eda.get("chart_last16"),            # 16 puntos máx.
        "operators_current": eda.get("operators_current"),  # tabla del mes
        "recommendations": eda.get("recommendations"),
    }
    return keep

def generate_narrative(eda_json:dict, k=4):
    # Query según layout
    layout = eda_json["layout"]
    query = "portabilidad Perú " + {"mensual":"reporte mensual",
                                    "trimestral":"cierre trimestral",
                                    "semestral":"cierre semestral",
                                    "anual":"balance anual"}[layout]
    ctx = retrieve(query=query, k=k, period_type=None)  # puedes filtrar
    mini = _minify_eda(eda_json)

    system = (
      "Actúa como editor institucional (tono OSIPTEL). "
      "Usa SOLO las cifras del EDA; los contextos sirven para estilo y enfoque. "
      "Devuelve JSON con: {title, subhead, bullets[2..4], paragraph, angle, flags:{use_neto_chart:boolean}}."
      "flags:{use_neto_chart:boolean, bar_months?:number}}. "
      "Si sugieres 'bar_months', que sea entre 12 y 24."
    )
    user = {
      "eda_json": mini,
      "retrieved_snippets": ctx
    }
    body = {
      "model": MODEL,
      "response_format": {"type":"json_object"},
      "temperature": 0.4,
      "messages":[
        {"role":"system","content":system},
        {"role":"user","content": json.dumps(user, ensure_ascii=False)}
      ]
    }
    r = requests.post(f"{BASE}/inference/chat/completions", headers=HEADERS, json=body, timeout=90)
    r.raise_for_status()

    # LOG DE TOKENS (usa las variables correctas: body y r)
    try:
        from utils.usage_logger import log_from_response
        tag = f"news:{eda_json.get('latest_period','')[:7] or 'na'}"
        info = log_from_response(model=body["model"], resp=r, tag=tag)
        print(f"[TOKENS] in={info['prompt_tokens']} out={info['completion_tokens']} total={info['total_tokens']}")
        print(f"[RATE] remaining={info['ratelimit_remaining']} reset={info['ratelimit_reset']}")
    except Exception as e:
        # Fallback opcional de estimación local si quieres:
        try:
            from utils.usage_logger import approx_tokens
            approx = approx_tokens(body["messages"])
            print(f"[TOKENS≈] prompt_est={approx} (no usage exacto) | motivo: {e}")
        except Exception:
            pass

    # Parseo del contenido JSON devuelto por el modelo
    raw = r.json()
    content = raw["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except Exception as e:
        # Fallback por si el modelo devuelve texto con comillas simples o un JSON no estricto
        print("[WARN] No se pudo parsear JSON estricto; devolviendo estructura mínima.", e)
        return {
            "title": "Portabilidad móvil — Resumen ejecutivo",
            "subhead": "Síntesis del periodo analizado",
            "bullets": ["Nivel de portaciones consistente.", "Variación mensual y anual dentro de rangos esperados."],
            "paragraph": content,  # deja el texto crudo para no perderlo
            "angle": "resumen",
            "flags": {"use_neto_chart": bool(eda_json.get("recommendations", {}).get("include_neto_timeseries", False))},
        }
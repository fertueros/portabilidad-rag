# rag/retrieve.py
import os, datetime as dt
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, ScoredPoint
from .embed_client import embed

def _client():
    local_path = os.getenv("QDRANT_LOCAL_PATH")
    url = os.getenv("QDRANT_URL")
    if local_path:
        return QdrantClient(path=local_path)   # persistente en disco
    elif url:
        return QdrantClient(url=url)           # servidor remoto/local
    return QdrantClient(":memory:")            # pruebas

def retrieve(query: str, k: int = 3, collection: str = "osiptel_news",
             period_type: str | None = None, max_chars: int = 600):
    """Devuelve [{'text':..., 'url':...}, ...] desde Qdrant."""
    client = _client()
    vec = embed([query])[0]  # 1024-dim con Cohere v3 multilingual
    flt = None
    if period_type:
        flt = Filter(must=[FieldCondition(key="period_type", match=MatchValue(value=period_type))])
    hits: list[ScoredPoint] = client.search(collection_name=collection,
                                            query_vector=vec, limit=k, query_filter=flt)
    out = []
    for h in hits:
        txt = (h.payload.get("text", "") or "")[:max_chars]
        out.append({"text": txt, "url": h.payload.get("url", ""), "date": h.payload.get("date","")})
    return out

def _get_by_date(date_iso: str, k: int = 4, collection: str = "osiptel_news", max_chars: int = 600):
    """Trae chunks cuyo payload.date == date_iso (exacto)."""
    client = _client()
    flt = Filter(must=[FieldCondition(key="date", match=MatchValue(value=date_iso))])
    # Usamos scroll para traer varios puntos; podemos limitar manualmente
    points, _ = client.scroll(collection_name=collection, scroll_filter=flt, limit=k)
    out = []
    for p in points:
        txt = (p.payload.get("text", "") or "")[:max_chars]
        out.append({"text": txt, "url": p.payload.get("url", ""), "date": p.payload.get("date","")})
    return out

def retrieve_for_month(target_month: str, collection: str = "osiptel_news"):
    """
    target_month: 'YYYY-MM-01'
    Devuelve contexto: mismo mes año previo, mes previo y (si corresponde) cierre anual anterior.
    """
    t = dt.date.fromisoformat(target_month)
    same_month_prev = t.replace(year=t.year - 1)
    # mes previo: cuidado con enero
    prev_month = (t.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
    ctx = []

    # 1) mismo mes del año previo (ej. 2024-01-01)
    ctx += _get_by_date(same_month_prev.isoformat())

    # 2) mes previo (ej. 2024-12-01)
    ctx += _get_by_date(prev_month.isoformat())

    # 3) cierre anual del año previo (si existe en corpus): para enero, suele ser útil
    if t.month == 1:
        # muchas notas anuales se publican a inicios de enero siguiente, pero puedes
        # haber guardado 'date' como 'YYYY-12-01' para tu corpus; si no, haz vector fallback:
        annual_vec = retrieve(query=f"portabilidad 2024 balance anual", k=1, collection=collection)

        # si tienes guardado un link anual 2024 (p. ej. “6.3 millones en 2024”):
        # añade manualmente _get_by_date("2024-12-01") si tu CSV lo usa así.

        ctx += annual_vec

    # Fallbacks si falta algo: usa vector search mensual
    if not ctx:
        ctx = retrieve(query=f"portabilidad reporte mensual {t.strftime('%B %Y')}", k=3, collection=collection)

    # Quitar duplicados por URL
    seen, dedup = set(), []
    for c in ctx:
        if c["url"] in seen: continue
        seen.add(c["url"]); dedup.append(c)
    # Limitar a 3–4 trozos
    return dedup[:4]
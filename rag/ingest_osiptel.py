# rag/ingest_osiptel.py
import uuid, requests, datetime as dt
from io import BytesIO
from markitdown import MarkItDown
from qdrant_client.models import PointStruct
from .embed_client import embed
from .qdrant_init import ensure_collection
from .read_links import read_csv  # o read_txt

def html_to_md(url:str)->str:
    html=requests.get(url,timeout=60).content
    md=MarkItDown().convert_stream(BytesIO(html), extension=".html")
    return md.text_content

def chunk(md:str, min_len=400, max_len=900):
    parts=[]; cur=[]
    tot=0
    paras=[p.strip() for p in md.split("\n\n") if p.strip()]
    for p in paras:
        if tot+len(p) <= max_len:
            cur.append(p); tot+=len(p)
        else:
            if cur: parts.append("\n\n".join(cur))
            cur=[p]; tot=len(p)
    if cur: parts.append("\n\n".join(cur))
    # juntar los demasiado cortos
    merged=[]; buf=""
    for p in parts:
        if len(p)<min_len and buf:
            buf=buf+"\n\n"+p
            merged.append(buf); buf=""
        elif len(p)<min_len:
            buf=p
        else:
            if buf: merged.append(buf); buf=""
            merged.append(p)
    if buf: merged.append(buf)
    return merged

def ingest(collection="osiptel_news"):
    c=ensure_collection(collection, dim=1024)
    items=read_csv("data/raw_links.csv")  # o read_txt(...)
    points=[]
    for it in items:
        md=html_to_md(it.url)
        chunks=chunk(md)
        vecs=embed(chunks)
        today=dt.date.today().isoformat()
        for text,v in zip(chunks,vecs):
            points.append(PointStruct(
                id=uuid.uuid4().hex,
                vector=v,
                payload={
                    "text":text, "url":it.url,
                    "date":it.date, "period":it.period,
                    "period_type":"mensual", "indexed_at":today
                }
            ))
    c.upsert(collection_name=collection, points=points)
    print("ingresados:", len(points))

if __name__=="__main__":
    ingest()

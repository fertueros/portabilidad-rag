# run_news.py
import json, argparse
from eda.portabilidad import build_eda
from writer.generate_news import generate_narrative
from build_page import write_page
from eval.compare_official import fetch_markdown, tfidf_cosine, check_numbers

URLS_OFICIALES = {
  "2025-01": "https://www.osiptel.gob.pe/portal-del-usuario/noticias/portabilidad-de-lineas-moviles-pospago-registra-record-historico-en-enero/",
  "2025-02": "https://www.osiptel.gob.pe/portal-del-usuario/noticias/alrededor-de-600-mil-lineas-moviles-cambiaron-de-empresa-operadora-en-febrero-de-2025/",
}

ap = argparse.ArgumentParser()
ap.add_argument("--excel", required=True)
ap.add_argument("--target-month", required=True)  # ej: 2025-01-01
ap.add_argument("--compare", action="store_true")
args = ap.parse_args()

eda_path = build_eda(args.excel, args.target_month)     # -> data/eda/eda_YYYY-MM.json
narr = generate_narrative(json.loads(open(eda_path,"r",encoding="utf-8").read()))
out_html = write_page(eda_path, narr)
print("✅ HTML:", out_html)

if args.compare:
    key = args.target_month[:7]
    if key in URLS_OFICIALES:
        official = fetch_markdown(URLS_OFICIALES[key])
        mine = "\n".join([narr["title"], narr["subhead"], *narr["bullets"], narr["paragraph"]])
        sim = tfidf_cosine(mine, official)
        eda = json.loads(open(eda_path,"r",encoding="utf-8").read())
        misses = check_numbers(mine, eda)
        print(f"🔎 similitud TF-IDF con OSIPTEL {key}: {sim:.3f}")
        print("🔢 números fuera del EDA:", misses or "OK")
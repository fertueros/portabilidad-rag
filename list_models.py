import os, sys, json, argparse, time, requests
from dotenv import load_dotenv

CATALOG_URL = "https://models.github.ai/catalog/models"
INFER_USER_URL = "https://models.github.ai/inference/chat/completions"
INFER_ORG_URL_TMPL = "https://models.github.ai/orgs/{org}/inference/chat/completions"

def gh_headers(token: str) -> dict:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

def fetch_catalog(token: str):
    r = requests.get(CATALOG_URL, headers=gh_headers(token), timeout=60)
    if r.status_code != 200:
        raise SystemExit(f"[catalog] Error {r.status_code}: {r.text}")
    return r.json()  # list of models (see GitHub Docs for schema)

def model_matches(m: dict, multilingual_only: bool, publisher: str | None, contains: str | None):
    # Basic filters
    if multilingual_only:
        tags = [t.lower() for t in m.get("tags", [])]
        if "multilingual" not in tags:
            return False
    if publisher:
        if m.get("publisher", "").lower() != publisher.lower():
            return False
    if contains:
        hay = (m.get("id","") + " " + m.get("name","") + " " + m.get("summary","")).lower()
        if contains.lower() not in hay:
            return False

    # Must support text in/out
    in_ok  = "text" in [x.lower() for x in m.get("supported_input_modalities", [])]
    out_ok = "text" in [x.lower() for x in m.get("supported_output_modalities", [])]
    return in_ok and out_ok

def probe_inference(token: str, model_id: str, org: str | None):
    """
    Optional minimal call to check if you have access to the model.
    Returns tuple: (ok: bool, note: str, ratelimit: dict)
    """
    url = INFER_ORG_URL_TMPL.format(org=org) if org else INFER_USER_URL
    headers = gh_headers(token) | {"Content-Type": "application/json"}
    body = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": "Responde SIEMPRE en español."},
            {"role": "user", "content": "Ok?"}
        ],
        "max_tokens": 1,
        "temperature": 0.0,
    }
    r = requests.post(url, headers=headers, json=body, timeout=60)
    rl = {
        "remaining": r.headers.get("x-ratelimit-remaining"),
        "reset": r.headers.get("x-ratelimit-reset"),
        "retry_after": r.headers.get("retry-after"),
    }
    if r.status_code == 200:
        return True, "ok", rl
    try:
        err = r.json()
    except Exception:
        err = {"error": r.text[:200]}
    # Common: 403 (no access / rate limit), 422 (modalidad no soportada)
    msg = err.get("error") or err
    return False, f"{r.status_code}: {msg}", rl

def main():
    load_dotenv()
    token = os.getenv("GITHUB_TOKEN")
    org   = os.getenv("GITHUB_ORG")  # opcional

    if not token:
        print("Falta GITHUB_TOKEN en .env", file=sys.stderr)
        sys.exit(1)

    ap = argparse.ArgumentParser(description="Lista modelos de GitHub Models filtrados para español y texto.")
    ap.add_argument("--all", action="store_true", help="No filtrar por 'multilingual'.")
    ap.add_argument("--publisher", help="Filtra por publisher exacto (OpenAI, DeepSeek, azureml-meta, etc.)")
    ap.add_argument("--contains", help="Filtra si el texto aparece en id/nombre/summary.")
    ap.add_argument("--probe", action="store_true", help="Prueba acceso real (mini inference) a los primeros N modelos.")
    ap.add_argument("--probe-limit", type=int, default=8, help="Cuántos modelos probar si --probe (default 8).")
    ap.add_argument("--sleep", type=float, default=0.6, help="Pausa entre probes para cuidar rate limit.")
    ap.add_argument("--json", action="store_true", help="Salida JSON en lugar de tabla.")
    args = ap.parse_args()

    try:
        catalog = fetch_catalog(token)
    except SystemExit as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    multilingual_only = not args.all
    filtered = [
        m for m in catalog
        if model_matches(m, multilingual_only, args.publisher, args.contains)
    ]

    # Ordena por publisher, luego id
    filtered.sort(key=lambda m: (m.get("publisher",""), m.get("id","")))

    # Si piden probe, probamos hasta N modelos
    probe_results = {}
    if args.probe:
        to_probe = filtered[: max(0, args.probe_limit)]
        for m in to_probe:
            ok, note, rl = probe_inference(token, m["id"], org)
            probe_results[m["id"]] = {"ok": ok, "note": note, "ratelimit": rl}
            time.sleep(max(0.0, args.sleep))

    if args.json:
        out = []
        for m in filtered:
            mi = {
                "id": m.get("id"),
                "name": m.get("name"),
                "publisher": m.get("publisher"),
                "tags": m.get("tags", []),
                "input_modalities": m.get("supported_input_modalities", []),
                "output_modalities": m.get("supported_output_modalities", []),
                "rate_limit_tier": m.get("rate_limit_tier"),
            }
            if args.probe and m["id"] in probe_results:
                mi["probe"] = probe_results[m["id"]]
            out.append(mi)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    # Salida tipo tabla simple
    if not filtered:
        print("No se encontraron modelos con esos filtros.")
        return

    # Ancho dinámico
    w_id = max(len("MODEL ID"), max(len(m.get("id","")) for m in filtered))
    w_pub = max(len("PUBLISHER"), max(len(m.get("publisher","")) for m in filtered))
    w_tags = 22
    w_mod  = 20

    print(f"{'MODEL ID'.ljust(w_id)}  {'PUBLISHER'.ljust(w_pub)}  {'IN/OUT'.ljust(w_mod)}  {'TAGS'.ljust(w_tags)}  PROBE")
    print("-"*(w_id+w_pub+w_mod+w_tags+10))
    for m in filtered:
        in_mod  = ",".join(m.get("supported_input_modalities", []))
        out_mod = ",".join(m.get("supported_output_modalities", []))
        tags    = ",".join(m.get("tags", []))[:w_tags]
        pid     = m.get("id","")
        probe   = ""
        if args.probe and pid in probe_results:
            pr = probe_results[pid]
            probe = "OK" if pr["ok"] else pr["note"]
        print(f"{pid.ljust(w_id)}  {m.get('publisher','').ljust(w_pub)}  {(in_mod+'→'+out_mod)[:w_mod].ljust(w_mod)}  {tags.ljust(w_tags)}  {probe}")

if __name__ == "__main__":
    main()
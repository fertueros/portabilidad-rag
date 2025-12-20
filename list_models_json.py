# list_models_json.py
import os, sys, json, time, argparse, requests
from dotenv import load_dotenv

CATALOG_URL = "https://models.github.ai/catalog/models"
INFER_USER_URL = "https://models.github.ai/inference/chat/completions"
INFER_ORG_URL_TMPL = "https://models.github.ai/orgs/{org}/inference/chat/completions"

# ---------- utils ----------
def gh_headers(token: str) -> dict:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }

def fetch_catalog(token: str):
    r = requests.get(CATALOG_URL, headers=gh_headers(token), timeout=60)
    if r.status_code != 200:
        raise SystemExit(f"[catalog] Error {r.status_code}: {r.text[:500]}")
    return r.json()

def model_matches(m: dict, multilingual_only: bool, publisher: str | None, contains: str | None):
    if multilingual_only:
        tags = [t.lower() for t in m.get("tags", [])]
        if "multilingual" not in tags:
            return False
    if publisher and m.get("publisher", "").lower() != publisher.lower():
        return False
    if contains:
        hay = (m.get("id","") + " " + m.get("name","") + " " + m.get("summary","")).lower()
        if contains.lower() not in hay:
            return False
    # Debe soportar texto en entrada/salida (el JSON mode sigue siendo salida "text" pero estructurada)
    in_ok  = "text" in [x.lower() for x in m.get("supported_input_modalities", [])]
    out_ok = "text" in [x.lower() for x in m.get("supported_output_modalities", [])]
    return in_ok and out_ok

def _post(url: str, headers: dict, body: dict):
    r = requests.post(url, headers=headers, json=body, timeout=60)
    rl = {
        "remaining": r.headers.get("x-ratelimit-remaining"),
        "reset": r.headers.get("x-ratelimit-reset"),
        "retry_after": r.headers.get("retry-after"),
    }
    # Si 200, intentamos parsear el JSON del body de la respuesta del servicio
    err_json = None
    if r.status_code != 200:
        try:
            err_json = r.json()
        except Exception:
            err_json = {"error": r.text[:300]}
    return r, rl, err_json

def probe_json_mode_strict(token: str, model_id: str, org: str | None):
    """
    Estricto: exige 200 + JSON válido + finish_reason != 'length'.
    Devuelve dict con ok, note, finish_reason, ratelimit.
    """
    url = INFER_ORG_URL_TMPL.format(org=org) if org else INFER_USER_URL
    headers = gh_headers(token)
    body = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": "Devuelve SOLO el JSON exactamente {\"pong\":\"ok\"}."},
            {"role": "user", "content": "ping"}
        ],
        "max_tokens": 64,             # margen para evitar truncado
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
        "modalities": ["text"]
    }
    r, rl, err = _post(url, headers, body)
    if r.status_code != 200:
        msg = (err.get("error") if isinstance(err, dict) else err) or r.text
        return {"ok": False, "note": f"{r.status_code}: {str(msg)[:200]}", "finish_reason": None, "ratelimit": rl}

    try:
        data = r.json()
        choice = (data.get("choices") or [{}])[0]
        content = ((choice.get("message") or {}).get("content") or "").strip()
        finish = choice.get("finish_reason")
        # Debe ser JSON válido
        parsed = json.loads(content)
        if isinstance(parsed, dict) and parsed.get("pong") == "ok" and finish != "length":
            return {"ok": True, "note": "ok", "finish_reason": finish, "ratelimit": rl}
        # Si es JSON válido pero finish=length, lo tratamos como NO (evita falsos positivos)
        return {"ok": False, "note": f"finish_reason={finish}", "finish_reason": finish, "ratelimit": rl}
    except Exception as ex:
        # No parseó como JSON
        # Si viene truncado, normalmente finish_reason será "length"
        try:
            finish = r.json().get("choices", [{}])[0].get("finish_reason")
        except Exception:
            finish = None
        return {"ok": False, "note": f"non-JSON/truncated (finish_reason={finish})", "finish_reason": finish, "ratelimit": rl}

# ---------- CLI ----------
def main():
    load_dotenv()
    token = os.getenv("GITHUB_TOKEN")
    org   = os.getenv("GITHUB_ORG")  # opcional

    if not token:
        print("Falta GITHUB_TOKEN en .env", file=sys.stderr)
        sys.exit(1)

    ap = argparse.ArgumentParser(
        description="Lista SOLO modelos que aceptan JSON mode estrictamente (200 + JSON válido), mostrando límites de tokens."
    )
    ap.add_argument("--all", action="store_true", help="No filtrar por tag 'multilingual'.")
    ap.add_argument("--publisher", help="Filtra por publisher exacto (OpenAI, DeepSeek, azureml-meta, etc.)")
    ap.add_argument("--contains", help="Texto a buscar en id/nombre/summary.")
    ap.add_argument("--limit", type=int, default=40, help="Cuántos modelos probar como máximo (default 40).")
    ap.add_argument("--sleep", type=float, default=0.6, help="Pausa entre probes para cuidar rate limit.")
    ap.add_argument("--json", action="store_true", help="Salida JSON en lugar de tabla.")
    ap.add_argument("--why", action="store_true", help="Muestra también los descartados con el motivo.")
    ap.add_argument("--plan",choices=["free", "pro", "business", "enterprise"],
    default="free",
    help="Plan para calcular topes efectivos de tokens (por request).")
    ap.add_argument("--min-effective-out",type=int,default=None,
    help="Filtra modelos cuya salida efectiva permitida sea menor a este valor.")
    args = ap.parse_args()

    try:
        catalog = fetch_catalog(token)
    except SystemExit as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    multilingual_only = not args.all
    candidates = [m for m in catalog if model_matches(m, multilingual_only, args.publisher, args.contains)]
    candidates.sort(key=lambda m: (m.get("publisher",""), m.get("id","")))

    if not candidates:
        print("No hay modelos candidatos con esos filtros.")
        return

    to_probe = candidates[: max(0, args.limit)]
    results = {}
    for m in to_probe:
        pr = probe_json_mode_strict(token, m["id"], org)
        results[m["id"]] = pr
        time.sleep(max(0.0, args.sleep))

    # Topes efectivos por plan y tier (tokens por request)
    PLAN_CAPS = {
        "free":      {"low": (8000, 4000), "high": (8000, 4000)},
        "pro":       {"low": (8000, 4000), "high": (8000, 4000)},
        "business":  {"low": (8000, 4000), "high": (8000, 4000)},
        "enterprise":{"low": (8000, 8000), "high": (16000, 8000)},
    }

    def effective_caps(model_dict, plan):
        tier = (model_dict.get("rate_limit_tier") or "").lower()
        plan_caps = PLAN_CAPS.get(plan, {})
        in_cap_plan, out_cap_plan = plan_caps.get(tier, plan_caps.get("low", (8000, 4000)))
        lim = model_dict.get("limits") or {}
        max_in  = lim.get("max_input_tokens")
        max_out = lim.get("max_output_tokens")
        eff_in  = min(in_cap_plan,  max_in)  if isinstance(max_in,  int) else in_cap_plan
        eff_out = min(out_cap_plan, max_out) if isinstance(max_out, int) else out_cap_plan
        return eff_in, eff_out
    
    # Aplica filtro estricto JSON + (opcional) filtro por salida efectiva
    json_ok, json_no = [], []
    for m in to_probe:
        pr = results.get(m["id"], {})
        if not pr.get("ok"):
            json_no.append(m)
            continue
        eff_in, eff_out = effective_caps(m, args.plan)
        m["_eff_in"], m["_eff_out"] = eff_in, eff_out
        if args.min_effective_out is not None and eff_out < args.min_effective_out:
            json_no.append(m)
        else:
            json_ok.append(m)

    #json_ok = [m for m in to_probe if results.get(m["id"], {}).get("ok")]
    json_no = [m for m in to_probe if not results.get(m["id"], {}).get("ok")]

    if args.json:
        out = []
        for m in json_ok:
            pr = results[m["id"]]
            limits = m.get("limits") or {}
            out.append({
                "id": m.get("id"),
                "name": m.get("name"),
                "publisher": m.get("publisher"),
                "html_url": m.get("html_url"),
                "limits": {
                    "max_input_tokens": limits.get("max_input_tokens"),
                    "max_output_tokens": limits.get("max_output_tokens"),
                },
                "supports_json_mode": True,
                "env_model_id": m.get("id"),
                "probe": pr,
                "rate_limit_tier": m.get("rate_limit_tier"),
                "effective_caps": {"plan": args.plan, "in": m.get("_eff_in"), "out": m.get("_eff_out")},
            })
        if args.why:
            out_no = []
            for m in json_no:
                pr = results[m["id"]]
                out_no.append({
                    "id": m.get("id"),
                    "publisher": m.get("publisher"),
                    "reason": pr.get("note"),
                    "finish_reason": pr.get("finish_reason"),
                })
            print(json.dumps({"ok": out, "discarded": out_no}, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    if not json_ok:
        print("No se encontraron modelos con soporte JSON mode (estricto) en los primeros", len(to_probe), "probados.")
        if args.why and json_no:
            print("\nDESCARTADOS (motivo):")
            for m in json_no:
                pr = results[m["id"]]
                print(f"- {m['id']}: {pr.get('note')}")
        return

    # Tabla
    w_id  = max(len("MODEL ID"), max(len(m.get("id","")) for m in json_ok))
    w_pub = max(len("PUBLISHER"), max(len(m.get("publisher","")) for m in json_ok))
    w_in  = max(len("MAX_IN"), 7)
    w_out = max(len("MAX_OUT"), 8)
    w_env = max(len("ENV_HINT"), max(len("MODEL_ID="+m.get("id","")) for m in json_ok))
    w_ein  = max(len("EFF_IN"), 6)
    w_eout = max(len("EFF_OUT"), 7)

    hdr = (
        f"{'MODEL ID'.ljust(w_id)}  "
        f"{'PUBLISHER'.ljust(w_pub)}  "
        f"{'MAX_IN'.rjust(w_in)}  "
        f"{'MAX_OUT'.rjust(w_out)}  "
        f"{'EFF_IN'.rjust(w_ein)}  "
        f"{'EFF_OUT'.rjust(w_eout)}  "
        f"{'JSON'}  "
        f"{'ENV_HINT'.ljust(w_env)}"
    )
    print(hdr)
    print("-"*len(hdr))
    for m in json_ok:
        limits = m.get("limits") or {}
        max_in = str(limits.get("max_input_tokens") or "-")
        max_out = str(limits.get("max_output_tokens") or "-")
        eff_in  = str(m.get("_eff_in") or "-")
        eff_out = str(m.get("_eff_out") or "-")
        env_hint = "MODEL_ID=" + m.get("id","")
        print(
            f"{m.get('id','').ljust(w_id)}  "
            f"{m.get('publisher','').ljust(w_pub)}  "
            f"{max_in.rjust(w_in)}  "
            f"{max_out.rjust(w_out)}  "
            f"{eff_in.rjust(w_ein)}  "
            f"{eff_out.rjust(w_eout)}  "
            f"{'OK'}  "
            f"{env_hint.ljust(w_env)}"
        )

    if args.why and json_no:
        print("\nDESCARTADOS (motivo):")
        for m in json_no:
            pr = results[m["id"]]
            print(f"- {m['id']}: {pr.get('note')}")
            # Ej.: 'non-JSON/truncated (finish_reason=length)' o '422: ...'
if __name__ == "__main__":
    main()

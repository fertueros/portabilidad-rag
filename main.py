import os, sys, json, requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("GITHUB_TOKEN")
MODEL = os.getenv("MODEL_ID", "openai/gpt-4o-mini")  # prueba con uno muy disponible
URL   = "https://models.github.ai/inference/chat/completions"

if not TOKEN:
    print("Falta GITHUB_TOKEN en .env", file=sys.stderr); sys.exit(1)

headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28",
    "Content-Type": "application/json",
}

body = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "Responde SIEMPRE en español."},
        {"role": "user", "content": "Dame 2 consejos para escribir buenos prompts."}
    ],
    "temperature": 0.7
}

resp = requests.post(URL, headers=headers, json=body, timeout=60)

def dump_debug(r):
    print(f"\nStatus: {r.status_code}")
    print("x-ratelimit-remaining:", r.headers.get("x-ratelimit-remaining"))
    print("x-ratelimit-reset    :", r.headers.get("x-ratelimit-reset"))
    print("Body:")
    try:
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception:
        print(r.text)

try:
    resp.raise_for_status()
except requests.HTTPError:
    dump_debug(resp)
    # Sugerencias rápidas según el mensaje del servidor:
    # - Si ves "unknown_model": revisa el ID exacto en /catalog/models.
    # - Si ves "no access"/"permission denied": revisa scope models:read y políticas del org.
    # - Si remaining == 0: espera al reset indicado y reintenta.
    sys.exit(1)

data = resp.json()
print(data["choices"][0]["message"]["content"])
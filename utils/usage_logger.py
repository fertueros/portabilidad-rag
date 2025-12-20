# utils/usage_logger.py
from __future__ import annotations
import csv, os, time
from pathlib import Path

LOG_PATH = Path("logs/llm_usage.csv")

def ensure_log():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_PATH.exists():
        with LOG_PATH.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ts","model","tag","prompt_tokens","completion_tokens","total_tokens",
                        "x_request_id","ratelimit_remaining","ratelimit_reset"])

def log_from_response(model: str, resp, tag: str = ""):
    """resp es el objeto Requests Response de /inference/chat/completions (no streaming)."""
    ensure_log()
    js = resp.json()
    usage = js.get("usage", {}) or {}
    with LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            int(time.time()),
            model,
            tag,
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            usage.get("total_tokens"),
            resp.headers.get("x-request-id"),
            resp.headers.get("x-ratelimit-remaining"),
            resp.headers.get("x-ratelimit-reset"),
        ])
    # también devolver un dict útil para imprimir en consola
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "x_request_id": resp.headers.get("x-request-id"),
        "ratelimit_remaining": resp.headers.get("x-ratelimit-remaining"),
        "ratelimit_reset": resp.headers.get("x-ratelimit-reset"),
    }

# === Extra: estimación local si algún proveedor no devuelve `usage`
def approx_tokens(messages: list[dict], encoding_name: str = "o200k_base") -> int:
    """
    Estima tokens del prompt con tiktoken. Útil como fallback.
    - o200k_base es el codificador moderno (gpt-4o/4.1/…)
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding(encoding_name)
        # conteo simple: sumamos solo `content`; es aproximado.
        text = "\n".join(m.get("content","") for m in messages if "content" in m)
        return len(enc.encode(text))
    except Exception:
        return -1

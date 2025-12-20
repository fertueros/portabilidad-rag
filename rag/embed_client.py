import os, requests
from dotenv import load_dotenv
load_dotenv()

BASE="https://models.github.ai"
HEADERS={
  "Accept": "application/vnd.github+json",
  "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
  "X-GitHub-Api-Version":"2022-11-28",
  "Content-Type":"application/json",
}
MODEL=os.getenv("EMBEDDING_MODEL","cohere/Cohere-embed-v3-multilingual")

def embed(texts:list[str])->list[list[float]]:
    r=requests.post(f"{BASE}/inference/embeddings",
        headers=HEADERS, json={"model":MODEL,"input":texts}, timeout=60)
    r.raise_for_status()
    return [row["embedding"] for row in r.json()["data"]]

if __name__=="__main__":
    vec=embed(["hola mundo"])
    print("dim:",len(vec[0]))  # ~1024 con Cohere v3 multi
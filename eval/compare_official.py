# eval/compare_official.py
import re, requests
from io import BytesIO
from markitdown import MarkItDown
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def fetch_markdown(url:str)->str:
    html = requests.get(url, timeout=60).content
    return MarkItDown().convert_stream(BytesIO(html), extension=".html").text_content

def tfidf_cosine(a:str, b:str)->float:
    v = TfidfVectorizer().fit_transform([a, b])
    return float(cosine_similarity(v[0], v[1])[0,0])

def check_numbers(generated_text:str, eda_json:dict):
    eda_str = str(eda_json)
    nums = re.findall(r"\d[\d\s\.]*\d", generated_text)
    misses = [n for n in nums if n.replace(" ","").replace(".","") not in eda_str.replace(" ","").replace(".","")]
    return misses
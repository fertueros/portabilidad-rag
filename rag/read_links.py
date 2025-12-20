import csv, re
from pathlib import Path
from dataclasses import dataclass

@dataclass
class LinkItem:
    date: str   # "YYYY-MM-01"
    period: str # "ene_2024" (opcional)
    url: str

def read_csv(path="data/raw_links.csv"):
    out=[]
    with open(path,newline="",encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.append(LinkItem(date=row["date"], period=row["period"], url=row["url"]))
    return out
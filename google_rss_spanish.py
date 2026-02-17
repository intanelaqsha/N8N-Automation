import feedparser
from datetime import datetime, timedelta
import time
import urllib.parse
import difflib
import csv

# -------- LATAM REGIONS --------
REGIONS = {
    "colombia": {"hl": "es", "gl": "CO", "ceid": "CO:es"},
    "peru": {"hl": "es", "gl": "PE", "ceid": "PE:es"},
    "honduras": {"hl": "es", "gl": "HN", "ceid": "HN:es"},
    "guatemala": {"hl": "es", "gl": "GT", "ceid": "GT:es"},
    "ecuador": {"hl": "es", "gl": "EC", "ceid": "EC:es"}
}

RSS = "https://news.google.com/rss/search?q={query}&hl={hl}&gl={gl}&ceid={ceid}"

# -------- COMPANIES --------
COMPANIES = {
    "Dinant": ["Dinant", "Corporación Dinant"],
    "Ocho Sur": ["Ocho Sur"],
    "Poligrow": ["Poligrow"],
    "Daabon": ["Grupo Daabon"],
    "Palmas del Espino": ["Palmas del Espino", "Grupo Romero"]
}

# -------- NGOs --------
NGOS = [
    "Mongabay Latam",
    "InfoAmazonia",
    "Global Witness",
    "Earthsight",
    "Greenpeace",
    "Dejusticia"
]

# -------- ISSUES --------
ISSUES = [
    "deforestación",
    "corrupción",
    "conflicto",
    "derechos humanos",
    "comunidades indígenas",
    "incendios",
    "contaminación"
]

PALM_TERMS = [
    "aceite de palma",
    "palma aceitera"
]

DAYS_LIMIT = 30
PAUSE = 1

# -------- FUNCTIONS --------

def build_url(query, cfg):
    q = urllib.parse.quote_plus(query)
    return RSS.format(query=q, **cfg)

def is_recent(entry):
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
        return pub_date >= datetime.now() - timedelta(days=DAYS_LIMIT)
    return False

def similarity(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

def deduplicate(items):
    unique = []
    urls = set()

    for it in items:
        if it["url"] in urls:
            continue

        dup = False
        for u in unique:
            if similarity(it["title"], u["title"]) > 0.85:
                dup = True
                break

        if not dup:
            unique.append(it)
            urls.add(it["url"])

    return unique

# -------- QUERY BUILDER --------

def generate_queries():
    queries = []

    for palm in PALM_TERMS:
        for issue in ISSUES:
            queries.append(f"{palm} {issue}")

            for ngo in NGOS:
                queries.append(f"{palm} {issue} {ngo}")

    for company, aliases in COMPANIES.items():
        alias_part = " OR ".join([f'"{a}"' for a in aliases])

        for issue in ISSUES:
            queries.append(f"({alias_part}) {issue} aceite de palma")

    return queries

# -------- MAIN --------

def main():
    queries = generate_queries()
    results = []

    for region, cfg in REGIONS.items():
        print("\nRegion:", region)

        for q in queries:
            url = build_url(q, cfg)
            entries = feedparser.parse(url).entries

            for e in entries:
                if is_recent(e):
                    results.append({
                        "title": e.get("title"),
                        "url": e.get("link"),
                        "region": region,
                        "query": q
                    })

            time.sleep(PAUSE)

    final = deduplicate(results)

    print("\nTotal unique:", len(final))

    with open("latam_palm_news.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title","url","region","query"])
        writer.writeheader()
        writer.writerows(final)

if __name__ == "__main__":
    main()
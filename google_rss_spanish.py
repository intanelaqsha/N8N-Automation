import feedparser
from datetime import datetime, timedelta
import time
import re

# --- CONFIGURATION (SPANISH GOOGLE NEWS) ---
RSS_BASE = "https://news.google.com/rss/search?q={query}&hl=es&gl=ES&ceid=ES:es"

# --- TARGET COMPANIES (LATAM / AFRICA) ---
TOP_COMPANIES = [
    "Dinant",
    "REPSA",
    "Grupo HAME",
    "Ocho Sur",
    "Socfin",
    "Poligrow",
    "Daabon"
]

# --- NGOs / Investigative orgs ---
NGO = [
    "Mongabay Latam",
    "Mongabay",
    "InfoAmazonia",
    "Global Witness",
    "Earthsight",
    "Greenpeace",
    "Dejusticia",
    "Rainforest Action Network"
]

# --- ISSUES (SPANISH) ---
ISSUES = [
    "deforestación",
    "conflicto",
    "corrupción",
    "derechos humanos",
    "comunidades indígenas",
    "incendios",
    "contaminación",
    "despojo de tierras",
    "trabajo forzoso"
]

# --- COUNTRIES TARGET ---
COUNTRY = [
    "Colombia",
    "Perú",
    "Guatemala",
    "Honduras",
    "Brasil",
    "Nigeria",
    "Camerún"
]

# --- PALM TERMS ---
PALM_TERMS = [
    "aceite de palma",
    "palma aceitera"
]

DAYS_LIMIT = 7

# --- FUNCTIONS ---
def fetch_news(query):
    url = RSS_BASE.format(query=query.replace(" ", "+"))
    return feedparser.parse(url).entries

def is_recent(entry, days=DAYS_LIMIT):
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
        return pub_date >= datetime.now() - timedelta(days=days)
    return False

def normalize_title(title):
    words = re.findall(r'\w+', title.lower())
    return set(words)

def is_similar(title1, title2, min_common=3):
    words1 = normalize_title(title1)
    words2 = normalize_title(title2)
    common = words1 & words2
    return len(common) >= min_common

def deduplicate(results):
    unique = []
    for r in results:
        duplicate_found = False
        for u in unique:
            if is_similar(r["title"], u["title"], min_common=4):
                duplicate_found = True
                break
        if not duplicate_found:
            unique.append(r)
    return unique

def search_and_collect(queries, label):
    results = []
    for q in queries:
        print(f"\n🔍 Searching {label}: {q}")
        entries = fetch_news(q)
        for e in entries:
            if is_recent(e):
                results.append({
                    "title": e.get("title", ""),
                    "url": e.get("link", ""),
                    "published": e.get("published", "Unknown"),
                    "query": q
                })
        time.sleep(1)
    return results

# --- MAIN WORKFLOW ---
def main():
    all_results = []

    # Pass 1: Palm oil + issue
    palm_queries = [
        f"{palm} {issue}"
        for palm in PALM_TERMS
        for issue in ISSUES
    ]
    all_results.extend(search_and_collect(palm_queries, "palm_issue"))

    # Pass 2: Company + issue
    company_queries = [
        f"{company} {issue}"
        for company in TOP_COMPANIES
        for issue in ISSUES
    ]
    all_results.extend(search_and_collect(company_queries, "company_issue"))

    # Pass 3: Palm oil + country + issue
    country_queries = [
        f"{palm} {issue} {country}"
        for palm in PALM_TERMS
        for issue in ISSUES
        for country in COUNTRY
    ]
    all_results.extend(search_and_collect(country_queries, "palm_country"))

    # Pass 4: Palm oil + NGO
    ngo_queries = [
        f"{palm} {ngo}"
        for palm in PALM_TERMS
        for ngo in NGO
    ]
    all_results.extend(search_and_collect(ngo_queries, "palm_ngo"))

    # Deduplicate
    final_results = deduplicate(all_results)

    print(f"\n✅ Found {len(final_results)} unique Spanish palm oil articles.\n")

    for idx, r in enumerate(final_results, 1):
        print(f"[{idx}] {r['title']}")
        print(f"   Published: {r['published']}")
        print(f"   URL: {r['url']}")
        print(f"   Query: {r['query']}\n")

if __name__ == "__main__":
    main()

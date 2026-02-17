# google_rss_idn_better.py
# Improved Google News RSS search for palm oil issues (Indonesian)
# Requires: feedparser
# Install: python3 -m pip install feedparser

import feedparser
from datetime import datetime, timedelta
import time
import re
import urllib.parse
import difflib
import csv

# --- CONFIGURATION ---
RSS_BASE = "https://news.google.com/rss/search?q={query}&hl=id&gl=ID&ceid=ID:id"

# --- COMPANY / NGO lists (adjust as needed) ---
# Use a dict of aliases so queries include common variants (lowercase used when building query)
COMPANY_ALIASES = {
    "Wilmar": ["Wilmar", "Wilmar International", "Wilmar Group"],
    "Musim Mas": ["Musim Mas", "Musimmas", "Musim Mas Group"],
    "Golden Agri-Resources": ["Golden Agri-Resources", "GAR", "Sinar Mas Agro Resources", "Sinar Mas"],
    "Astra Agro Lestari": ["Astra Agro Lestari", "Astra Agro", "AAL"],
    "Permata Hijau Group": ["Permata Hijau", "Permata Hijau Group", "PHG"],
    "Apical (RGE)": ["Apical", "Royal Golden Eagle", "RGE"],
    "Asian Agri": ["Asian Agri", "Santika/Asian Agri"],   # examples
    "Sime Darby": ["Sime Darby", "Sime Darby Plantation"]
}

# NGO / media list to combine with queries
NGO = [
    "Mongabay", "Rainforest Action Network", "Mighty Earth",
    "Greenpeace", "Sawit Watch", "WALHI", "Reuters", "BBC Indonesia", "Tempo", "Kompas"
]

ISSUES = [
    "deforestasi", "konflik", "korupsi", "sengketa", "kriminalisasi",
    "masyarakat adat", "kebakaran", "polusi", "pelanggaran HAM", "illegal clearing"
]

DAYS_LIMIT = 3
PAUSE_SECONDS = 1.0  # polite delay between requests
SIMILARITY_RATIO = 0.85  # for title fuzzy dedupe (0-1)

# --- HELPERS ---
def build_query(parts):
    """Build a Google News RSS query string (URL-encoded). parts is a list of words/phrases.
       We encode with quote_plus to be safe."""
    q = " ".join(parts)
    return urllib.parse.quote_plus(q)

def fetch_news(query):
    url = RSS_BASE.format(query=query)
    parsed = feedparser.parse(url)
    return parsed.entries

def is_recent(entry, days=DAYS_LIMIT):
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
        return pub_date >= datetime.now() - timedelta(days=days)
    return False

def normalize_title(title):
    words = re.findall(r'\w+', (title or "").lower())
    return set(words)

def title_similarity(a, b):
    """Fuzzy similarity using SequenceMatcher on full title plus word overlap."""
    if not a or not b:
        return 0.0
    seq = difflib.SequenceMatcher(None, a.lower(), b.lower())
    ratio = seq.ratio()
    # add small weight for word overlap
    words_a = normalize_title(a)
    words_b = normalize_title(b)
    if words_a or words_b:
        overlap = len(words_a & words_b) / max(1, min(len(words_a), len(words_b)))
    else:
        overlap = 0
    return 0.6 * ratio + 0.4 * overlap

def deduplicate_by_url_and_title(items):
    seen_urls = set()
    unique = []
    for it in items:
        url = it.get("url") or it.get("link") or ""
        if not url:
            continue
        if url in seen_urls:
            continue
        # fuzzy title check vs existing unique items
        dup = False
        for u in unique:
            sim = title_similarity(it.get("title",""), u.get("title",""))
            if sim >= SIMILARITY_RATIO:
                dup = True
                break
        if not dup:
            seen_urls.add(url)
            unique.append(it)
    return unique

# --- QUERY BUILDING ---

def company_queries_from_aliases(aliases_map, issues):
    queries = []
    for company, aliases in aliases_map.items():
        # join aliases with OR inside quotes so Google News tries variants
        alias_part = " OR ".join([f'"{a}"' for a in aliases])
        for issue in issues:
            # try combinations that include 'sawit' and 'minyak sawit' and plain company+issue
            queries.append(f'({alias_part}) {issue} sawit')
            queries.append(f'({alias_part}) {issue} "minyak sawit"')
            queries.append(f'({alias_part}) {issue}')
    return queries

def simple_palm_issue_queries(issues, ngos):
    queries = []
    for issue in issues:
        queries.append(f'sawit {issue}')
        for ngo in ngos:
            queries.append(f'sawit {issue} {ngo}')
    return queries

# --- COLLECTOR ---
def search_and_collect(query_list, label):
    results = []
    for q in query_list:
        # query is already a string; build URL-encoded version
        q_enc = build_query([q])
        print(f"Searching [{label}] → {q}")
        entries = fetch_news(q_enc)
        for e in entries:
            if is_recent(e):
                results.append({
                    "title": e.get("title", "").strip(),
                    "url": e.get("link") or e.get("id") or "",
                    "published": e.get("published", "Unknown"),
                    "query": q
                })
        time.sleep(PAUSE_SECONDS)
    return results

# --- OUTPUT ---
def save_csv(results, filename="results.csv"):
    keys = ["title","published","url","query"]
    with open(filename, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k,"") for k in keys})
    print(f"Saved {len(results)} rows to {filename}")

# --- MAIN ---
def main():
    all_results = []

    # pass 1: general palm + issue + NGOs
    all_results.extend(search_and_collect(simple_palm_issue_queries(ISSUES, NGO), "palm_issue_ngo"))

    # pass 2: company-specific queries
    all_results.extend(search_and_collect(company_queries_from_aliases(COMPANY_ALIASES, ISSUES), "company_issue"))

    # deduplicate
    final = deduplicate_by_url_and_title(all_results)
    print(f"\nFound {len(final)} unique recent articles (within {DAYS_LIMIT} days)\n")

    # print summary
    for i, r in enumerate(final, start=1):
        print(f"[{i}] {r['title']}")
        print(f"    published: {r['published']}")
        print(f"    url: {r['url']}")
        print(f"    query: {r['query']}\n")

    # save csv for easier post-processing
    save_csv(final, "palm_news_results.csv")

if __name__ == "__main__":
    main()
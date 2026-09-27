"""Phase 1: fetch each source URL once and save raw snapshots to data/raw/.

Later phases read only from these snapshots, so the network is needed only here.
"""
import csv
import json
import time
from datetime import date

import requests
from bs4 import BeautifulSoup

from src.config import RAW_DIR, SOURCES_CSV

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}
TIMEOUT = 15
RETRIES = 3


def load_sources() -> list[dict]:
    with open(SOURCES_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fetch(url: str) -> requests.Response:
    last_err = None
    for attempt in range(RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {url} after {RETRIES} attempts: {last_err}")


def extract_next_data(html: str) -> dict | None:
    tag = BeautifulSoup(html, "lxml").find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return None
    try:
        return json.loads(tag.string)
    except json.JSONDecodeError:
        return None


def visible_text_len(html: str) -> int:
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    return len(soup.get_text(" ", strip=True))


def snapshot(source: dict) -> dict:
    slug, url = source["slug"], source["url"]
    resp = fetch(url)
    html = resp.text
    next_data = extract_next_data(html)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{slug}.html").write_text(html, encoding="utf-8")
    if next_data is not None:
        (RAW_DIR / f"{slug}.json").write_text(
            json.dumps(next_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    meta = {
        "slug": slug,
        "url": url,
        "fetched_at": date.today().isoformat(),
        "status": resp.status_code,
        "has_next_data": next_data is not None,
        "html_bytes": len(html),
        "visible_text_chars": visible_text_len(html),
    }
    (RAW_DIR / f"{slug}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def main() -> None:
    results = []
    for source in load_sources():
        try:
            results.append(snapshot(source))
        except Exception as e:
            results.append({"slug": source["slug"], "status": "ERROR", "error": str(e)})

    print(f"{'slug':<16} {'status':<7} {'next_data':<10} {'html_bytes':>10} {'text_chars':>10}")
    for r in results:
        if r["status"] == "ERROR":
            print(f"{r['slug']:<16} ERROR   {r['error']}")
        else:
            print(f"{r['slug']:<16} {r['status']:<7} {str(r['has_next_data']):<10} "
                  f"{r['html_bytes']:>10} {r['visible_text_chars']:>10}")


if __name__ == "__main__":
    main()

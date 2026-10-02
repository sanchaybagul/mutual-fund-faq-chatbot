"""Phase 1: fetch each source URL once and save raw snapshots to data/raw/.

Later phases read only from these snapshots, so the network is needed only here.
HTML pages are saved as <slug>.html (plus <slug>.json when the page embeds Next.js
data); PDFs (KIMs, factsheet) are saved as <slug>.pdf.

www.hdfcfund.com rejects plain `requests` clients (HTTP 403 based on the TLS
fingerprint), so we fetch with curl_cffi impersonating a Chrome browser.
"""
import csv
import json
import time
from datetime import date

from bs4 import BeautifulSoup
from curl_cffi import requests

from src.config import RAW_DIR, SOURCES_CSV

TIMEOUT = 60
RETRIES = 3


def load_sources() -> list[dict]:
    with open(SOURCES_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def is_pdf_source(source: dict) -> bool:
    return source["url"].lower().split("?")[0].endswith(".pdf")


def fetch(url: str):
    last_err = None
    for attempt in range(RETRIES):
        try:
            resp = requests.get(url, impersonate="chrome", timeout=TIMEOUT)
            resp.raise_for_status()
            return resp
        except Exception as e:  # curl_cffi raises its own error types
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
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    meta = {"slug": slug, "url": url, "fetched_at": date.today().isoformat(),
            "status": resp.status_code}

    if is_pdf_source(source):
        if not resp.content.startswith(b"%PDF"):
            raise RuntimeError(f"{url} did not return a PDF")
        (RAW_DIR / f"{slug}.pdf").write_bytes(resp.content)
        meta.update(format="pdf", bytes=len(resp.content))
    else:
        html = resp.text
        next_data = extract_next_data(html)
        (RAW_DIR / f"{slug}.html").write_text(html, encoding="utf-8")
        if next_data is not None:
            (RAW_DIR / f"{slug}.json").write_text(
                json.dumps(next_data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        meta.update(format="html", has_next_data=next_data is not None, bytes=len(html),
                    visible_text_chars=visible_text_len(html))

    (RAW_DIR / f"{slug}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def main() -> None:
    results = []
    for source in load_sources():
        try:
            results.append(snapshot(source))
        except Exception as e:
            results.append({"slug": source["slug"], "status": "ERROR", "error": str(e)})

    print(f"{'slug':<24} {'status':<7} {'format':<6} {'bytes':>9}")
    for r in results:
        if r["status"] == "ERROR":
            print(f"{r['slug']:<24} ERROR   {r['error']}")
        else:
            print(f"{r['slug']:<24} {r['status']:<7} {r['format']:<6} {r['bytes']:>9}")


if __name__ == "__main__":
    main()

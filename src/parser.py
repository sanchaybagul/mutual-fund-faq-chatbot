"""Phase 2: turn raw snapshots in data/raw/ into structured SourceDoc objects.

One parser per source_type (see sources.csv):
- scheme_page     HDFC MF scheme page: facts from the embedded __NEXT_DATA__ JSON (docs/field_map.md)
- kim             Key Information Memorandum PDF: selected numbered sections
- factsheet       Monthly factsheet PDF: the fund-facts block of each of our schemes (one doc per scheme)
- statement_guide HDFC MF service pages: main article text
- regulator       SEBI / AMFI investor-education pages: main article text

Return/performance data (returns, NAV, risk ratios, portfolio holdings) is never read,
so it can't leak into the corpus (PRD GR-2).
"""
import json
import logging
import re
from dataclasses import asdict, dataclass
from functools import lru_cache

from bs4 import BeautifulSoup
from pypdf import PdfReader

from src.config import RAW_DIR
from src.loader import load_sources
from src.schemes import SCHEMES

logging.getLogger("pypdf").setLevel(logging.ERROR)  # font-encoding warnings on the factsheet

REQUIRED = ["expense_ratio", "exit_load", "min_sip", "riskometer", "benchmark"]


@dataclass
class SourceDoc:
    slug: str           # unique per doc; prefix of every chunk id
    scheme: str         # canonical scheme name, or "" for general (non-scheme) sources
    category: str
    title: str          # chunk-prefix label, e.g. "HDFC Small Cap Fund – Direct Growth"
    source_url: str
    source_type: str
    fetched_at: str
    fields: dict[str, str]    # scheme pages only; becomes the facts card
    sections: dict[str, str]


def clean(text) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def html_to_text(fragment: str | None) -> str:
    return clean(BeautifulSoup(fragment or "", "lxml").get_text(" ", strip=True).replace("●", ""))


def html_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    return soup.get_text("\n", strip=True)


def tidy(sections: dict[str, str]) -> dict[str, str]:
    """Drop empty sections and doubled punctuation from values that already end in '.'."""
    return {k: re.sub(r"\.\.", ".", v) for k, v in sections.items() if v.strip()}


# ---------------------------------------------------------------- scheme pages (HTML + JSON)

def manager_line(m: dict) -> str:
    name = clean(m.get("managerName"))
    since = clean(m.get("since")).strip("()")
    # The site uses "Since 1970" as a placeholder for a missing date.
    return f"{name} ({since.lower()})" if since and "1970" not in since else name


# FAQ titles that ask for an opinion or suitability judgement; facts-only bot skips them.
OPINION_FAQ = re.compile(
    r"\b(should|suitable|who can|better|advantage|risky|beginners|ideal|role|why invest)\b", re.I)
# Marketing sentences on scheme pages that hint at performance (PRD GR-2).
PROMO_SENTENCE = re.compile(r"performing|track record|growth & trust|market cycles?|wealth creation", re.I)


def drop_promo(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(s for s in sentences if not PROMO_SENTENCE.search(s))


def parse_scheme_page(source: dict, fetched_at: str) -> list[SourceDoc]:
    nd = json.loads((RAW_DIR / f"{source['slug']}.json").read_text(encoding="utf-8"))
    data = nd["props"]["pageProps"]["singleFundResponse"]["data"]
    details = {k: v for block in data["details"] for k, v in block.items()}
    ov = details["Overview"]["data"]
    scheme = source["scheme"]

    managers = [manager_line(m) for m in (details.get("managers") or [])]
    managers += [manager_line(m) + " – overseas investments" for m in (details.get("overseasManagers") or [])]
    aum_date = clean(ov.get("aumAsMonth")).strip("()")
    exit_load = html_to_text(ov.get("exitLoad")) or clean(ov.get("exitLoadValue"))

    fields = {
        "category":      f"{clean(data['meta'].get('category'))} – {source['category']}",
        "plan_type":     "Direct Plan – Growth",
        "expense_ratio": f"{ov['terDirecct']}% (Direct Plan); Regular Plan: {ov['terRegular']}%"
                         if ov.get("terDirecct") else "",
        "exit_load":     "Nil" if exit_load.upper() == "NIL" else exit_load,
        "min_sip":       f"₹{ov['minimumSip']}" if ov.get("minimumSip") else "",
        "lock_in":       clean(ov.get("lockInValue")) or "None",
        "riskometer":    clean((ov.get("risk") or [{}])[0].get("name")),
        "benchmark":     clean((ov.get("benchmark") or [""])[0]),
        "aum":           f"₹{ov['aum']} Cr (as on {aum_date})" if ov.get("aum") else "",
        "fund_managers": "; ".join(managers),
        "launch_date":   f"{clean(ov.get('inceptionDate'))} (Direct Plan)",
    }
    missing = [k for k in REQUIRED if not fields.get(k)]
    if missing:
        print(f"WARNING [{source['slug']}] missing required fields: {missing}")

    about = html_text(details["Overview"].get("overviewDescription") or "")
    about = re.split(r"\n(?:Why invest|Who can consider|How to start)", about)[0]

    faqs = [f for f in (details.get("faqs") or [])
            if not OPINION_FAQ.search(f["title"].replace(scheme, ""))]  # "Balanced Advantage" isn't an opinion
    faq_text = "\n".join(
        f"Q: {re.sub(r'^[0-9]+[.)]\s*', '', clean(f['title']))} A: {html_to_text(f['description'])}"
        for f in faqs
    )

    sections = {
        "About the Scheme": drop_promo(clean(about.replace("\n", " "))),
        "Expense Ratio and Fund Size": f"Total expense ratio (TER): {fields['expense_ratio']}. "
                                       f"Fund size (AUM): {fields['aum']}.",
        "Minimum Investment and Lock-in": f"Minimum SIP investment: {fields['min_sip']}. "
                                          f"Lock-in period: {fields['lock_in']}.",
        "Exit Load": f"Exit load: {fields['exit_load']}.",
        "Riskometer and Benchmark": f"Riskometer: {fields['riskometer']} risk. Benchmark: {fields['benchmark']}.",
        "Fund Management": f"Fund managers: {fields['fund_managers']}.",
        "FAQs": faq_text,
    }
    return [SourceDoc(source["slug"], scheme, source["category"], f"{scheme} – Direct Growth",
                      source["url"], source["source_type"], fetched_at, fields, tidy(sections))]


# ---------------------------------------------------------------- KIM (PDF)

# The KIM template numbers its sections 1-23; we keep the factual, investor-facing ones.
# Skipped: asset allocation / strategy / risk (long legal text), performance (GR-2),
# and fund manager (dated; the scheme page is current).
KIM_TITLES = {
    1: "Name of Scheme", 2: "Type of Scheme", 3: "Category of Scheme", 4: "SEBI Scheme Code",
    5: "Investment Objective", 6: "Asset Allocation", 7: "Investment Strategy", 8: "Risk Profile",
    9: "Plans", 10: "Applicable NAV", 11: "Minimum Application", 12: "Despatch of Redemption",
    13: "Benchmark Index", 14: "Dividend", 15: "Name of the Fund Manager", 16: "Name of the Trustee",
    17: "Performance of the Scheme", 18: "Additional Scheme", 19: "Expenses of the Scheme",
    20: "Tax Treatment", 21: "Daily Net Asset Value", 22: "For Investor Grievances", 23: "Unit Holder",
}
KIM_KEEP = {
    2: "Type of Scheme", 5: "Investment Objective", 9: "Plans and Options",
    11: "Minimum Application Amount", 12: "Redemption Payout Timeline", 13: "Benchmark Index",
    19: "Load Structure and Expenses (FY 2024-25 actuals)",
    23: "Account Statements",
}


def pdf_pages(slug: str) -> list[str]:
    return [p.extract_text() or "" for p in PdfReader(RAW_DIR / f"{slug}.pdf").pages]


def kim_sections(text: str) -> dict[int, str]:
    """Split on the numbered headings, searching in order so table rows like '2. Derivatives' don't match."""
    found, start = {}, 0
    for n, title in KIM_TITLES.items():
        m = re.compile(rf"^\s*{n}\.\s+{re.escape(title)}[^\n]*\n", re.M).search(text, start)
        if m:
            found[n], start = m, m.end()
    keys = sorted(found)
    return {n: text[found[n].end():(found[keys[i + 1]].start() if i + 1 < len(keys) else len(text))]
            for i, n in enumerate(keys)}


def parse_kim(source: dict, fetched_at: str) -> list[SourceDoc]:
    pages = [re.sub(r"^\s*\d+\s*\n\s*HDFC[^\n]*- KIM\s*\n", "", p) for p in pdf_pages(source["slug"])]
    text = "\n".join(pages)
    dated = re.search(r"Key Information Memorandum is dated ([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    raw = kim_sections(text)

    sections = {}
    for n, label in KIM_KEEP.items():
        body = raw.get(n, "")
        if n == 23:  # keep only the account-statement part, not the periodic-disclosure table
            body = body.split("Periodic Disclosures")[0]
        sections[label] = clean(body)

    title = f"{source['scheme']} – Key Information Memorandum" + (f" dated {dated.group(1)}" if dated else "")
    return [SourceDoc(source["slug"], source["scheme"], source["category"], title, source["url"],
                      source["source_type"], fetched_at, {}, tidy(sections))]


# ---------------------------------------------------------------- factsheet (PDF)

FACTSHEET_HEADINGS = [  # (label, heading as printed); labels starting with "_" are dropped
    ("Category", "CATEGORY OF SCHEME"), ("Investment objective", "INVESTMENT OBJECTIVE"),
    ("Fund managers (name, managing since, total experience)", "FUND MANAGER"),
    ("Inception date", "DATE OF ALLOTMENT/INCEPTION DATE"), ("_nav", "NAV"),
    ("Assets under management (AUM)", "ASSETS UNDER MANAGEMENT"), ("_quant", "QUANTITATIVE DATA"),
    ("Base expense ratio", "EXPENSE RATIO"), ("Benchmark", "#BENCHMARK INDEX"),
    ("_addl", "##ADDL. BENCHMARK INDEX"), ("Exit load", "EXIT LOAD"),
    ("_end", "....Contd on next page"), ("_end", "PORTFOLIO"),
]


def factsheet_block(page: str) -> list[str]:
    hits = sorted((m.start(), m.end(), label) for label, head in FACTSHEET_HEADINGS
                  if (m := re.search(rf"^\s*{re.escape(head)}", page, re.M)))
    lines = []
    for i, (_, end, label) in enumerate(hits):
        if label.startswith("_"):
            continue
        body = clean(page[end:hits[i + 1][0] if i + 1 < len(hits) else len(page)])
        body = re.sub(r"^[\s:¥€$@]+|[@]+$", "", body).replace("Name Since Total Exp ", "")
        lines.append(f"{label}: {body}")
    return lines


def parse_factsheet(source: dict, fetched_at: str) -> list[SourceDoc]:
    pages = pdf_pages(source["slug"])
    month = re.search(r"\|\s*([A-Z][a-z]+ \d{4})", "\n".join(pages[5:10]))
    docs = []
    for scheme, info in SCHEMES.items():
        title = re.escape(info["factsheet_title"])
        # A scheme's first factsheet page starts with the product-label note, then "<page> | <Month YYYY>", then the name.
        page = next((p for p in pages if p.lstrip().startswith("For Product label")
                     and re.search(rf"\|\s*\w+ \d{{4}}\s*\n{title}\s*\n", p[:400])), None)
        if page is None:
            print(f"WARNING [{source['slug']}] no factsheet page for {scheme}")
            continue
        label = f"Fund facts (HDFC MF Factsheet, {month.group(1) if month else 'monthly'})"
        docs.append(SourceDoc(f"{source['slug']}-{info['slug']}", scheme, info["category"],
                              f"{scheme} – Factsheet", source["url"], source["source_type"], fetched_at,
                              {}, tidy({label: "\n".join(factsheet_block(page))})))
    return docs


# ---------------------------------------------------------------- guides (HTML articles)

# (start marker, end marker) around the article body in the page's visible text.
ARTICLE_BOUNDS = {
    "www.hdfcfund.com":          ("Reading Line\nOn\nOff\n", "\nOUR VISION"),
    "investor.sebi.gov.in":      ("\nContent\n", None),
    "www.mutualfundssahihai.com": ("\nHome\n/\n", "\nRelated Articles"),
}
# Form-widget and link labels that carry no content.
NOISE_LINES = {"PAN", "OR", "Folio", "Send OTP", "Duration", "Current Financial Year", "SEND EMAIL",
               "Click here", "Services", "Learn", "Blog", ">", "/"}


def join_wrapped_lines(lines: list[str]) -> list[str]:
    """Inline tags (<a>, <strong>) split sentences across lines; glue them back together."""
    out = []
    for line in lines:
        if out and (line[:1].islower() or line[:1] in ").,:;" or out[-1].endswith(("(", "-", "e.g."))
                    or (not out[-1].endswith((".", ":", "?", "!")) and len(out[-1].split()) > 3
                        and not line[:1].isdigit())):
            out[-1] = f"{out[-1]} {line}"
        else:
            out.append(line)
    return out


def article_text(html: str, url: str) -> tuple[str, str]:
    """Return (page title, article body) from a guide page."""
    soup = BeautifulSoup(html, "lxml")
    page_title = clean(soup.title.get_text() if soup.title else "")
    text = html_text(html)
    start, end = ARTICLE_BOUNDS.get(url.split("/")[2], (None, None))
    if start and start in text:
        text = text.split(start, 1)[1]
    if end and end in text:
        text = text.split(end, 1)[0]

    seen, lines = set(), []
    for line in (clean(x) for x in text.split("\n")):
        if not line or line in NOISE_LINES or line in seen:  # SEBI pages repeat paragraphs
            continue
        seen.add(line)
        lines.append(line)
    return page_title, "\n".join(join_wrapped_lines(lines))


def parse_guide(source: dict, fetched_at: str) -> list[SourceDoc]:
    html = (RAW_DIR / f"{source['slug']}.html").read_text(encoding="utf-8")
    page_title, body = article_text(html, source["url"])
    title = re.sub(r"^:+\s*|\s*::$", "", page_title)
    title = re.sub(r"^Securities Market Investment:\s*", "", title).split(" | ")[0].strip()
    publisher = {"investor.sebi.gov.in": "SEBI", "www.mutualfundssahihai.com": "AMFI"}.get(
        source["url"].split("/")[2], "HDFC Mutual Fund")
    return [SourceDoc(source["slug"], "", source["category"], f"{publisher} – {title}", source["url"],
                      source["source_type"], fetched_at, {}, tidy({title: body}))]


# ---------------------------------------------------------------- dispatch

PARSERS = {
    "scheme_page": parse_scheme_page,
    "kim": parse_kim,
    "factsheet": parse_factsheet,
    "statement_guide": parse_guide,
    "regulator": parse_guide,
}


def parse_source(source: dict) -> list[SourceDoc]:
    meta = json.loads((RAW_DIR / f"{source['slug']}.meta.json").read_text(encoding="utf-8"))
    return PARSERS[source["source_type"]](source, meta["fetched_at"])


@lru_cache
def _parse_all() -> tuple[SourceDoc, ...]:
    return tuple(d for s in load_sources() for d in parse_source(s))


def parse_all() -> list[SourceDoc]:
    return list(_parse_all())  # the factsheet PDF is slow to read; parse once per process


def main() -> None:
    for doc in parse_all():
        print(json.dumps(asdict(doc), indent=2, ensure_ascii=False))
        print("-" * 80)


if __name__ == "__main__":
    main()

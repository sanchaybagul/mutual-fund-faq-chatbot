"""Phase 2: turn raw snapshots in data/raw/ into structured SchemeDoc objects.

Facts come from the embedded __NEXT_DATA__ JSON first (see docs/field_map.md);
the visible HTML is only a fallback for missing fields. Return/performance data
(stats, return_stats except .risk, NAV, analysis, peer comparison) is never read,
so it can't leak into the corpus (PRD GR-2).
"""
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

from src.config import RAW_DIR
from src.loader import load_sources

IST = timezone(timedelta(hours=5, minutes=30))
DATA_ROOT = ["props", "pageProps", "mfServerSideData"]

# Paths are relative to props.pageProps.mfServerSideData.
FIELD_PATHS = {
    "scheme_name":     ["scheme_name"],
    "fund_house":      ["fund_house"],
    "asset_class":     ["category"],
    "sub_category":    ["sub_category"],
    "plan_type":       ["plan_type"],
    "expense_ratio":   ["expense_ratio"],
    "exit_load":       ["exit_load"],
    "min_sip":         ["min_sip_investment"],
    "min_lumpsum":     ["min_investment_amount"],
    "min_additional":  ["mini_additional_investment"],
    "lock_in":         ["lock_in"],
    "riskometer":      ["return_stats", 0, "risk"],  # NOT nfo_risk (stale)
    "benchmark":       ["benchmark_name"],
    "benchmark_short": ["benchmark"],
    "aum":             ["aum"],
    "launch_date":     ["launch_date"],
    "stamp_duty":      ["stamp_duty"],
    "tax_note":        ["category_info", "tax_impact"],
    "rta_name":        ["rta_details", "rta_name"],
    "rta_website":     ["rta_details", "website"],
    "amc_website":     ["sid_url"],
}

# Label → value regexes on the visible HTML text (newline-joined), used only as fallback.
HTML_FALLBACKS = {
    "expense_ratio": r"Expense ratio\n([\d.]+)%",
    "min_sip":       r"Min\. for SIP\n₹([\d,]+)",
    "min_lumpsum":   r"Min\. for 1st investment\n₹([\d,]+)",
    "min_additional": r"Min\. for 2nd investment\n₹([\d,]+)",
    "exit_load":     r"Exit load, stamp duty and tax\nExit load\n(.+)",
    "riskometer":    r"is rated (.+?) risk",
}

REQUIRED = ["expense_ratio", "exit_load", "min_sip", "riskometer", "benchmark"]


@dataclass
class SchemeDoc:
    slug: str
    scheme: str
    category: str
    source_url: str
    source_type: str
    fetched_at: str
    fields: dict[str, str]
    sections: dict[str, str]


def get_path(d, path):
    for key in path:
        try:
            d = d[key]
        except (KeyError, IndexError, TypeError):
            return None
    return d


def clean(text) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def inr(amount) -> str:
    """Format a number with Indian digit grouping: 107295.79 -> '1,07,295.79'."""
    whole, _, frac = f"{float(amount):.2f}".partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        # Group the leading digits in pairs from the right: 107 -> 1,07
        head = ",".join(p for p in re.split(r"(?=(?:\d{2})+$)", head) if p)
        whole = f"{head},{tail}"
    frac = frac.rstrip("0")
    return f"{whole}.{frac}" if frac else whole


def fmt_rupees(value) -> str:
    return f"₹{inr(value)}" if value not in (None, "") else ""


def fmt_lock_in(lock) -> str:
    if not isinstance(lock, dict) or not any(lock.get(k) for k in ("years", "months", "days")):
        return "None"
    parts = []
    for unit in ("years", "months", "days"):
        n = lock.get(unit)
        if n:
            parts.append(f"{n} {unit if n != 1 else unit[:-1]}")
    return " ".join(parts)


def fmt_month_year(iso: str) -> str:
    """'2023-06-21T18:30:00.000Z' (UTC, = IST midnight) -> 'Jun 2023'."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(IST)
        return dt.strftime("%b %Y")
    except (ValueError, AttributeError):
        return ""


def html_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    return soup.get_text("\n", strip=True)


def parse_fields(m: dict, text: str) -> dict[str, str]:
    raw = {name: get_path(m, path) for name, path in FIELD_PATHS.items()}

    # HTML fallback for anything the JSON is missing.
    for name, pattern in HTML_FALLBACKS.items():
        if raw.get(name) in (None, ""):
            hit = re.search(pattern, text)
            if hit:
                raw[name] = hit.group(1).replace(",", "") if name.startswith("min_") else hit.group(1)

    fields = {
        "scheme_name":     clean(raw["scheme_name"]),
        "fund_house":      clean(raw["fund_house"]),
        "category":        " – ".join(x for x in (clean(raw["asset_class"]), clean(raw["sub_category"])) if x),
        "plan_type":       clean(raw["plan_type"]),
        "expense_ratio":   f"{clean(raw['expense_ratio'])}%" if raw["expense_ratio"] not in (None, "") else "",
        "exit_load":       clean(raw["exit_load"]),
        "min_sip":         fmt_rupees(raw["min_sip"]),
        "min_lumpsum":     fmt_rupees(raw["min_lumpsum"]),
        "min_additional":  fmt_rupees(raw["min_additional"]),
        "lock_in":         fmt_lock_in(raw["lock_in"]),
        "riskometer":      clean(raw["riskometer"]),
        "benchmark":       clean(raw["benchmark"]),
        "benchmark_short": clean(raw["benchmark_short"]),
        "aum":             f"₹{inr(raw['aum'])} Cr" if raw["aum"] not in (None, "") else "",
        "launch_date":     clean(raw["launch_date"]),
        "stamp_duty":      clean(raw["stamp_duty"]),
        "tax_note":        clean(raw["tax_note"]),
        "rta_name":        clean(raw["rta_name"]),
        "rta_website":     clean(raw["rta_website"]),
        "amc_website":     clean(raw["amc_website"]),
    }

    managers = m.get("fund_manager_details") or []
    fields["fund_managers"] = ", ".join(clean(fm.get("person_name")) for fm in managers if fm.get("person_name"))
    return fields


def parse_sections(m: dict, f: dict) -> dict[str, str]:
    sections = {}

    if m.get("description"):
        sections["Investment Objective"] = clean(m["description"])

    article = "an" if f["category"][:1].upper() in "AEIOU" else "a"
    sections["Scheme Overview"] = (
        f"{f['scheme_name']} is {article} {f['category']} scheme from {f['fund_house']} ({f['plan_type']} plan). "
        f"Launch date: {f['launch_date']}. Fund size (AUM): {f['aum']}. "
        f"Expense ratio: {f['expense_ratio']}."
    )

    sections["Minimum Investment"] = (
        f"Minimum SIP investment: {f['min_sip']}. Minimum first (lumpsum) investment: {f['min_lumpsum']}. "
        f"Minimum additional investment: {f['min_additional']}. Lock-in period: {f['lock_in']}."
    )

    sections["Exit Load, Stamp Duty and Tax"] = (
        f"Exit load: {f['exit_load']}. Stamp duty on investment: {f['stamp_duty']}. "
        f"Tax implication: {f['tax_note']}"
    )

    sections["Riskometer and Benchmark"] = (
        f"Riskometer: {f['riskometer']} risk. "
        f"Benchmark: {f['benchmark']} ({f['benchmark_short']})."
    )

    managers = m.get("fund_manager_details") or []
    if managers:
        lines = []
        for fm in managers:
            since = fmt_month_year(fm.get("date_from", ""))
            line = f"{clean(fm.get('person_name'))}" + (f" (managing since {since})" if since else "") + "."
            if fm.get("education"):
                line += f" Education: {clean(fm['education'])}."
            if fm.get("experience"):
                line += f" Experience: {clean(fm['experience'])}."
            lines.append(line)
        sections["Fund Management"] = "\n".join(lines)

    sections["Fund House and Registrar"] = (
        f"Fund house: {f['fund_house']} (website: {f['amc_website']}). "
        f"Registrar & Transfer Agent (RTA): {f['rta_name']} (website: {f['rta_website']})."
    )

    # Tidy doubled punctuation from values that already end in '.'
    return {k: re.sub(r"\.\.", ".", v) for k, v in sections.items()}


def parse_source(source: dict) -> SchemeDoc:
    slug = source["slug"]
    meta = json.loads((RAW_DIR / f"{slug}.meta.json").read_text(encoding="utf-8"))
    json_path = RAW_DIR / f"{slug}.json"
    next_data = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else {}
    m = get_path(next_data, DATA_ROOT) or {}
    text = html_text((RAW_DIR / f"{slug}.html").read_text(encoding="utf-8"))

    fields = parse_fields(m, text)
    missing = [k for k in REQUIRED if not fields.get(k)]
    if missing:
        print(f"WARNING [{slug}] missing required fields: {missing}")

    return SchemeDoc(
        slug=slug,
        scheme=source["scheme"],
        category=source["category"],
        source_url=source["url"],
        source_type=source["source_type"],
        fetched_at=meta["fetched_at"],
        fields=fields,
        sections=parse_sections(m, fields),
    )


def parse_all() -> list[SchemeDoc]:
    return [parse_source(s) for s in load_sources()]


def main() -> None:
    for doc in parse_all():
        print(json.dumps(asdict(doc), indent=2, ensure_ascii=False))
        print("-" * 80)


if __name__ == "__main__":
    main()

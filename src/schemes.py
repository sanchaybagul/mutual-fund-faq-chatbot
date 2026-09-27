"""Phase 5: map scheme names/aliases in a question to canonical scheme names."""
import re

SCHEME_ALIASES = {
    "HDFC Large Cap Fund": ["hdfc large cap", "large cap", "largecap", "hdfc top 100", "top 100"],
    "HDFC Flexi Cap Fund": ["hdfc flexi cap", "flexi cap", "flexicap", "flexi", "hdfc equity fund"],
    "HDFC ELSS Tax Saver Fund": ["hdfc elss", "elss", "tax saver", "taxsaver", "tax saving", "80c"],
    "HDFC Small Cap Fund": ["hdfc small cap", "small cap", "smallcap"],
    "HDFC Balanced Advantage Fund": ["hdfc balanced advantage", "balanced advantage", "baf",
                                     "dynamic asset allocation", "hybrid"],
}
# Deliberately NOT aliased: "bluechip" (SBI/ICICI names), bare "equity fund" (generic term).

# Terms whose answer differs by scheme; if no scheme is named we ask which one.
SCHEME_SPECIFIC_TERMS = [
    "expense ratio", "exit load", "sip", "lumpsum", "lump sum", "minimum investment",
    "riskometer", "risk level", "benchmark", "aum", "fund size", "fund manager",
    "managed by", "launch date", "launched", "objective",
]

OTHER_AMCS = [
    "sbi", "icici", "axis", "nippon", "kotak", "mirae", "parag parikh", "ppfas", "uti", "tata",
    "dsp", "aditya birla", "absl", "quant", "motilal", "franklin", "hsbc", "canara", "invesco",
    "edelweiss", "bandhan", "sundaram", "pgim", "mahindra", "whiteoak", "baroda", "lic", "navi",
    "zerodha", "groww mutual", "jm financial", "360 one", "bajaj finserv", "union", "iti",
]


def _pattern(alias: str) -> str:
    # word boundaries; allow "small cap" / "small-cap" / "smallcap"-style separators
    return r"\b" + r"[\s\-]?".join(map(re.escape, alias.split())) + r"\b"


# Longest aliases first so "hdfc small cap" is consumed before "small cap".
_ALIAS_INDEX = sorted(
    ((alias, scheme) for scheme, aliases in SCHEME_ALIASES.items() for alias in aliases),
    key=lambda x: -len(x[0]),
)


def detect_schemes(question: str) -> list[str]:
    """Return canonical schemes mentioned in the question, in order of first appearance."""
    text = question.lower()
    found = {}
    for alias, scheme in _ALIAS_INDEX:
        for m in re.finditer(_pattern(alias), text):
            found.setdefault(scheme, m.start())
            text = text[:m.start()] + " " * (m.end() - m.start()) + text[m.end():]  # consume span
    return sorted(found, key=found.get)


def needs_scheme(question: str) -> bool:
    text = question.lower()
    return any(re.search(_pattern(t), text) for t in SCHEME_SPECIFIC_TERMS)


def mentions_other_amc(question: str) -> bool:
    text = question.lower()
    return any(re.search(_pattern(a), text) for a in OTHER_AMCS)

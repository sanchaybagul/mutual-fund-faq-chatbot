"""Phase 7: deterministic guardrails that run BEFORE retrieval (architecture §4.1).

Order (first match wins): PII → performance → advice → off-topic → fact.
Rule-based on purpose: free, instant, and explainable in a demo.
Never log raw user input from this module.
"""
import re
from typing import Literal

from src.schemes import detect_schemes

Intent = Literal["pii", "performance", "advice", "off_topic", "fact"]

PII_PATTERNS = {
    "pan":     re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.I),
    "aadhaar": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    "phone":   re.compile(r"(?<!\d)(?:\+91[\-\s]?|0)?[6-9]\d{9}\b"),
    "email":   re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "otp":     re.compile(r"\botp\b\D{0,15}\d{4,8}\b", re.I),
    # 9+ digit runs: bank account / folio numbers. Amounts like ₹100 or ₹1,00,000 don't match.
    "account": re.compile(r"\b\d{9,18}\b"),
}

PERFORMANCE_PAT = re.compile(
    r"\b(returns?|cagr|performance|performed|performing|nav|growth rate|grown|gave|"
    r"top performing|outperform\w*|underperform\w*|profit|how much (?:will|would|can) i (?:make|earn|get))\b",
    re.I,
)
# "How are returns taxed?" is a tax fact, not a performance question.
TAX_PAT = re.compile(r"\btax(?:ed|es|ation)?\b", re.I)

ADVICE_PAT = re.compile(
    r"\b(should i|shall i|do you recommend|recommend\w*|suggest\w*|advi[cs]e|"
    r"best|better|worth it|worth investing|good (?:time|fund|investment|choice|option)|"
    r"(?:good|right|suitable|safe) for me|is it (?:good|safe|wise)|"
    r"which (?:fund|scheme|one) (?:should|to|is (?:best|better|good))|"
    r"(?:buy|sell|hold|switch|exit|redeem) (?:now|or|this|it)|"
    r"invest (?:now|more|all))\b",
    re.I,
)

MF_VOCAB = [
    "fund", "scheme", "mutual", "sip", "lumpsum", "lump sum", "nav", "expense ratio", "exit load",
    "elss", "lock-in", "lock in", "riskometer", "risk", "benchmark", "statement", "capital gain",
    "folio", "aum", "amc", "hdfc", "redeem", "redemption", "kyc", "tax", "stamp duty",
    "fund manager", "registrar", "cams", "direct plan", "growth plan", "minimum investment",
]


def contains_pii(text: str) -> bool:
    return any(p.search(text) for p in PII_PATTERNS.values())


def is_performance(text: str) -> bool:
    return bool(PERFORMANCE_PAT.search(text)) and not TAX_PAT.search(text)


def is_advice(text: str) -> bool:
    return bool(ADVICE_PAT.search(text))


def is_mf_related(text: str) -> bool:
    low = text.lower()
    return bool(detect_schemes(text)) or any(v in low for v in MF_VOCAB)


def classify(text: str) -> Intent:
    if contains_pii(text):
        return "pii"
    if is_performance(text):
        return "performance"
    if is_advice(text):
        return "advice"
    if not is_mf_related(text):
        return "off_topic"
    return "fact"

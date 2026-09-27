"""Retrieval eval: does the right (scheme, section) chunk come back? Reports hit@1 and hit@4.

    python -m scripts.eval_retrieval
"""
from src.retriever import retrieve

# (question, acceptable chunk-id prefixes: any match counts as a hit)
EVAL_SET = [
    ("What is the expense ratio of HDFC Flexi Cap Fund?", ["hdfc-flexi-cap:key-facts", "hdfc-flexi-cap:scheme-overview"]),
    ("Expense ratio of HDFC Large Cap Fund?", ["hdfc-large-cap:key-facts", "hdfc-large-cap:scheme-overview"]),
    ("What is the lock-in period for HDFC ELSS Tax Saver Fund?", ["hdfc-elss:key-facts", "hdfc-elss:minimum-investment"]),
    ("ELSS lock-in?", ["hdfc-elss:key-facts", "hdfc-elss:minimum-investment"]),
    ("What is the exit load on HDFC Small Cap Fund?", ["hdfc-small-cap:key-facts", "hdfc-small-cap:exit-load"]),
    ("Exit load of HDFC Balanced Advantage Fund?", ["hdfc-baf:key-facts", "hdfc-baf:exit-load"]),
    ("Minimum SIP for HDFC Balanced Advantage Fund?", ["hdfc-baf:key-facts", "hdfc-baf:minimum-investment"]),
    ("Minimum SIP amount for tax saver fund", ["hdfc-elss:key-facts", "hdfc-elss:minimum-investment"]),
    ("Riskometer of HDFC Large Cap?", ["hdfc-large-cap:key-facts", "hdfc-large-cap:riskometer"]),
    ("What is the benchmark of HDFC Small Cap Fund?", ["hdfc-small-cap:key-facts", "hdfc-small-cap:riskometer"]),
    ("Who manages HDFC Flexi Cap Fund?", ["hdfc-flexi-cap:key-facts", "hdfc-flexi-cap:fund-management"]),
    ("What is the AUM of HDFC BAF?", ["hdfc-baf:key-facts", "hdfc-baf:scheme-overview"]),
    ("Stamp duty on HDFC ELSS?", ["hdfc-elss:exit-load"]),
    ("What is the investment objective of HDFC Small Cap Fund?", ["hdfc-small-cap:investment-objective"]),
    ("Who is the registrar for HDFC Large Cap Fund?", ["hdfc-large-cap:fund-house-and-registrar"]),
    ("How are gains taxed for HDFC Flexi Cap?", ["hdfc-flexi-cap:exit-load"]),
]


def main() -> None:
    hit1 = hit4 = 0
    for q, prefixes in EVAL_SET:
        ids = [c["id"] for c in retrieve(q).chunks]
        h1 = bool(ids) and any(ids[0].startswith(p) for p in prefixes)
        h4 = any(i.startswith(p) for i in ids[:4] for p in prefixes)
        hit1 += h1
        hit4 += h4
        print(f"  {'✓' if h1 else ('~' if h4 else '✗')}  {ids[0] if ids else '-':<48} {q}")
    n = len(EVAL_SET)
    print(f"\nhit@1: {hit1}/{n} = {hit1 / n:.0%}   hit@4: {hit4}/{n} = {hit4 / n:.0%}   (target hit@1 ≥ 80%)")


if __name__ == "__main__":
    main()

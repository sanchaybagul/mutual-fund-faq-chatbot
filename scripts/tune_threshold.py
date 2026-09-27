"""Print top-1 similarity for in-scope vs out-of-scope questions to pick SIM_THRESHOLD.

    python -m scripts.tune_threshold
"""
from src.retriever import retrieve

IN_SCOPE = [
    ("What is the expense ratio of HDFC Flexi Cap Fund?", "hdfc-flexi-cap:key-facts:0"),
    ("What is the lock-in period for HDFC ELSS Tax Saver Fund?", "hdfc-elss"),
    ("ELSS lock-in?", "hdfc-elss"),
    ("What is the exit load on HDFC Small Cap Fund?", "hdfc-small-cap"),
    ("Minimum SIP for HDFC Balanced Advantage Fund?", "hdfc-baf"),
    ("Riskometer of HDFC Large Cap?", "hdfc-large-cap"),
    ("What is the benchmark of HDFC Small Cap Fund?", "hdfc-small-cap"),
    ("Who manages HDFC Flexi Cap Fund?", "hdfc-flexi-cap"),
    ("fund manager of hdfc top 100", "hdfc-large-cap"),
    ("What is the AUM of HDFC BAF?", "hdfc-baf"),
    ("Stamp duty on HDFC ELSS?", "hdfc-elss"),
    ("What is the investment objective of HDFC Small Cap Fund?", "hdfc-small-cap"),
    ("Who is the registrar for HDFC Large Cap Fund?", "hdfc-large-cap"),
    ("How are gains taxed for HDFC Flexi Cap?", "hdfc-flexi-cap"),
    ("Minimum lumpsum for tax saver fund", "hdfc-elss"),
]
OUT_OF_SCOPE = [
    "What is the capital of France?",
    "How do I bake a chocolate cake?",
    "What is the weather in Mumbai today?",
    "Tell me a joke",
    "What is the price of bitcoin?",
    "Who won the cricket world cup?",
    "How do I reset my Gmail password?",
    "What is the NAV of SBI Bluechip Fund?",
    "Expense ratio of Axis Small Cap Fund?",
]


def main() -> None:
    print("IN-SCOPE (want: ok, correct scheme at rank 1)")
    for q, expect in IN_SCOPE:
        r = retrieve(q, threshold=0.0)
        top = r.chunks[0] if r.chunks else None
        ok = bool(top) and top["id"].startswith(expect)
        print(f"  {top['similarity'] if top else 0:.3f}  {'✓' if ok else '✗'}  {r.status:<9} "
              f"{top['id'] if top else '-':<45} {q}")
    print("\nOUT-OF-SCOPE (want: not_found)")
    for q in OUT_OF_SCOPE:
        r = retrieve(q, threshold=0.0)
        top = r.chunks[0] if r.chunks else None
        print(f"  {top['similarity'] if top else 0:.3f}     {r.status:<9} "
              f"{top['id'] if top else '(short-circuited)':<45} {q}")


if __name__ == "__main__":
    main()

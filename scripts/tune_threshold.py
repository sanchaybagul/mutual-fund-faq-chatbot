"""Print top-1 similarity for in-scope vs out-of-scope questions to pick SIM_THRESHOLD.

    python -m scripts.tune_threshold
"""
from src.retriever import retrieve

# (question, scheme the rank-1 chunk must belong to; "General" = SEBI/AMFI/HDFC service pages)
IN_SCOPE = [
    ("What is the expense ratio of HDFC Flexi Cap Fund?", "HDFC Flexi Cap Fund"),
    ("What is the lock-in period for HDFC ELSS Tax Saver Fund?", "HDFC ELSS Tax Saver Fund"),
    ("ELSS lock-in?", "HDFC ELSS Tax Saver Fund"),
    ("What is the exit load on HDFC Small Cap Fund?", "HDFC Small Cap Fund"),
    ("Minimum SIP for HDFC Balanced Advantage Fund?", "HDFC Balanced Advantage Fund"),
    ("Riskometer of HDFC Large Cap?", "HDFC Large Cap Fund"),
    ("What is the benchmark of HDFC Small Cap Fund?", "HDFC Small Cap Fund"),
    ("Who manages HDFC Flexi Cap Fund?", "HDFC Flexi Cap Fund"),
    ("fund manager of hdfc top 100", "HDFC Large Cap Fund"),
    ("What is the AUM of HDFC BAF?", "HDFC Balanced Advantage Fund"),
    ("What is the investment objective of HDFC Small Cap Fund?", "HDFC Small Cap Fund"),
    ("Minimum redemption amount for tax saver fund", "HDFC ELSS Tax Saver Fund"),
    ("How do I download my capital gains statement?", "General"),
    ("Is there a fee for the account statement?", "General"),
    ("What is a riskometer?", "General"),
    ("What is a lock-in period?", "General"),
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
        ok = bool(top) and top["metadata"]["scheme"] == expect
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

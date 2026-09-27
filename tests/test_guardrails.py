import pytest

from src.guardrails import classify, contains_pii


@pytest.mark.parametrize("text,expected", [
    # Plan table (implementation.md Phase 7)
    ("My PAN is ABCDE1234F", "pii"),
    ("call me on 9876543210", "pii"),
    ("Minimum SIP is ₹100?", "fact"),
    ("Should I buy HDFC Small Cap?", "advice"),
    ("Which is better, flexi cap or large cap?", "advice"),
    ("What were the 3 year returns of ELSS?", "performance"),
    ("What's the weather today?", "off_topic"),
    ("Exit load of HDFC Flexi Cap?", "fact"),
    ("How do I download my capital gains statement?", "fact"),
    # More PII
    ("my pan abcde1234f what is my balance", "pii"),
    ("Aadhaar 1234 5678 9012", "pii"),
    ("email me at someone@example.com", "pii"),
    ("my OTP is 482913", "pii"),
    ("folio 1234567890123 exit load?", "pii"),
    ("+91 9876543210 is my number", "pii"),
    # Performance
    ("Which fund gave better returns, large cap or flexi cap?", "performance"),
    ("What is the NAV of HDFC ELSS?", "performance"),
    ("How has HDFC Small Cap performed?", "performance"),
    ("What is the CAGR of BAF?", "performance"),
    # Advice
    ("Is HDFC Small Cap good for me?", "advice"),
    ("Is it a good time to invest in ELSS?", "advice"),
    ("Which fund should I pick?", "advice"),
    ("What is the best HDFC fund?", "advice"),
    ("Do you recommend HDFC Flexi Cap?", "advice"),
    ("Should I sell my large cap fund now?", "advice"),
    # Facts that look similar to advice/performance but aren't
    ("How are returns taxed for HDFC Flexi Cap?", "fact"),
    ("What is the exit load if I redeem within a year?", "fact"),
    ("What is the lock-in for tax saver fund?", "fact"),
    ("Who manages HDFC Balanced Advantage Fund?", "fact"),
    ("What is the riskometer of HDFC Large Cap?", "fact"),
    ("What is the expense ratio?", "fact"),
    # Off-topic
    ("Tell me a joke", "off_topic"),
    ("What is the capital of France?", "off_topic"),
    ("hello", "off_topic"),
])
def test_classify(text, expected):
    assert classify(text) == expected


@pytest.mark.parametrize("text", [
    "Minimum SIP is ₹100", "Expense ratio 0.78%", "AUM ₹1,07,295.79 Cr", "₹1,00,000 lumpsum",
    "Exit load 1% within 1 year", "launched 01-Jan-2013", "NIFTY 100 TRI", "BSE 250 SmallCap",
    "stamp duty 0.005% from July 1st, 2020", "tax above Rs 1.25 lakh at 12.5%", "ELSS 3 years lock-in",
])
def test_no_pii_false_positives(text):
    assert not contains_pii(text)

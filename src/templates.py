"""Phase 6: fixed response text for non-answer paths (refusals, not-found, clarify, PII)."""

NOT_FOUND = "I couldn't find that in my sources. You can check the scheme page for more details."
CLARIFY = ("Which scheme do you mean? I cover: HDFC Large Cap, Flexi Cap, ELSS Tax Saver, "
           "Small Cap, and Balanced Advantage.")
ADVICE = ("I can only share factual information about these schemes and can't give investment "
          "advice. To learn how to evaluate mutual funds, see the link below.")
PERFORMANCE = ("I don't compute or compare returns. Please refer to the official factsheet "
               "for performance data.")
PII_BLOCK = ("Please don't share personal information like PAN, Aadhaar, account numbers, OTPs, "
             "email or phone. I haven't stored your message.")
OFF_TOPIC = ("I can only answer factual questions about 5 HDFC Mutual Fund schemes, HDFC MF statements, "
             "and basic mutual fund terms.")
SERVICE_ERROR = "Sorry, the answer service is temporarily unavailable. Please try again shortly."

# Educational link for refusals: SEBI's official investor-education portal.
# (PRD open question #2: swap for an AMFI page if preferred.)
EDU_LINK = "https://investor.sebi.gov.in/"

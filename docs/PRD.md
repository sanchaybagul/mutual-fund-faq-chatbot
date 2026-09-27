# PRD: Mutual Fund FAQ Assistant (Facts-Only RAG Chatbot)

| | |
|---|---|
| **Status** | Draft v1 |
| **Date** | 2026-09-27 |
| **Owner** | Sanchay Bagul |
| **Context** | Class demo / milestone project |
| **Source brief** | [problemstatement.txt](problemstatement.txt) |

---

## 1. Summary

A small retrieval-augmented (RAG) chatbot that answers **factual** questions about five HDFC Mutual Fund schemes: expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, benchmark, and how to download statements. Every answer is grounded in the ingested public pages, is at most 3 sentences long, cites exactly one source link, and shows when the sources were last updated. The bot declines investment advice, performance comparisons and any personal data.

## 2. Problem

Retail investors comparing schemes, and support or content teams, answer the same MF questions again and again ("What's the exit load?", "What's the lock-in for ELSS?"). The answers exist on public pages, but they are scattered and hard to scan. General-purpose chatbots answer these questions too, but they often hallucinate figures, give no source, and drift into advice.

## 3. Goals and non-goals

### Goals
1. Answer factual scheme questions accurately from a fixed corpus of public pages.
2. Cite one clear source link in **every** answer.
3. Refuse opinion or portfolio questions politely and point to an educational link.
4. Show a complete RAG pipeline: **Load → Chunk → Embed → Store** (ingestion) and **Retrieve → Generate** (query).
5. Run as a working prototype that can be demoed live in under 3 minutes.

### Non-goals
- Investment advice, recommendations, or suitability judgments.
- Computing, comparing or predicting returns or NAV performance.
- Account-level features (login, holdings, transactions).
- Covering all AMCs or schemes; only one AMC and five schemes are in scope.
- Production hardening (auth, scaling, monitoring).

## 4. Users

| User | Need | Example question |
|---|---|---|
| Retail investor | Quick, trustworthy facts while comparing schemes | "What is the minimum SIP for HDFC Small Cap Fund?" |
| Support / content team | Consistent, cited answers to repetitive questions | "What is the exit load on HDFC Flexi Cap?" |
| Class evaluator | See a working RAG pipeline that meets the constraints | "Should I buy HDFC ELSS?" (tests the refusal) |

## 5. Scope: corpus

**AMC:** HDFC Mutual Fund. All schemes are **Direct – Growth** plans.

| # | Category | Scheme | Source URL |
|---|---|---|---|
| 1 | Large Cap | HDFC Large Cap Fund | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| 2 | Flexi Cap | HDFC Flexi Cap Fund (formerly HDFC Equity Fund) | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| 3 | ELSS | HDFC ELSS Tax Saver Fund | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| 4 | Small Cap | HDFC Small Cap Fund | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
| 5 | Hybrid (BAF) | HDFC Balanced Advantage Fund | https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth |

These five URLs make up the source list deliverable (`sources.csv` / `sources.md`).

> **Gap:** these scheme pages do not explain how to download a capital-gains or account statement, and they do not provide an educational link for refusals. See [Open questions](#13-open-questions) for the proposed fix: a small set of optional official pages from HDFC MF, AMFI, SEBI, CAMS or KFintech.

## 6. Functional requirements

### 6.1 Question answering
| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Answer factual questions about the five schemes: expense ratio, exit load, min SIP / lump sum, lock-in, riskometer, benchmark, fund manager, AUM, category, launch date, and statement download steps. | P0 |
| FR-2 | Answers are **≤ 3 sentences** and use only retrieved context. | P0 |
| FR-3 | Every answer includes **exactly one** citation link: the source URL of the top supporting chunk. | P0 |
| FR-4 | Every answer ends with `Last updated from sources: <date>`, where the date is the ingestion timestamp of the cited source. | P0 |
| FR-5 | If the answer is not in the corpus, say so plainly ("I couldn't find that in my sources") and link the most relevant scheme page. Never guess. | P0 |
| FR-6 | Resolve scheme aliases, for example "HDFC Equity Fund" → Flexi Cap, "tax saver" → ELSS, "BAF" → Balanced Advantage. | P1 |
| FR-7 | If a question names no scheme and the answer differs by scheme, ask which scheme the user means. | P1 |

### 6.2 Guardrails
| ID | Requirement | Priority |
|---|---|---|
| GR-1 | **Advice refusal.** Detect opinion or portfolio questions ("Should I buy/sell?", "Which is better?", "Is this good for me?") and reply with a polite facts-only message plus one educational link. | P0 |
| GR-2 | **No performance claims.** Do not compute, compare or rank returns. If asked about returns, point the user to the official factsheet link. | P0 |
| GR-3 | **No PII.** Detect PAN, Aadhaar, account numbers, OTPs, emails and phone numbers in user input. Block the message, do not store or log it, and tell the user not to share personal data. | P0 |
| GR-4 | Politely decline off-topic questions (not about these schemes or MF basics). | P1 |

**Refusal template (example):**
> I can only share factual information about these schemes and can't give investment advice. To understand how to evaluate mutual funds, see: <educational link>.

### 6.3 User interface
| ID | Requirement | Priority |
|---|---|---|
| UI-1 | Welcome line, e.g. "Hi! Ask me facts about 5 HDFC Mutual Fund schemes." | P0 |
| UI-2 | Three clickable example questions. | P0 |
| UI-3 | Persistent disclaimer: **"Facts-only. No investment advice."** | P0 |
| UI-4 | Show the citation as a clickable link below each answer. | P0 |
| UI-5 | Simple chat history for the current session only; nothing persisted. | P1 |

Suggested example questions:
1. "What is the expense ratio of HDFC Flexi Cap Fund?"
2. "What is the lock-in period for HDFC ELSS Tax Saver Fund?"
3. "What is the exit load on HDFC Small Cap Fund?"

## 7. System architecture

```
                    ┌──────────────── INGESTION (offline, one-time) ─────────────────┐
  5 source URLs ──► │ Load (fetch + parse HTML) → Clean → Chunk → Embed → ChromaDB   │
                    └────────────────────────────────────────────────────────────────┘

                    ┌──────────────────── QUERY (online) ────────────────────────────┐
  User question ──► │ PII check → Intent check (fact / advice / off-topic)           │
                    │    │ advice/PII/off-topic ──► canned refusal + edu link        │
                    │    ▼ fact                                                      │
                    │ Embed query → ChromaDB top-k (+ scheme metadata filter)        │
                    │    → LLM with strict grounded prompt → post-check              │
                    │    → Answer (≤3 sentences) + 1 citation + "Last updated"       │
                    └────────────────────────────────────────────────────────────────┘
```

### 7.1 Tech stack
| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | |
| Loading | `requests` + `BeautifulSoup` | Groww pages are Next.js; parse the embedded JSON (`__NEXT_DATA__`) if the visible HTML is incomplete. Fall back to Playwright only if needed. |
| Chunking | Custom, section-aware (see 7.2) | |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | 384-dim, runs locally on CPU, **max input 256 tokens** |
| Vector DB | ChromaDB (persistent, local) | Cosine distance |
| LLM | Configurable (default: an API-hosted model with a low temperature) | Used only for phrasing grounded answers |
| Orchestration | Plain Python, or LangChain / LlamaIndex if preferred | Keep it simple for the demo |
| UI | Streamlit | Easiest route to a hosted demo (Streamlit Community Cloud) |

### 7.2 Chunking strategy

The source pages are **semi-structured**: they are mostly labeled key facts (expense ratio, exit load, min SIP, benchmark, riskometer), with a few short prose sections (fund objective, fund manager bio, tax notes). Fixed-size chunking would split a label from its value and mix facts from different schemes, so we use **structure-aware chunking**:

1. **Parse by section.** Split each page into logical sections: *Key facts / fund details*, *Exit load & tax*, *Investment objective*, *Fund manager*, *Riskometer & benchmark*, *Holdings summary*, and so on.
2. **One section = one chunk** when the section is under about 200 tokens. This keeps each fact-and-value pair intact.
3. **Split long prose sections** recursively (paragraph → sentence) into chunks of about **200 tokens with a 30-token overlap**. This stays under MiniLM's 256-token limit, beyond which text is silently truncated.
4. **Prepend context** to every chunk: `"[HDFC Small Cap Fund – Direct Growth] [Exit Load] …"`. Without this, a chunk that reads "Exit load 1% if redeemed within 1 year" cannot be matched to a scheme.
5. **Emit a "facts card" chunk** per scheme: one normalized, compact chunk listing all key fields (expense ratio, exit load, min SIP, lock-in, riskometer, benchmark). This gives high retrieval precision for the most common questions.
6. **Store metadata** with every chunk:
   ```json
   { "scheme": "HDFC Small Cap Fund", "category": "Small Cap",
     "section": "Exit Load", "source_url": "https://groww.in/...",
     "fetched_at": "2026-09-27" }
   ```

### 7.3 Retrieval and generation
- **Scheme detection.** Match scheme names and aliases in the query, then apply a Chroma `where={"scheme": ...}` filter so retrieval doesn't mix up schemes.
- **Top-k.** Retrieve k = 4. If the best similarity falls below a threshold, return the "not found" response (FR-5).
- **Prompt rules.** The system prompt requires the model to:
  - answer only from the provided context;
  - use at most 3 sentences;
  - give no advice, opinions or return comparisons;
  - reply `NOT_FOUND` if the context doesn't contain the answer.
- **Citation.** Take the `source_url` of the highest-ranked chunk that was used. The LLM never writes the link itself, which rules out hallucinated URLs.
- **Post-check.** Enforce the 3-sentence cap, append the citation and the `Last updated from sources:` line, and scan the output for advice phrases ("you should invest", "better than", "recommend").

### 7.4 Intent and PII classification
- **PII:** regex checks run before anything else.

  | Data | Pattern |
  |---|---|
  | PAN | `[A-Z]{5}[0-9]{4}[A-Z]` |
  | Aadhaar | 12 digits, optionally spaced |
  | Phone | 10-digit Indian mobile number |
  | Email | standard email pattern |
  | OTP | 4–6 digits near the word "OTP" |
  | Account number | long digit strings |

  A blocked message never reaches the LLM, the vector DB or the logs.
- **Advice / performance:** a keyword and pattern list ("should I", "better", "best", "recommend", "returns", "buy", "sell", "switch", "worth it"), optionally backed by a single LLM classification call.

## 8. Non-functional requirements
| Area | Requirement |
|---|---|
| Accuracy | Numeric facts must match the source exactly. No rounding, no paraphrasing of figures. |
| Latency | Under 5 s per answer on a laptop or free hosting tier. |
| Cost | Free or near-free: local embeddings and a local vector DB. The LLM is the only paid call. |
| Privacy | Store no user input. No analytics that capture query text. |
| Reproducibility | A single `python ingest.py` rebuilds the vector store from the source list. |
| Transparency | Every answer shows its source and data freshness. |

## 9. Deliverables

| # | Deliverable | Format |
|---|---|---|
| 1 | Working prototype | Hosted Streamlit link, or a demo video of 3 minutes or less |
| 2 | Source list (the 5 URLs) | `sources.csv` / `sources.md` |
| 3 | README | Setup steps, scope (AMC and schemes), architecture, known limits |
| 4 | Sample Q&A | `sample_qa.md` with 5–10 queries, the assistant's answers and links (include at least one refusal and one PII block) |
| 5 | Disclaimer snippet | The text used in the UI: "Facts-only. No investment advice." |

**Suggested repo layout**
```
├── data/raw/            # fetched HTML/JSON snapshots
├── data/chroma/         # persisted vector store
├── src/
│   ├── ingest.py        # load → chunk → embed → store
│   ├── chunker.py
│   ├── retriever.py
│   ├── guardrails.py    # PII + intent checks
│   └── generator.py     # prompt + LLM call + post-check
├── app.py               # Streamlit UI
├── sources.csv
├── sample_qa.md
├── requirements.txt
└── README.md
```

## 10. Success criteria (demo acceptance)
| # | Test | Pass condition |
|---|---|---|
| 1 | 10 factual questions across all 5 schemes | 9 or more correct, each with 1 valid citation and the "Last updated" line |
| 2 | "Should I buy HDFC Small Cap?" | Polite refusal plus educational link, with no opinion given |
| 3 | "Which fund gave better returns?" | No computation; links to the factsheet |
| 4 | "My PAN is ABCDE1234F, …" | Blocked, with a warning; nothing stored |
| 5 | A question not covered by the corpus | "Not found" response, no hallucinated answer |
| 6 | Any answer | 3 sentences or fewer |
| 7 | UI | Welcome line, 3 example questions and the disclaimer are visible |

## 11. Known limitations
- **Point-in-time data.** Expense ratios and AUM change. Answers reflect the last ingestion date, not live values.
- **Small corpus.** Five pages, so many valid MF questions will return "not found".
- **Scraping fragility.** A change to the Groww page structure can break the loader.
- **Heuristic guardrails.** Keyword and regex checks can miss cleverly phrased advice requests or unusual PII formats.
- **English only.**

## 12. Milestones
| # | Milestone | Output |
|---|---|---|
| M1 | Ingestion | Fetch and parse the 5 pages, save raw snapshots |
| M2 | Chunk + embed + store | ChromaDB populated; inspect sample chunks |
| M3 | Retrieval + generation | CLI Q&A working with citations |
| M4 | Guardrails | PII block, advice refusal, not-found handling |
| M5 | UI | Streamlit app with welcome line, examples and disclaimer |
| M6 | Deliverables | README, sources.csv, sample_qa.md, hosting or demo video |

## 13. Open questions
1. **Source compliance.** The brief says to use official AMC/SEBI/AMFI pages and no third-party sources, but the provided URLs are Groww, which is a distributor. For the demo, do we accept Groww as given, or swap in or add the matching HDFC MF scheme pages and factsheets?
2. **Statement downloads and educational links.** Should we add a few official pages beyond the five scheme URLs? Candidates:
   - the HDFC MF, CAMS or KFintech statement page, to answer "How to download a capital-gains statement?";
   - an AMFI investor-education page, as the refusal link.
3. **LLM provider.** Which model or API is available for the class, and is there a budget?
4. **Hosting.** Streamlit Community Cloud, or a local demo plus video?

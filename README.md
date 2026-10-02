# HDFC Mutual Fund Facts Assistant (RAG Chatbot)

A small retrieval-augmented chatbot that answers **factual** questions about five HDFC Mutual Fund schemes and related investor services, using only official public pages from HDFC Mutual Fund, SEBI and AMFI. It covers:

- expense ratio, exit load and minimum SIP;
- ELSS lock-in, riskometer and benchmark;
- fund managers, AUM, minimum redemption and redemption payout time;
- how to download account and capital-gains statements;
- basic terms such as riskometer, exit load and lock-in period.

Every answer:
- is at most 3 sentences long;
- cites exactly one official source link;
- shows when the sources were last updated.

The bot refuses investment advice and performance comparisons (linking to the official factsheet for performance), and blocks any personal data.

> **Facts-only. No investment advice.**

Built as a class demo. See [docs/PRD.md](docs/PRD.md), [docs/architecture.md](docs/architecture.md) and [docs/implementation.md](docs/implementation.md).

## Scope

**AMC:** HDFC Mutual Fund. All schemes are **Direct – Growth** plans.

| Scheme | Category |
|---|---|
| HDFC Large Cap Fund | Large Cap |
| HDFC Flexi Cap Fund | Flexi Cap |
| HDFC ELSS Tax Saver Fund | ELSS |
| HDFC Small Cap Fund | Small Cap |
| HDFC Balanced Advantage Fund | Hybrid (BAF) |

**Corpus: 18 official public sources.** The full list with URLs is in [sources.md](sources.md) / [sources.csv](sources.csv). No third-party sites or blogs are used.

| Source type | Count | Publisher | Used for |
|---|---|---|---|
| Scheme pages (HTML) | 5 | HDFC MF | Current TER, exit load, minimum SIP, lock-in, riskometer, benchmark, AUM, fund managers, FAQs |
| Key Information Memoranda (PDF, Nov 21, 2025) | 5 | HDFC MF | Objective, plans/options, minimum application and redemption, payout timeline, load structure, account statements |
| Monthly factsheet (PDF, August 2026) | 1 | HDFC MF | Fund facts per scheme; the link given for performance questions |
| Statement guides (HTML) | 3 | HDFC MF | Downloading account, consolidated and capital-gains statements |
| Investor education (HTML) | 4 | SEBI (3), AMFI (1) | Riskometer, exit load, mutual fund basics, lock-in period |

## How it works

```
INGESTION (offline)   sources.csv → Load → Parse → Chunk → Embed (MiniLM) → ChromaDB
QUERY (online)        question → Guardrails → Scheme detection → Retrieve (top-4) → Groq LLM → Post-process → answer + 1 citation
```

| Stage | Implementation |
|---|---|
| Load | `src/loader.py`: fetches each source once and saves HTML (+ embedded JSON) or PDF to `data/raw/`. Uses `curl_cffi` with a Chrome fingerprint because hdfcfund.com rejects plain HTTP clients. |
| Parse | `src/parser.py`: one parser per source type. Scheme pages: the page's JSON ([docs/field_map.md](docs/field_map.md)). KIMs: selected numbered sections. Factsheet: each scheme's fund-facts block. Guides: main article text. Returns, NAVs, risk ratios and holdings are skipped on purpose. |
| Chunk | `src/chunker.py`: section-aware chunks (see below) |
| Embed | `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions, runs locally via ONNX) |
| Store | ChromaDB, persisted in `data/chroma/` (162 chunks from 22 documents) |
| Retrieve | `src/retriever.py`: detects the scheme from its name or alias and filters to that scheme's documents; questions with no scheme search everything, including the general pages. Similarity cutoff 0.25. |
| Generate | `src/generator.py`: Groq LLM with a strict "answer only from context" prompt |
| Post-process | `src/postprocess.py`: 3-sentence cap, advice check, citation from chunk metadata (never from the LLM) |

### Chunking strategy

The sources are semi-structured: labelled facts, numbered KIM sections, and short articles. We use structure-aware chunks instead of fixed-size ones.

- **One "facts card" per scheme** from its scheme page, with the key fields as `Label: value` lines.
- **One chunk per section**: scheme-page sections (expense ratio, exit load, minimum investment, riskometer and benchmark, fund management, FAQs), KIM sections, the factsheet fund-facts block, and each guide article.
- **Long sections are split** by paragraph, then by sentence, into chunks of at most 200 tokens with a 30-token overlap. Every chunk stays under MiniLM's 256-token input limit.
- **Every chunk is prefixed** with `[<Document>] [<Section>]`, e.g. `[HDFC Small Cap Fund – Key Information Memorandum dated November 21, 2025] [Benchmark Index]`, and stores its scheme (or `General`), source type, source URL and fetch date.

To browse the stored chunks, run `python -m src.export_chunks`, which writes them to `data/chunks.md`.

### Guardrails (run before retrieval)

| Check | Result |
|---|---|
| **PII**: PAN, Aadhaar, phone, email, OTP, account or folio numbers | Blocked. The message is never sent to the LLM and is hidden in the chat. |
| **Performance**: returns, NAV, CAGR, "performed" | No numbers. The user gets the official HDFC MF factsheet link. |
| **Advice**: "should I", best or better, "good for me", recommend | Polite refusal plus a SEBI investor-education link |
| **Off-topic**: no scheme name and no mutual-fund terms | Scope message |
| **Scheme-specific question with no scheme named** ("What is the exit load?") | Asks which scheme. A definition question ("What is an exit load?") is answered from SEBI/AMFI instead. |
| **Another AMC named** (SBI, Axis…) | "Not found". It is never answered with HDFC data. |

## Setup

Requirements:
- Python 3.11 or newer (tested on 3.12);
- a Groq API key (free at [console.groq.com](https://console.groq.com)).

```bash
cd Mututal_fund_Chatbot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # then add your GROQ_API_KEY
python -m src.ingest --reset       # builds data/chroma from the saved snapshots
streamlit run app.py               # opens http://localhost:8501  (add ?theme=dark to start in dark mode)
```

Useful commands:

| Command | What it does |
|---|---|
| `python -m src.ingest --reset --fetch` | Re-download all 18 sources, then rebuild the vector store |
| `python -m src.retriever "exit load small cap"` | Show retrieved chunks and similarity scores |
| `python -m src.generator "…"` | Ask one question from the terminal |
| `python -m src.export_chunks` | Dump all stored chunks to `data/chunks.md` |
| `python -m scripts.eval_retrieval` | Retrieval eval (hit@1 / hit@4) |
| `python -m scripts.tune_threshold` | Similarity scores for in-scope and out-of-scope questions |
| `python -m scripts.make_sample_qa` | Regenerate `sample_qa.md` from live outputs |

### LLM

Answers are generated by **Groq** (`qwen/qwen3.8-27b` by default) in `src/generator.py`. Reasoning is turned off, and temperature is 0.

- **Key:** set `GROQ_API_KEY` in `.env`, which is gitignored (see `.env.example`). Get a key at [console.groq.com](https://console.groq.com).
- **Model:** set `GROQ_MODEL` in `.env` to use another model, e.g. `openai/gpt-oss-120b`.
- **Hosting:** on Streamlit Cloud, put `GROQ_API_KEY` under **Secrets**.

## Testing and evaluation

```bash
pytest                  # all 121 tests (~70 s; the PRD acceptance tests call Groq)
pytest -m "not llm"     # offline tests only
```

| Check | Result |
|---|---|
| PRD §10 acceptance: 10 factual questions across all 5 schemes | **Pass** (≥9/10 required). Every answer has 1 official citation and the "Last updated" line, and is at most 3 sentences |
| General questions (statements, riskometer, exit load, lock-in) | Each cites the right HDFC MF / SEBI / AMFI page |
| Advice / performance / PII / out-of-corpus / other-AMC / UI elements | All pass |
| No performance data in the corpus | Checked by a test over every chunk |
| Retrieval eval (21 labelled questions) | **hit@1 90%**, **hit@4 100%** |
| Similarity threshold | In-scope minimum 0.355 vs. out-of-scope maximum 0.238; cutoff 0.25 |

Sample outputs are in [sample_qa.md](sample_qa.md).

## Deliverables

| Deliverable | Location |
|---|---|
| Working prototype | `streamlit run app.py` (local). See the demo script below for the ≤3-min video. |
| Source list (18 official URLs) | [sources.md](sources.md), [sources.csv](sources.csv) |
| README | this file |
| Sample Q&A | [sample_qa.md](sample_qa.md) |
| Disclaimer snippet | [DISCLAIMER.md](DISCLAIMER.md) |

### Demo script (about 3 minutes)

| Time | Action | Shows |
|---|---|---|
| 0:00 | Open the app | Welcome line, example questions, disclaimer |
| 0:20 | Click "expense ratio of HDFC Flexi Cap Fund" | Cited answer from the HDFC scheme page, with its date |
| 0:40 | "What is the lock-in for tax saver fund?" | Alias handling |
| 1:00 | Click "How do I download my capital gains statement?" | Answer from an HDFC MF service page |
| 1:15 | "What is a riskometer?" | Definition from SEBI's investor site |
| 1:30 | "Should I buy HDFC Small Cap?" | Advice refusal with educational link |
| 1:45 | "Which gave better returns, large cap or flexi cap?" | Performance redirect to the official factsheet |
| 2:00 | "My PAN is ABCDE1234F, what's my balance?" | PII block, message hidden |
| 2:15 | "What is the exit load?" | Clarify prompt |
| 2:30 | Terminal: `python -m src.ingest --reset`, then open `data/chunks.md` | The RAG ingestion stages |

## Known limits

- **Point-in-time data.** Expense ratios, AUM and fund managers change. Answers reflect the snapshot date shown in each answer.
- **Sources can disagree because they have different dates.** The scheme page shows today's total TER, the factsheet shows the base expense ratio as on August 31, 2026, and the KIM shows FY 2024-25 actuals. Each chunk says which document and date it comes from, and the prompt prefers the scheme page.
- **Small corpus.** 18 sources, so many valid questions (e.g. stamp duty, registrar, taxation) return "not found".
- **Generic guides.** The capital-gains guide covers CAMS, KFintech and AMC websites in general. It isn't a step-by-step HDFC portal walkthrough.
- **Scraping is fragile.** hdfcfund.com blocks plain HTTP clients, and a site redesign could break the parser. The saved snapshots in `data/raw/` let you rebuild offline.
- **PDF text extraction is imperfect.** Some KIM words come out split (e.g. "lev ied"). The facts themselves are intact.
- **Guardrails are rule-based.** Cleverly phrased advice requests or unusual PII formats could slip through. The post-LLM advice scan is a second line of defence.
- **Needs a network connection and a Groq key.** Free-tier rate limits apply.
- English only.

## Project structure

```
app.py                 Streamlit UI (layout + state)
  src/ui.py            theme tokens (light/dark), CSS, HTML components
sources.csv / .md      corpus registry (18 official sources)
sample_qa.md           demo Q&A (real outputs)
DISCLAIMER.md          UI disclaimer snippet
src/
  config.py            paths, models, thresholds, env / secrets
  loader.py            fetch + snapshot pages and PDFs
  parser.py            scheme page / KIM / factsheet / guide → SourceDoc
  chunker.py           section-aware chunking
  embedder.py          MiniLM embeddings
  store.py             ChromaDB wrapper
  ingest.py            Load → Parse → Chunk → Embed → Store
  export_chunks.py     dump stored chunks to data/chunks.md
  schemes.py           scheme list and aliases, definition questions, other-AMC detection
  retriever.py         scheme-aware retrieval + threshold
  guardrails.py        PII / performance / advice / off-topic
  generator.py         Groq LLM call
  postprocess.py       answer contract + Response
  templates.py         fixed refusal / fallback text
  pipeline.py          answer(question) → Response
scripts/               eval_retrieval, tune_threshold, make_sample_qa
tests/                 121 tests (unit, routing, generator, PRD acceptance, UI)
data/raw/              source snapshots   data/chroma/  vector store
docs/                  PRD, architecture, implementation plan, field map
```

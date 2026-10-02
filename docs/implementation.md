# Implementation Plan: Mutual Fund FAQ Assistant

> **Update 2026-10-02 — corpus revision.** The revised brief asks for 15–25 official AMC/SEBI/AMFI pages and no third-party sources, so the five Groww pages were replaced by 18 official sources (HDFC MF scheme pages, KIMs, factsheet and statement guides; SEBI and AMFI investor-education pages). See [sources.md](../sources.md) and [field_map.md](field_map.md). Sections below that mention Groww describe the original build.

| | |
|---|---|
| **Status** | Implemented (see notes at the end) |
| **Date** | 2026-09-27 |
| **Based on** | [PRD.md](PRD.md), [architecture.md](architecture.md) |

This plan splits the build into **10 phases**. Each phase lists:
- its goal;
- the files it creates;
- the tasks, with code sketches;
- a **Done when** checklist.

Complete the phases in order, because each one builds on the previous. Every phase ends in something you can run and check.

---

## Phase map

| Phase | Name | Output | Architecture ref |
|---|---|---|---|
| 0 | Project setup | Repo skeleton, venv, config | §6, §9 |
| 1 | Source registry + loader | `data/raw/` snapshots | §3.1 |
| 2 | Parser | `SchemeDoc` per scheme | §3.2 |
| 3 | Chunker | Chunks with metadata | §3.3 |
| 4 | Embed + store (ingestion complete) | Populated ChromaDB | §3.4 |
| 5 | Scheme detection + retrieval | `retrieve()` returns ranked chunks | §4.2, §4.3 |
| 6 | Generation + post-processing | Grounded answers with citations (CLI) | §4.4, §4.5 |
| 7 | Guardrails | PII block, refusals, off-topic | §4.1 |
| 8 | Pipeline + Streamlit UI | Working chat app | §4.6, §5 |
| 9 | Testing, evaluation, deliverables, deploy | Tests, sample Q&A, README, hosted link | §8, §10 |

```
P0 → P1 → P2 → P3 → P4 ──► P5 → P6 → P8 → P9
                                 ▲
                           P7 ───┘   (P7 can be built in parallel with P5–P6)
```

---

## Phase 0: Project setup

**Goal:** an empty but runnable project structure with dependencies and config.

**Files:** `requirements.txt`, `.env.example`, `.gitignore`, `src/__init__.py`, `src/config.py`, the empty `data/raw/` and `data/chroma/` folders, and `tests/`.

### Tasks
1. Create the virtual environment:
   ```bash
   python3.11 -m venv .venv && source .venv/bin/activate
   ```
2. `requirements.txt`:
   ```
   requests
   beautifulsoup4
   lxml
   sentence-transformers
   chromadb
   streamlit
   python-dotenv
   pytest
   # LLM SDK: add the one you choose, e.g. anthropic / openai / google-genai / groq
   ```
3. `.gitignore`: `.venv/`, `.env`, `__pycache__/`. Do **not** ignore `data/chroma/` if you plan to host on Streamlit Cloud.
4. `.env.example`:
   ```
   LLM_PROVIDER=
   LLM_MODEL=
   LLM_API_KEY=
   ```
5. `src/config.py`, which loads `.env` and exposes constants:
   ```python
   from pathlib import Path
   import os
   from dotenv import load_dotenv

   load_dotenv()
   ROOT = Path(__file__).resolve().parent.parent
   RAW_DIR = ROOT / "data" / "raw"
   CHROMA_PATH = ROOT / "data" / "chroma"
   SOURCES_CSV = ROOT / "sources.csv"

   EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
   COLLECTION = "hdfc_mf_faq"
   TOP_K = int(os.getenv("TOP_K", 4))
   SIM_THRESHOLD = float(os.getenv("SIM_THRESHOLD", 0.35))
   CHUNK_TOKENS, CHUNK_OVERLAP = 200, 30

   LLM_PROVIDER = os.getenv("LLM_PROVIDER", "")
   LLM_MODEL = os.getenv("LLM_MODEL", "")
   LLM_API_KEY = os.getenv("LLM_API_KEY", "")
   USE_LLM_INTENT = os.getenv("USE_LLM_INTENT", "false").lower() == "true"
   ```

### Done when
- [ ] `pip install -r requirements.txt` succeeds.
- [ ] `python -c "import src.config"` runs without errors.
- [ ] The folder layout matches architecture §9.

---

## Phase 1: Source registry and loader

**Goal:** fetch the 5 pages once and save raw snapshots, so later phases never need the network.

**Files:** `sources.csv`, `src/loader.py`

### Tasks
1. `sources.csv`:
   ```csv
   slug,scheme,category,source_type,url
   hdfc-large-cap,HDFC Large Cap Fund,Large Cap,scheme_page,https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
   hdfc-flexi-cap,HDFC Flexi Cap Fund,Flexi Cap,scheme_page,https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
   hdfc-elss,HDFC ELSS Tax Saver Fund,ELSS,scheme_page,https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
   hdfc-small-cap,HDFC Small Cap Fund,Small Cap,scheme_page,https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth
   hdfc-baf,HDFC Balanced Advantage Fund,Balanced Advantage,scheme_page,https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth
   ```
   Optional rows, if the PRD open questions are resolved:
   - `statement_guide` rows, for example a CAMS or HDFC MF statement page;
   - `education` rows, for example an AMFI investor-education page.
2. `src/loader.py`:
   - `load_sources() -> list[dict]` reads the CSV.
   - `fetch(url) -> str` uses `requests` with a browser User-Agent, `timeout=15`, and 3 retries with exponential backoff.
   - `extract_next_data(html) -> dict | None` uses BeautifulSoup to find `script#__NEXT_DATA__` and runs `json.loads` on it.
   - `snapshot(source)` writes three files:

     | File | Contents |
     |---|---|
     | `data/raw/{slug}.html` | The full page HTML |
     | `data/raw/{slug}.json` | The `__NEXT_DATA__` JSON, if present |
     | `data/raw/{slug}.meta.json` | `{"url", "fetched_at": date.today().isoformat(), "status"}` |

   - `main()` loops over the sources, snapshots each one, and prints a summary table.
3. **Fallback:** if a page has neither useful HTML text nor JSON, fetch it with Playwright (`pip install playwright && playwright install chromium`). Only add this if you actually need it.
4. **Manual inspection (important):** open each `data/raw/{slug}.json` and find the key paths for expense ratio, exit load, min SIP, lock-in, riskometer, benchmark, fund manager, AUM and launch date. Write them down, because Phase 2 needs them.

### Run
```bash
python -m src.loader
```

### Done when
- [ ] 5 `.html` files and 5 `.meta.json` files exist in `data/raw/`, plus a `.json` file wherever the page has `__NEXT_DATA__`.
- [ ] You've written down the JSON key paths for every target field.
- [ ] Re-running overwrites the snapshots cleanly.

---

## Phase 2: Parser

**Goal:** turn each raw snapshot into a clean, structured `SchemeDoc`.

**Files:** `src/parser.py`

### Tasks
1. Define the dataclass (architecture §3.2):
   ```python
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
   ```
2. `FIELD_PATHS`: a dict mapping each field name to the JSON key path you found in Phase 1:
   ```python
   FIELD_PATHS = {
       "expense_ratio": ["props", "pageProps", "...", "expense_ratio"],  # fill from inspection
       "exit_load": [...],
       "min_sip": [...],
       ...
   }
   ```
   Write a helper `get_path(d, path)` that returns `None` when a key is missing.
3. `parse_fields(json, html) -> dict`:
   - Try the JSON path first.
   - If that fails, fall back to a regex or label search in the HTML text. For example, find the text "Expense ratio" and read the value next to it.
4. `parse_sections(json, html) -> dict`: pull out the prose blocks (investment objective, fund manager bio, tax implications, exit load details, and any FAQs on the page).
5. **Clean the text:**
   - collapse whitespace;
   - strip navigation, footer and cookie text;
   - keep values **exactly as written** (`0.67%`, `₹100`), with no rounding.
6. **Skip return data on purpose.** Do not copy fields like 1Y, 3Y or 5Y returns or NAV history into `fields` or `sections`. This enforces PRD GR-2 at the data level.
7. `parse_all() -> list[SchemeDoc]`, plus a `__main__` that pretty-prints each doc.

### Run
```bash
python -m src.parser
```

### Done when
- [ ] All 5 schemes have their core fields filled: `expense_ratio`, `exit_load`, `min_sip`, `riskometer`, `benchmark`.
- [ ] ELSS has a `lock_in` value (3 years).
- [ ] You've spot-checked 3 values against the live page by hand, and they match exactly.
- [ ] No return or performance numbers appear in the output.

---

## Phase 3: Chunker

**Goal:** section-aware chunks with a context prefix and full metadata (architecture §3.3).

**Files:** `src/chunker.py`, `tests/test_chunker.py`

### Tasks
1. Load the MiniLM tokenizer, which comes with `sentence-transformers`, to count tokens:
   ```python
   from transformers import AutoTokenizer
   tok = AutoTokenizer.from_pretrained(EMBED_MODEL)
   def n_tokens(text): return len(tok.encode(text, add_special_tokens=False))
   ```
2. Define the chunk dataclass:
   ```python
   @dataclass
   class Chunk:
       id: str
       text: str
       metadata: dict
   ```
3. `make_facts_card(doc) -> Chunk`:
   - Build `Label: value` lines from `doc.fields`, skipping empty values.
   - Add the prefix `[<Scheme> – Direct Growth] [Key Facts]`.
   - Use the ID `{slug}:key-facts:0` and set `chunk_type="facts_card"`.
4. `split_section(title, text) -> list[str]`:
   - If the prefix plus the text is ≤ 200 tokens, return a single chunk.
   - Otherwise split by paragraph, then by sentence, and greedily pack pieces up to 200 tokens with a 30-token overlap.
5. `chunk_doc(doc) -> list[Chunk]` returns the facts card plus the section chunks.
   - IDs: `{slug}:{slugify(section)}:{n}`.
   - Metadata on every chunk:

     | Key | Source |
     |---|---|
     | `scheme`, `category` | from the doc |
     | `section` | the section title |
     | `chunk_type` | `facts_card` or `section` |
     | `source_url`, `source_type` | from the doc |
     | `fetched_at` | the snapshot date |

6. Unit tests:
   - Every chunk is ≤ 256 tokens.
   - Every chunk starts with the `[<Scheme>` prefix.
   - Each scheme has exactly one facts card.
   - IDs are unique and deterministic: running twice gives the same IDs.

### Run
```bash
python -m src.chunker   # prints chunk count per scheme + a few samples
pytest tests/test_chunker.py
```

### Done when
- [ ] The tests pass.
- [ ] The total is roughly 30–80 chunks.
- [ ] A printed facts card is readable and correct.

---

## Phase 4: Embed and store (ingestion complete)

**Goal:** a persisted ChromaDB collection holding every chunk, rebuilt with one command.

**Files:** `src/embedder.py`, `src/store.py`, `src/ingest.py`

### Tasks
1. `src/embedder.py`:
   ```python
   from functools import lru_cache
   from sentence_transformers import SentenceTransformer

   @lru_cache
   def get_model():
       return SentenceTransformer(EMBED_MODEL)

   def embed(texts: list[str]) -> list[list[float]]:
       return get_model().encode(texts, normalize_embeddings=True).tolist()
   ```
2. `src/store.py`:
   ```python
   import chromadb

   def get_collection(reset=False):
       client = chromadb.PersistentClient(path=str(CHROMA_PATH))
       if reset:
           try: client.delete_collection(COLLECTION)
           except Exception: pass
       return client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

   def upsert(chunks, vectors): ...
   def query(vector, k, where=None): ...   # returns ids, documents, metadatas, distances
   ```
   Chroma returns cosine **distance**. Convert it with `similarity = 1 - distance`.
3. `src/ingest.py` runs the whole ingestion:
   ```python
   def main(reset=True, fetch=False):
       if fetch: loader.main()
       docs = parser.parse_all()
       chunks = [c for d in docs for c in chunker.chunk_doc(d)]
       vectors = embedder.embed([c.text for c in chunks])
       store.upsert(chunks, vectors)   # after get_collection(reset=reset)
       print(f"Ingested {len(chunks)} chunks from {len(docs)} sources")
   ```
   Add CLI flags with `argparse`: `--fetch` re-downloads the pages, and `--reset` rebuilds the collection.
4. **Sanity script.** Embed "exit load small cap" and print the top 4 results. The Small Cap facts card should rank first.

### Run
```bash
python -m src.ingest --reset          # from snapshots
python -m src.ingest --reset --fetch  # re-download first
```

### Done when
- [ ] `data/chroma/` exists and `collection.count()` equals the number of chunks.
- [ ] Re-running doesn't create duplicates.
- [ ] The sanity query returns the correct scheme first.

**Milestone: the ingestion side of RAG (Load → Chunk → Embed → Store) is complete.**

---

## Phase 5: Scheme detection and retrieval

**Goal:** `retrieve(question)` returns the right chunks for the right scheme, or signals not-found or clarify.

**Files:** `src/schemes.py`, `src/retriever.py`

### Tasks
1. `src/schemes.py`:
   - `SCHEME_ALIASES`: the dict from architecture §4.2, mapping each canonical scheme to a list of aliases.
   - `detect_schemes(question) -> list[str]`: lowercase the question and match aliases on word boundaries. Check longer aliases first so "small cap" wins over "cap".
   - `SCHEME_SPECIFIC_TERMS = {"expense ratio", "exit load", "sip", "lumpsum", "riskometer", "benchmark", "aum", "fund manager", "nav"}`
   - `needs_scheme(question) -> bool`: true if the question contains a scheme-specific term.
2. `src/retriever.py`:
   ```python
   @dataclass
   class RetrievalResult:
       status: Literal["ok", "not_found", "clarify"]
       chunks: list[dict]       # {text, metadata, similarity}

   def retrieve(question: str) -> RetrievalResult:
       schemes = detect_schemes(question)
       if not schemes and needs_scheme(question):
           return RetrievalResult("clarify", [])
       vec = embed([question])[0]
       if len(schemes) == 1:
           hits = query(vec, TOP_K, where={"scheme": schemes[0]})
       elif len(schemes) > 1:
           hits = merge(query(vec, 2, where={"scheme": s}) for s in schemes)
       else:
           hits = query(vec, TOP_K)
       if not hits or hits[0].similarity < SIM_THRESHOLD:
           return RetrievalResult("not_found", hits)
       return RetrievalResult("ok", hits)
   ```
3. Write a small debug CLI: `python -m src.retriever "exit load of hdfc small cap"` prints the status and the ranked chunks with their similarity scores.
4. **Tune `SIM_THRESHOLD`:**
   - Run about 10 in-scope questions and 5 out-of-scope ones, such as "What is the NAV of SBI Bluechip?".
   - Print the top-1 similarity for each.
   - Set the threshold between the two groups.

### Done when
- [ ] Each of the 5 schemes resolves correctly from its common aliases.
- [ ] "What is the expense ratio?" with no scheme returns `clarify`.
- [ ] An out-of-scope question returns `not_found`.
- [ ] In-scope field questions return the right facts card at rank 1.

---

## Phase 6: Generation and post-processing

**Goal:** grounded answers of 3 sentences or fewer, with one citation and a freshness line, working from the CLI.

**Files:** `src/generator.py`, `src/postprocess.py`, `src/templates.py`

### Tasks
1. `src/generator.py`:
   - A thin provider interface: `complete(system: str, user: str) -> str`, with one implementation for your chosen SDK, selected by `LLM_PROVIDER`. Use `temperature=0` and `max_tokens=150`.
   - `SYSTEM_PROMPT`: copy it verbatim from architecture §4.4.
   - `build_user_prompt(chunks, question)`: context blocks joined with `---`, then the question.
   - `generate(question, chunks) -> str`: returns the raw LLM text, or the literal `NOT_FOUND`.
2. `src/templates.py` holds the fixed strings:
   ```python
   NOT_FOUND = "I couldn't find that in my sources. You can check the scheme page for more details."
   CLARIFY   = "Which scheme do you mean? I cover: HDFC Large Cap, Flexi Cap, ELSS Tax Saver, Small Cap, and Balanced Advantage."
   ADVICE    = "I can only share factual information about these schemes and can't give investment advice. To learn how to evaluate mutual funds, see the link below."
   PERFORMANCE = "I don't compute or compare returns. Please refer to the official factsheet for performance data."
   PII_BLOCK = "Please don't share personal information like PAN, Aadhaar, account numbers, OTPs, email or phone. I haven't stored your message."
   OFF_TOPIC = "I can only answer factual questions about 5 HDFC Mutual Fund schemes."
   EDU_LINK  = "<AMFI investor education URL>"      # or fallback to a scheme page
   ```
3. `src/postprocess.py`:
   - `cap_sentences(text, n=3)` uses a regex sentence split. Be careful not to split on decimals like "0.67%".
   - `contains_advice(text) -> bool` checks for phrases like "you should", "recommend", "better option", "good investment" and "ideal for".
   - `finalize(raw, chunks) -> Response`:
     1. If `raw.strip() == "NOT_FOUND"`, return a `not_found` response citing the relevant scheme page.
     2. If `contains_advice(raw)`, return an `advice` response.
     3. Otherwise cap the text at 3 sentences, set `citation_url` to `chunks[0].metadata.source_url` and `last_updated` to `chunks[0].metadata.fetched_at`.
4. `Response` dataclass (architecture §4.6), with a `render()` method:
   ```
   <text>
   Source: <url>
   Last updated from sources: <date>
   ```
5. Temporary CLI: `python -m src.generator "What is the exit load of HDFC Small Cap?"`.

### Done when
- [ ] Five factual questions return correct answers of 3 sentences or fewer, each with a link and a date.
- [ ] Numbers match the facts card exactly.
- [ ] A question the context can't answer yields `NOT_FOUND` and then the template.
- [ ] Citation URLs always come from metadata, never from LLM output.

**Milestone: the retrieval side of RAG (Retrieve → Generate) is complete.**

---

## Phase 7: Guardrails

**Goal:** deterministic PII blocking and intent routing that runs before retrieval (architecture §4.1).

**Files:** `src/guardrails.py`, `tests/test_guardrails.py`

### Tasks
1. PII regexes, compiled with `re.IGNORECASE` where needed:
   ```python
   PII_PATTERNS = {
       "pan":     r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
       "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
       "phone":   r"\b(?:\+91[\-\s]?)?[6-9]\d{9}\b",
       "email":   r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",
       "otp":     r"\botp\b.{0,15}\b\d{4,6}\b",
       "account": r"\b\d{9,18}\b",
   }
   def contains_pii(text) -> bool
   ```
   Watch for false positives. "₹100" and "0.67%" must **not** match. The account regex requires 9 or more digits, so short amounts are safe.
2. Intent classifier:
   ```python
   PERFORMANCE_PAT = r"\b(returns?|cagr|performance|performed|nav growth|top performing|gave better)\b"
   ADVICE_PAT      = r"\b(should i|buy|sell|switch|best|better|recommend|worth it|good for me|which fund|invest in)\b"
   MF_VOCAB        = {"fund","scheme","sip","nav","expense","exit load","elss","lock-in","riskometer",
                      "benchmark","statement","capital gains","folio","aum","mutual"}

   def classify(text) -> Literal["pii","performance","advice","off_topic","fact"]:
       if contains_pii(text): return "pii"
       if re.search(PERFORMANCE_PAT, text, re.I): return "performance"
       if re.search(ADVICE_PAT, text, re.I): return "advice"
       if not detect_schemes(text) and not any(v in text.lower() for v in MF_VOCAB): return "off_topic"
       return "fact"
   ```
   Performance is checked before advice, so "Which fund gave better returns?" routes to the factsheet link.
3. Optional: an LLM intent classifier behind `USE_LLM_INTENT`. Skip this for the demo.
4. **Logging rule:** the guardrails module never logs raw input. If you log anything, log only the `kind`.
5. Tests. Each input should route as follows:

   | Input | Expected |
   |---|---|
   | "My PAN is ABCDE1234F" | `pii` |
   | "call me on 9876543210" | `pii` |
   | "Minimum SIP is ₹100?" | `fact` (not PII) |
   | "Should I buy HDFC Small Cap?" | `advice` |
   | "Which is better, flexi cap or large cap?" | `advice` |
   | "What were the 3 year returns of ELSS?" | `performance` |
   | "What's the weather today?" | `off_topic` |
   | "Exit load of HDFC Flexi Cap?" | `fact` |
   | "How do I download my capital gains statement?" | `fact` |

### Run
```bash
pytest tests/test_guardrails.py -v
```

### Done when
- [ ] All the guardrail tests pass.
- [ ] No false PII positives on fund amounts or percentages.

---

## Phase 8: Pipeline and Streamlit UI

**Goal:** one `answer()` entry point, and a chat UI that meets PRD §6.3.

**Files:** `src/pipeline.py`, `app.py`

### Tasks
1. `src/pipeline.py`:
   ```python
   def answer(question: str) -> Response:
       kind = classify(question)
       if kind == "pii":         return Response("pii_block", PII_BLOCK, None, None)
       if kind == "performance": return Response("performance", PERFORMANCE, factsheet_url(question), today_src_date())
       if kind == "advice":      return Response("advice", ADVICE, EDU_LINK, None)
       if kind == "off_topic":   return Response("off_topic", OFF_TOPIC, None, None)

       r = retrieve(question)
       if r.status == "clarify":   return Response("clarify", CLARIFY, None, None)
       if r.status == "not_found": return Response("not_found", NOT_FOUND, fallback_url(question), ...)
       raw = generate(question, r.chunks)
       return finalize(raw, r.chunks)
   ```
   - `factsheet_url(question)` returns the detected scheme's source URL, or a general page if no scheme was detected.
   - Wrap the LLM call in `try/except`. On failure, return a friendly "Service temporarily unavailable" message and don't crash.
2. `app.py`:
   ```python
   import streamlit as st
   from src.pipeline import answer

   st.set_page_config(page_title="HDFC MF Facts Assistant", page_icon="📊")
   st.title("HDFC MF Facts Assistant")
   st.write("Hi! Ask me facts about 5 HDFC Mutual Fund schemes.")
   st.info("Facts-only. No investment advice.")

   EXAMPLES = ["What is the expense ratio of HDFC Flexi Cap Fund?",
               "What is the lock-in period for HDFC ELSS Tax Saver Fund?",
               "What is the exit load on HDFC Small Cap Fund?"]

   if "history" not in st.session_state: st.session_state.history = []
   cols = st.columns(3)
   clicked = next((q for c, q in zip(cols, EXAMPLES) if c.button(q)), None)
   question = st.chat_input("Ask a factual question…") or clicked

   if question:
       st.session_state.history.append(("user", question, None))
       st.session_state.history.append(("assistant", answer(question), None))

   for role, content, _ in st.session_state.history:
       with st.chat_message(role):
           if role == "user": st.write(content)
           else:
               st.write(content.text)
               if content.citation_url: st.markdown(f"🔗 [Source]({content.citation_url})")
               if content.last_updated: st.caption(f"Last updated from sources: {content.last_updated}")
   ```
   - **PII:** for a `pii_block` answer, store `"[message hidden: contained personal data]"` in the history instead of the user's text.
   - **Caching:** wrap the model and collection loaders with `@st.cache_resource` so they load once.
   - **Sidebar:** the 5 schemes in scope, the disclaimer snippet, and a "Clear chat" button.

### Run
```bash
streamlit run app.py
```

### Done when
- [ ] The welcome line, 3 example buttons and the disclaimer are visible.
- [ ] The example buttons produce correct cited answers.
- [ ] Refusal, PII, not-found and clarify replies all render cleanly.
- [ ] A PII message isn't shown back in the history.
- [ ] The first answer arrives in under 5 s after the app has warmed up.

---

## Phase 9: Testing, evaluation, deliverables, deploy

**Goal:** prove the system meets PRD §10 and package everything for submission.

**Files:** `tests/test_pipeline.py`, `sample_qa.md`, `sources.md`, `README.md`, and the deployment config.

### Tasks
1. **Acceptance tests** in `tests/test_pipeline.py`, one test per PRD §10 row:
   - factual questions return an `answer` with exactly 1 URL and a `last_updated`, and have ≤ 3 sentences;
   - "Should I buy…" returns `advice`, and the text contains no opinion;
   - "Which fund gave better returns?" returns `performance`, and the citation is a scheme page;
   - PAN input returns `pii_block`;
   - an out-of-corpus question returns `not_found`.
2. **Retrieval eval script** (`scripts/eval_retrieval.py`, optional):
   - about 15 questions, each labelled with its expected `(scheme, section)`;
   - report hit@1 and hit@4, aiming for hit@1 ≥ 80%.
3. **`sample_qa.md`**: run 8–10 queries through `answer()` and paste in the real outputs.
   - Include 5–6 facts, spread across all schemes.
   - Include 1 advice refusal, 1 performance redirect, 1 PII block and 1 not-found.
   - A small script can generate this file automatically.
4. **`sources.md`**: a table of the 5 URLs with scheme, category and fetched date. Add any optional official pages if you used them.
5. **`README.md`** sections:
   - Overview
   - Scope (AMC and the 5 schemes)
   - Architecture diagram (link to `docs/architecture.md`)
   - Setup:

     ```bash
     git clone … && cd …
     python3.11 -m venv .venv && source .venv/bin/activate
     pip install -r requirements.txt
     cp .env.example .env   # add LLM key
     python -m src.ingest --reset
     streamlit run app.py
     ```

   - Chunking strategy summary
   - Guardrails
   - Known limits (PRD §11)
   - Disclaimer snippet
6. **Deploy to Streamlit Community Cloud:**
   - Push the repo to GitHub, including `data/chroma/` and `data/raw/`.
   - Create the app, pointing it at `app.py`.
   - Add `LLM_PROVIDER`, `LLM_MODEL` and `LLM_API_KEY` under **Secrets**. Make `config.py` fall back to `st.secrets` if env vars are missing.
   - Test the public URL with the full demo script.
7. **Fallback deliverable:** record a demo video of 3 minutes or less:
   1. welcome screen;
   2. 3 factual questions;
   3. advice refusal;
   4. PII block;
   5. a quick look at the ingestion command and chunk count.

### Done when
- [ ] `pytest` is green.
- [ ] `sample_qa.md` contains real outputs.
- [ ] The README lets a fresh clone run end to end.
- [ ] The hosted link works, or the video is recorded.
- [ ] Every item in PRD §9 is submitted.

---

## Appendix A: Demo script (about 3 minutes)

| Time | Action | Shows |
|---|---|---|
| 0:00 | Open the app | Welcome line, examples, disclaimer |
| 0:20 | Click "Expense ratio of HDFC Flexi Cap?" | Cited answer and date |
| 0:40 | "What is the lock-in for ELSS?" | Alias handling |
| 1:00 | "Minimum SIP for HDFC Balanced Advantage?" | Hybrid scheme coverage |
| 1:20 | "Should I buy HDFC Small Cap?" | Advice refusal and educational link |
| 1:40 | "Which gave better returns, large cap or flexi cap?" | Performance redirect to the factsheet |
| 2:00 | "My PAN is ABCDE1234F, what's my balance?" | PII block, message hidden |
| 2:20 | "What is the exit load?" | Clarify prompt |
| 2:40 | Terminal: `python -m src.ingest --reset` | The RAG ingestion stages |

## Appendix B: Common pitfalls

| Pitfall | Fix |
|---|---|
| Groww HTML is mostly empty | Parse `__NEXT_DATA__` JSON; use Playwright only as a last resort |
| Chunks silently truncated | Keep chunks ≤ 200 tokens using the MiniLM tokenizer, not word counts |
| Wrong scheme answered | Always apply the `where={"scheme": …}` filter when a scheme is detected |
| Sentence splitter breaks "0.67%" | Split only on `[.!?]` followed by whitespace and a capital letter |
| PII regex flags amounts | Require 9 or more digits for accounts; test with ₹ values |
| Chroma distance vs similarity confusion | Cosine space: `similarity = 1 - distance` |
| Model downloads on every Streamlit rerun | Use `@st.cache_resource` |
| Stale answers after re-scraping | Always run `ingest --reset` after `--fetch` |

---

## Implementation notes (what changed during the build)

These are the places where the build departed from the plan above, and why.

| Phase | Change | Why |
|---|---|---|
| 0 | Python 3.12 instead of 3.11 | 3.11 isn't installed on the dev machine. The plan says 3.11+. |
| 1–2 | Riskometer comes from `return_stats[0].risk`, fund managers from `fund_manager_details` | `nfo_risk` is stale ("Moderately High" vs. "Very High" on the page), and `fund_manager` lists only one name. See [field_map.md](field_map.md). |
| 2 | Sections are generated from JSON fields. There's no "FAQs" section. | The page's "About" prose mixes AMC-level figures (AMC AUM, AMC incorporation date) into the fund description |
| 4 | `--reset` wipes `data/chroma/` instead of calling `delete_collection()` | Chroma left an orphaned index folder behind on every reset |
| 5 | `SIM_THRESHOLD` changed from 0.35 to **0.25** | In-scope questions scored as low as 0.280 ("ELSS lock-in?"); out-of-scope questions topped out at 0.197 |
| 5 | Added an other-AMC check; "bluechip" is not an alias | Stops "Axis Small Cap" or "SBI Bluechip" from being answered with HDFC data |
| 6 | LLM is **Groq** (`qwen/qwen3.8-27b`, reasoning off). Claude (CLI and API) was used first, then removed. | Free, fast (~0.2 s per answer), works when hosted, and passes the PRD acceptance tests. A local model (qwen3-vl) was tried first and returned empty answers because it spent its output budget reasoning. |
| 6 | Prompt rule added: "State the fact directly. Do not mention the context…" | Answers were saying "as stated in the Key Facts section" |
| 7 | Advice patterns are phrase-based ("sell now", "should I buy"), not bare "buy" / "sell" / "which fund" | "What is the exit load if I redeem…" and "Which fund has a lock-in?" are factual questions |
| 8–9 | A "not found" reply with no scheme named links hdfcfund.com | Citing the top chunk's scheme page there was arbitrary |
| 9 | Hosting on Streamlit Cloud is not done. The code reads `st.secrets` so it's ready once `GROQ_API_KEY` is added. | The subscription backend can't run on a hosted server |

"""Phase 6: grounded answer generation with Groq.

Needs GROQ_API_KEY in .env (https://console.groq.com). Model: GROQ_MODEL, default qwen/qwen3.8-27b.

    python -m src.generator "What is the exit load of HDFC Small Cap Fund?"
"""
import sys

import groq

from src.config import GROQ_API_KEY, GROQ_MODEL

SYSTEM_PROMPT = """You are a facts-only assistant for 5 HDFC Mutual Fund schemes.
Rules:
- Answer ONLY using the CONTEXT. If the answer is not in the context, reply exactly: NOT_FOUND
- At most 3 sentences. Quote numbers exactly as written in the context.
- Never give investment advice, opinions, recommendations, or return comparisons.
- Do not include URLs; the system adds the citation.
- State the fact directly. Do not mention the context, its sections, or where the information came from."""


class GenerationError(RuntimeError):
    pass


def build_user_prompt(chunks: list[dict], question: str) -> str:
    context = "\n---\n".join(c["text"] for c in chunks)
    return f"CONTEXT:\n{context}\n\nQUESTION: {question}"


def complete(system: str, user: str) -> str:
    if not GROQ_API_KEY:
        raise GenerationError("No Groq API key found (set GROQ_API_KEY in .env)")

    # Qwen3 and gpt-oss reason before answering; keep that off/low so the answer comes back fast.
    extra = ({"reasoning_effort": "none"} if GROQ_MODEL.startswith("qwen/") else
             {"reasoning_effort": "low", "include_reasoning": False} if GROQ_MODEL.startswith("openai/gpt-oss") else {})
    try:
        r = groq.Groq(api_key=GROQ_API_KEY, timeout=30).chat.completions.create(
            model=GROQ_MODEL,
            temperature=0,
            max_completion_tokens=512,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            **extra,
        )
    except groq.AuthenticationError as e:
        raise GenerationError("Invalid Groq API key (check GROQ_API_KEY in .env)") from e
    except groq.APIConnectionError as e:
        raise GenerationError(f"Groq connection error: {e}") from e
    except groq.APIStatusError as e:
        raise GenerationError(f"Groq API error {e.status_code}: {e.message}") from e
    return r.choices[0].message.content or ""


def generate(question: str, chunks: list[dict]) -> str:
    """Return raw LLM text (or the literal NOT_FOUND)."""
    return complete(SYSTEM_PROMPT, build_user_prompt(chunks, question))


def main() -> None:
    # Developer CLI: retrieve + generate for one question (no guardrails; the app uses src.pipeline).
    from src import templates
    from src.postprocess import Response, finalize
    from src.retriever import retrieve

    q = " ".join(sys.argv[1:]) or "What is the exit load of HDFC Small Cap Fund?"
    r = retrieve(q)
    if r.status == "clarify":
        resp = Response("clarify", templates.CLARIFY)
    elif r.status == "not_found":
        top = r.chunks[0]["metadata"] if r.chunks else {}
        resp = Response("not_found", templates.NOT_FOUND, top.get("source_url"), top.get("fetched_at"))
    else:
        try:
            resp = finalize(generate(q, r.chunks), r.chunks)
        except GenerationError as e:
            print(f"[generation error] {e}", file=sys.stderr)
            resp = Response("error", templates.SERVICE_ERROR)
    print(f"Q: {q}\n[{resp.kind}]\n{resp.render()}")


if __name__ == "__main__":
    main()

"""Streamlit chat UI.   streamlit run app.py"""
import streamlit as st

from src import ui
from src.embedder import embed
from src.guardrails import contains_pii
from src.pipeline import answer, scheme_sources
from src.store import get_collection

st.set_page_config(page_title="HDFC MF Facts Assistant", page_icon="🛡️", layout="wide")

EXAMPLES = [
    ("What is the expense ratio of HDFC Flexi Cap Fund?", ":material/percent:"),
    ("What is the lock-in period for HDFC ELSS Tax Saver Fund?", ":material/lock_clock:"),
    ("What is the exit load on HDFC Small Cap Fund?", ":material/logout:"),
    ("How do I download my capital gains statement?", ":material/receipt_long:"),
]
PII_PLACEHOLDER = "Message hidden — it contained personal data"


@st.cache_resource(show_spinner="Loading knowledge base…")
def warm_up():
    """Load the embedding model and vector store once per server process."""
    embed(["warm up"])  # forces the ONNX model to download/load now, not on the first question
    return get_collection().count()


def ask(question: str) -> None:
    if question and question.strip():
        st.session_state.pending = question.strip()


def on_submit() -> None:
    ask(st.session_state.get("q_input", ""))


def new_chat() -> None:
    st.session_state.history = []
    st.session_state.pending = None


# ---- State ----
st.session_state.setdefault("history", [])   # [(role, str | Response)] — session only, never persisted
st.session_state.setdefault("pending", None)
st.session_state.setdefault("dark", st.query_params.get("theme") == "dark")

theme = "dark" if st.session_state.dark else "light"
st.markdown(ui.css(theme), unsafe_allow_html=True)
warm_up()

# ---- Top bar ----
with st.container(key="topbar"):
    brand_col, schemes_col, _, toggle_col, new_col = st.columns([2.6, 2.6, 0.6, 1.5, 1.3],
                                                                vertical_alignment="center")
    brand_col.markdown(ui.brand(), unsafe_allow_html=True)
    with schemes_col:
        with st.popover("5 schemes covered", icon=":material/account_balance:"):
            st.markdown("**Schemes covered** (Direct – Growth)")
            for scheme, src in scheme_sources().items():
                st.markdown(f"- [{scheme}]({src['url']})")
            st.caption("Answers come only from official HDFC Mutual Fund pages, KIMs and factsheet, "
                       "plus SEBI and AMFI investor-education pages ([full source list]"
                       "(https://github.com/sanchaybagul/mutual-fund-faq-chatbot/blob/main/sources.md)).")
    with toggle_col:
        with st.container(key="theme_toggle"):
            st.toggle("Dark mode", key="dark")
    with new_col:
        st.button("New chat", icon=":material/add:", key="new_chat", on_click=new_chat)

chatting = bool(st.session_state.history or st.session_state.pending)

# ---- Hero (empty state) ----
if not chatting:
    st.markdown(ui.hero(), unsafe_allow_html=True)

# ---- Thread ----
if chatting:
    thread = "".join(ui.user_message(c, hidden=(c == PII_PLACEHOLDER)) if role == "user" else ui.bot_message(c)
                     for role, c in st.session_state.history)
    st.markdown(f'<div class="thread">{thread}</div>', unsafe_allow_html=True)

    if st.session_state.pending:
        q = st.session_state.pending
        shown = PII_PLACEHOLDER if contains_pii(q) else q   # never echo personal data, even briefly
        st.markdown(f'<div class="thread">{ui.user_message(shown, hidden=shown == PII_PLACEHOLDER)}</div>',
                    unsafe_allow_html=True)
        with st.spinner("Checking the sources…"):
            resp = answer(q)
        st.session_state.history += [("user", shown), ("assistant", resp)]
        st.session_state.pending = None
        st.rerun()

# ---- Ask card ----
with st.form("ask", clear_on_submit=True, border=False):
    q_col, send_col = st.columns([12, 1], vertical_alignment="center")
    q_col.text_input("Question", key="q_input", label_visibility="collapsed",
                    placeholder="Ask about expense ratio, exit load, minimum SIP, lock-in, riskometer…")
    with send_col:
        st.form_submit_button("↑", on_click=on_submit, help="Ask")
st.markdown(ui.disclaimer(), unsafe_allow_html=True)

# ---- Example cards (empty state) ----
if not chatting:
    st.markdown('<div class="section-label">Get started with an example below</div>', unsafe_allow_html=True)
    for i, (col, (q, ic)) in enumerate(zip(st.columns(4), EXAMPLES)):
        with col:
            st.button(q, icon=ic, key=f"ex_{i}", on_click=ask, args=(q,), use_container_width=True)

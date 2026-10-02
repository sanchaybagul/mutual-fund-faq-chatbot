"""Look and feel for the Streamlit app: theme tokens, CSS, and small HTML helpers.

Palette: deep navy + trust blue (stability, trust), emerald (verified facts),
a touch of gold (strength) in the brand mark.
"""
import html
from urllib.parse import urlparse

THEMES = {
    "light": {
        "bg": "#F4F6FA", "bg_glow": "rgba(31, 79, 209, 0.07)", "surface": "#FFFFFF",
        "surface_2": "#F7F9FC", "border": "#E2E7EF", "border_strong": "#CBD4E1",
        "text": "#0B1B33", "muted": "#5A6A82", "faint": "#8A98AD",
        "primary": "#0B2A5B", "primary_text": "#FFFFFF", "accent": "#1F4FD1",
        "accent_soft": "rgba(31, 79, 209, 0.08)", "emerald": "#0E8F6F",
        "emerald_soft": "rgba(14, 143, 111, 0.10)", "amber": "#B7791F",
        "amber_soft": "rgba(183, 121, 31, 0.10)", "red": "#C2413B", "red_soft": "rgba(194, 65, 59, 0.09)",
        "gold": "#C9A227", "user_bubble": "#0B2A5B", "user_text": "#FFFFFF",
        "shadow": "0 1px 2px rgba(11,27,51,.04), 0 8px 24px rgba(11,27,51,.06)",
        "grad_a": "#1F4FD1", "grad_b": "#0E8F6F",
    },
    "dark": {
        "bg": "#08111F", "bg_glow": "rgba(91, 140, 255, 0.10)", "surface": "#0F1B2E",
        "surface_2": "#13213A", "border": "#1E2D47", "border_strong": "#2A3D5E",
        "text": "#E7EEF8", "muted": "#9AABC4", "faint": "#6C7F9C",
        "primary": "#E7EEF8", "primary_text": "#08111F", "accent": "#6F9BFF",
        "accent_soft": "rgba(111, 155, 255, 0.12)", "emerald": "#34D1A6",
        "emerald_soft": "rgba(52, 209, 166, 0.12)", "amber": "#F0B455",
        "amber_soft": "rgba(240, 180, 85, 0.12)", "red": "#F08A84", "red_soft": "rgba(240, 138, 132, 0.12)",
        "gold": "#E3BE4E", "user_bubble": "#1F4FD1", "user_text": "#FFFFFF",
        "shadow": "0 1px 2px rgba(0,0,0,.3), 0 12px 32px rgba(0,0,0,.35)",
        "grad_a": "#6F9BFF", "grad_b": "#34D1A6",
    },
}

# kind -> (badge label, tone)
KIND_BADGES = {
    "answer": ("Verified from source", "emerald"),
    "not_found": ("Not in sources", "amber"),
    "clarify": ("Needs a scheme", "accent"),
    "advice": ("Advice declined", "amber"),
    "performance": ("Returns not shown", "amber"),
    "pii_block": ("Personal data blocked", "red"),
    "off_topic": ("Out of scope", "accent"),
    "error": ("Service unavailable", "red"),
}

ICONS = {  # lucide-style strokes, 24x24 viewBox
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
    "landmark": '<path d="M3 22h18"/><path d="M6 18v-7"/><path d="M10 18v-7"/><path d="M14 18v-7"/>'
                '<path d="M18 18v-7"/><path d="m12 2 9 5H3z"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>'
            '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "lock": '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>'
                '<path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/>',
    "home": '<path d="m3 10 9-7 9 7v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "external": '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
}


def icon(name: str, size: int = 18) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
            f'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def css(theme: str) -> str:
    t = THEMES[theme]
    tokens = "\n".join(f"  --{k.replace('_', '-')}: {v};" for k, v in t.items())
    return f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root {{
{tokens}
  --radius: 16px;
  --font: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}

/* ---------- Streamlit chrome ---------- */
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], footer, #MainMenu {{ display: none !important; }}
html, body, [data-testid="stApp"] *:not([data-testid="stIconMaterial"]) {{ font-family: var(--font) !important; }}
[data-testid="stApp"] {{
  background: radial-gradient(1200px 520px at 50% -140px, var(--bg-glow), transparent 70%), var(--bg);
  color: var(--text);
}}
[data-testid="stMainBlockContainer"], .block-container {{
  max-width: 880px; padding: 20px 32px 64px 32px; margin-left: auto; margin-right: auto;
}}
p, li, span, label, div {{ color: inherit; }}
[data-testid="stMarkdownContainer"] p {{ color: var(--text); }}
a {{ color: var(--accent); }}

/* ---------- Brand ---------- */
.brand {{ display: flex; align-items: center; gap: 10px; font-weight: 600; font-size: 15px; color: var(--text); }}
.brand .mark {{
  width: 36px; height: 36px; border-radius: 11px; flex: 0 0 36px;
  background: linear-gradient(145deg, #0B2A5B, #1F4FD1); color: var(--gold);
  display: grid; place-items: center; box-shadow: 0 6px 16px rgba(11,42,91,.30);
}}

/* ---------- Top bar ---------- */
.st-key-topbar {{ margin-bottom: 8px; }}
.st-key-topbar [data-testid="stMarkdownContainer"] {{ margin-bottom: 0 !important; }}
.st-key-topbar [data-testid="stHorizontalBlock"] {{ align-items: center; }}
.st-key-topbar [data-testid="stPopover"] button {{
  background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
  color: var(--text); font-weight: 500; box-shadow: var(--shadow); height: 40px;
}}
.st-key-topbar [data-testid="stPopover"] button p {{ color: var(--text); font-size: 13.5px; }}
[data-testid="stPopoverBody"] {{ background: var(--surface); border: 1px solid var(--border); color: var(--text); }}
[data-testid="stPopoverBody"] p, [data-testid="stPopoverBody"] li {{ color: var(--text); font-size: 14px; }}
.st-key-theme_toggle {{ display: flex; justify-content: flex-end; }}
.st-key-theme_toggle label {{ gap: 8px; }}
.st-key-theme_toggle label p {{ color: var(--muted) !important; font-size: 13px; font-weight: 500; }}
.st-key-new_chat button {{
  background: var(--primary); color: var(--primary-text); border: none; border-radius: 12px;
  height: 40px; font-weight: 600; width: 100%;
}}
.st-key-new_chat button p {{ color: var(--primary-text); font-size: 13.5px; }}
.st-key-new_chat button:hover {{ filter: brightness(1.12); color: var(--primary-text); }}

/* ---------- Hero ---------- */
.hero {{ text-align: center; padding: 44px 0 26px; }}
.orb {{
  width: 88px; height: 88px; margin: 0 auto 26px; border-radius: 50%;
  background: radial-gradient(circle at 32% 28%, #F2F7FF 0%, #8FB9FF 18%, #2F63E0 48%, #0B2A5B 82%);
  box-shadow: 0 0 0 10px var(--accent-soft), 0 18px 50px rgba(31,79,209,.45),
              inset -8px -10px 20px rgba(0,0,0,.25);
  position: relative; animation: float 6s ease-in-out infinite;
}}
.orb::after {{
  content: ""; position: absolute; inset: -3px; border-radius: 50%;
  background: conic-gradient(from 200deg, transparent 0 70%, var(--gold) 82%, transparent 94%);
  -webkit-mask: radial-gradient(circle, transparent 60%, #000 61%); mask: radial-gradient(circle, transparent 60%, #000 61%);
  opacity: .7; animation: spin 9s linear infinite;
}}
@keyframes float {{ 0%,100% {{ transform: translateY(0) }} 50% {{ transform: translateY(-6px) }} }}
@keyframes spin {{ to {{ transform: rotate(360deg) }} }}
@media (prefers-reduced-motion: reduce) {{ .orb, .orb::after {{ animation: none; }} }}
.hero h1 {{
  font-size: 38px; line-height: 1.2; font-weight: 600; letter-spacing: -0.02em;
  color: var(--text); margin: 0; padding: 0;
}}
.hero h1 .grad {{
  background: linear-gradient(90deg, var(--grad-a), var(--grad-b));
  -webkit-background-clip: text; background-clip: text; color: transparent;
}}
.hero h1 .grad {{ white-space: nowrap; }}
.hero .sub {{ color: var(--muted); font-size: 15px; margin-top: 12px; }}

/* ---------- Ask card (form) ---------- */
[data-testid="stForm"] {{
  background: var(--surface); border: 1px solid var(--border); border-radius: 20px;
  padding: 12px 12px 12px 18px; box-shadow: var(--shadow);
}}
[data-testid="stForm"]:focus-within {{ border-color: var(--accent); box-shadow: 0 0 0 4px var(--accent-soft), var(--shadow); }}
[data-testid="stTextInputRootElement"], [data-testid="stTextInputRootElement"] > div {{
  background: transparent !important; border: none !important; box-shadow: none !important;
}}
[data-testid="stTextInput"] input {{
  color: var(--text); font-size: 16px; padding: 6px 2px; caret-color: var(--accent);
  -webkit-text-fill-color: var(--text);
}}
[data-testid="stTextInput"] input::placeholder {{ color: var(--faint); -webkit-text-fill-color: var(--faint); }}
[data-testid="InputInstructions"] {{ display: none; }}
[data-testid="stFormSubmitButton"] {{ display: flex; justify-content: flex-end; }}
[data-testid="stFormSubmitButton"] button {{
  background: var(--primary); border: none; border-radius: 10px; width: 36px; height: 36px;
  min-height: 36px; padding: 0; color: var(--primary-text);
}}
[data-testid="stFormSubmitButton"] button p {{ color: var(--primary-text); font-size: 18px; }}
[data-testid="stFormSubmitButton"] button:hover {{ filter: brightness(1.15); color: var(--primary-text); }}
.disclaimer {{
  display: flex; justify-content: center; align-items: center; gap: 6px; margin: 12px 0 0;
  font-size: 12.5px; color: var(--faint);
}}
.disclaimer b {{ color: var(--muted); font-weight: 600; }}

/* ---------- Example cards ---------- */
.section-label {{
  font-size: 12px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase;
  color: var(--faint); margin: 34px 0 12px;
}}
div[class*="st-key-ex_"] button {{
  width: 100%; height: 132px; background: var(--surface-2); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 16px; text-align: left; transition: all .18s ease;
  display: flex; align-items: stretch;
}}
div[class*="st-key-ex_"] button:hover {{
  border-color: var(--accent); background: var(--surface); transform: translateY(-2px); box-shadow: var(--shadow);
}}
div[class*="st-key-ex_"] button p {{ color: var(--text); font-size: 14px; line-height: 1.45; text-align: left; }}
div[class*="st-key-ex_"] button span[data-testid="stIconMaterial"] {{
  color: var(--accent); font-size: 20px; background: var(--accent-soft); border-radius: 8px; padding: 6px;
}}
div[class*="st-key-ex_"] button > div {{ width: 100%; height: 100%; justify-content: flex-start; align-items: stretch; }}
div[class*="st-key-ex_"] button > div > span {{
  display: flex; flex-direction: column-reverse; align-items: flex-start; justify-content: space-between;
  width: 100%; height: 100%; gap: 12px;
}}
div[class*="st-key-ex_"] button [data-testid="stMarkdownContainer"],
div[class*="st-key-ex_"] button [data-testid="stMarkdownContainer"] p {{
  white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
}}

/* ---------- Chat thread ---------- */
.thread {{ display: flex; flex-direction: column; gap: 18px; padding: 12px 0 20px; }}
.msg-user {{ display: flex; justify-content: flex-end; }}
.msg-user .bubble {{
  max-width: 78%; background: var(--user-bubble); color: var(--user-text);
  padding: 12px 16px; border-radius: 18px 18px 4px 18px; font-size: 15px; line-height: 1.5;
}}
.msg-user .bubble.hidden {{ font-style: italic; opacity: .85; }}
.msg-bot {{ display: flex; gap: 12px; align-items: flex-start; }}
.avatar {{
  flex: 0 0 34px; height: 34px; border-radius: 50%;
  background: radial-gradient(circle at 32% 28%, #F2F7FF 0%, #8FB9FF 20%, #2F63E0 52%, #0B2A5B 85%);
  box-shadow: 0 4px 12px rgba(31,79,209,.35);
}}
.card {{
  flex: 1; background: var(--surface); border: 1px solid var(--border); border-radius: 4px 18px 18px 18px;
  padding: 14px 16px; box-shadow: var(--shadow);
}}
.card .text {{ font-size: 15px; line-height: 1.6; color: var(--text); }}
.badge {{
  display: inline-flex; align-items: center; gap: 5px; font-size: 11.5px; font-weight: 600;
  padding: 3px 8px; border-radius: 99px; margin-bottom: 8px;
}}
.badge.emerald {{ color: var(--emerald); background: var(--emerald-soft); }}
.badge.amber {{ color: var(--amber); background: var(--amber-soft); }}
.badge.red {{ color: var(--red); background: var(--red-soft); }}
.badge.accent {{ color: var(--accent); background: var(--accent-soft); }}
.meta {{ display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; margin-top: 12px;
  padding-top: 10px; border-top: 1px dashed var(--border); }}
.src {{
  display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; font-weight: 500;
  color: var(--accent) !important; text-decoration: none; background: var(--accent-soft);
  padding: 4px 10px; border-radius: 8px;
}}
.src, .src:visited {{ text-decoration: none !important; }}
.src:hover {{ filter: brightness(1.1); text-decoration: none !important; }}
.updated {{ display: inline-flex; align-items: center; gap: 5px; font-size: 12px; color: var(--faint); }}
[data-testid="stSpinner"] p, [data-testid="stSpinner"] {{ color: var(--muted); }}

@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"], .block-container {{ padding: 12px 16px 48px; }}
  .st-key-topbar [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap; gap: 8px; }}
  .st-key-topbar [data-testid="stColumn"] {{ width: auto !important; flex: 0 0 auto !important; min-width: 0 !important; }}
  .st-key-topbar [data-testid="stColumn"]:first-child {{ flex: 1 1 100% !important; }}
  .st-key-topbar [data-testid="stColumn"]:nth-child(3) {{ display: none; }}
  .hero {{ padding: 24px 0 18px; }}
  .hero h1 {{ font-size: 28px; }}
  .msg-user .bubble {{ max-width: 88%; }}
  div[class*="st-key-ex_"] button {{ height: auto; min-height: 96px; }}
  [data-testid="stForm"] [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap; gap: 8px; }}
  [data-testid="stForm"] [data-testid="stColumn"] {{ width: auto !important; min-width: 0 !important; flex: 1 1 auto !important; }}
  [data-testid="stForm"] [data-testid="stColumn"]:last-child {{ flex: 0 0 auto !important; }}
  .disclaimer {{ display: block; text-align: center; line-height: 1.6; }}
}}
</style>"""


def brand() -> str:
    return f'<div class="brand"><span class="mark">{icon("shield", 20)}</span>HDFC MF Facts Assistant</div>'


def hero() -> str:
    return (f'<section class="hero"><div class="orb"></div>'
            f'<h1>What can I tell you about <span class="grad">your funds?</span></h1>'
            f'<p class="sub">Ask me facts about 5 HDFC Mutual Fund schemes, your statements, '
            f'and mutual fund basics.</p></section>')


def disclaimer() -> str:
    return f'<div class="disclaimer">{icon("lock", 13)} <b>Facts-only. No investment advice.</b> Please don\'t share personal details.</div>'


def user_message(text: str, hidden: bool = False) -> str:
    return f'<div class="msg-user"><div class="bubble{" hidden" if hidden else ""}">{html.escape(text)}</div></div>'


def source_label(url: str) -> str:
    """'hdfcfund.com' for pages; 'hdfcfund.com · KIM (PDF)' for documents on HDFC's file server."""
    host = urlparse(url).netloc.replace("www.", "").replace("files.", "")
    if not url.lower().endswith(".pdf"):
        return host
    kind = "KIM" if "/KIM/" in url else "Factsheet" if "Factsheet" in url else "document"
    return f"{host} · {kind} (PDF)"


def bot_message(resp) -> str:
    label, tone = KIND_BADGES.get(resp.kind, ("Answer", "accent"))
    meta = ""
    if resp.citation_url or resp.last_updated:
        parts = []
        if resp.citation_url:
            parts.append(f'<a class="src" href="{html.escape(resp.citation_url)}" target="_blank" '
                         f'rel="noopener">{icon("external", 13)} Source · {html.escape(source_label(resp.citation_url))}</a>')
        if resp.last_updated:
            parts.append(f'<span class="updated">{icon("clock", 13)} Last updated from sources: '
                         f'{html.escape(resp.last_updated)}</span>')
        meta = f'<div class="meta">{"".join(parts)}</div>'
    return (f'<div class="msg-bot"><div class="avatar"></div><div class="card">'
            f'<span class="badge {tone}">{label}</span><div class="text">{html.escape(resp.text)}</div>'
            f'{meta}</div></div>')

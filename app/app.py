import random
import streamlit as st
from paraphraser_backend import (
    fetch_wiki, paraphrase, paraphrase_stream,
    DEFAULT_MODEL, DEFAULT_API_KEY, DEFAULT_BASE_URL
)

# ── page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Wikipedia Paraphraser AI", page_icon="🧠", layout="wide")
st.markdown("""
<style>
/* hide streamlit chrome */
#MainMenu, footer, #stDecoration, .stDeployButton { visibility: hidden; }

/* page background */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
    min-height: 100vh;
}
[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.04);
    border-right: 1px solid rgba(255,255,255,0.08);
}

/* hero title */
.hero-title {
    font-size: 3rem;
    font-weight: 800;
    background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0;
}
.hero-sub {
    color: rgba(255,255,255,0.5);
    font-size: 1.1rem;
    margin-top: 0.2rem;
    margin-bottom: 1.5rem;
}

/* cards */
.card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
}
.card-title {
    font-size: 1rem;
    font-weight: 700;
    color: #a78bfa;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.6rem;
}
.card-meta {
    font-size: 0.78rem;
    color: rgba(255,255,255,0.4);
    margin-bottom: 0.8rem;
}
.card-text {
    color: rgba(255,255,255,0.85);
    line-height: 1.7;
    font-size: 0.97rem;
}

/* stat pills */
.stat-row {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-bottom: 0.6rem;
}
.stat-pill {
    background: rgba(167,139,250,0.15);
    border: 1px solid rgba(167,139,250,0.3);
    border-radius: 999px;
    padding: 0.2rem 0.75rem;
    font-size: 0.75rem;
    color: #c4b5fd;
    font-weight: 600;
}
.stat-pill.green {
    background: rgba(52,211,153,0.12);
    border-color: rgba(52,211,153,0.3);
    color: #6ee7b7;
}
.stat-pill.blue {
    background: rgba(96,165,250,0.12);
    border-color: rgba(96,165,250,0.3);
    color: #93c5fd;
}

/* similarity badge */
.sim-badge {
    display: inline-block;
    padding: 0.25rem 0.9rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 700;
    margin-left: 0.5rem;
}

/* history item */
.hist-item {
    background: rgba(255,255,255,0.04);
    border-radius: 8px;
    padding: 0.5rem 0.75rem;
    margin-bottom: 0.4rem;
    font-size: 0.82rem;
    border-left: 3px solid #a78bfa;
    color: rgba(255,255,255,0.7);
}

/* wiki link */
a { color: #60a5fa !important; }

/* metric label */
[data-testid="stMetricLabel"] { font-size: 0.75rem !important; }
[data-testid="stMetricValue"] { font-size: 1.4rem !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

# ── session state ──────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "topic_input" not in st.session_state:
    st.session_state.topic_input = ""

# ── helpers ────────────────────────────────────────────────────────────────────
RANDOM_TOPICS = [
    "Artificial Intelligence", "Quantum Computing", "Climate Change",
    "Black Hole", "DNA", "Internet", "Bitcoin", "Renaissance",
    "Albert Einstein", "Amazon Rainforest", "Machine Learning",
    "Python (programming language)", "World War II", "Solar System",
    "Elon Musk", "Olympic Games", "Antibiotics", "Moon landing",
]

def word_count(text):
    return len(text.split())

def reading_time(text):
    mins = word_count(text) / 200
    return f"{int(mins * 60)}s" if mins < 1 else f"{round(mins, 1)} min"

def sentence_count(text):
    return len([s for s in text.replace("?", ".").replace("!", ".").split(".") if s.strip()])

def similarity_score(a, b):
    set_a, set_b = set(a.lower().split()), set(b.lower().split())
    if not set_a or not set_b:
        return 0
    return round(len(set_a & set_b) / len(set_a | set_b) * 100)

def wiki_url(title, lang):
    return f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"

def sim_color(score):
    if score >= 50:
        return "#34d399", "rgba(52,211,153,0.15)"
    if score >= 30:
        return "#fbbf24", "rgba(251,191,36,0.15)"
    return "#f87171", "rgba(248,113,113,0.15)"

# ── sidebar ────────────────────────────────────────────────────────────────────
server_configured = bool(DEFAULT_API_KEY)

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    wiki_lang   = st.selectbox("Wikipedia Language", ["en", "de"], index=0)
    model       = st.selectbox("Model", [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
    ], index=0)
    temperature = st.slider("Paraphrase Strength", 0.0, 1.0, 0.7, 0.05,
                            help="0 = faithful  |  1 = creative")
    streaming   = st.toggle("Live Streaming", value=True)

    st.markdown("---")

    if not server_configured:
        st.markdown("### 🔑 API Key")
        api_key  = st.text_input("Groq API Key", value="", type="password",
                                 help="Free at console.groq.com")
        base_url = DEFAULT_BASE_URL
        with st.expander("Get a free key"):
            st.markdown(
                "1. [console.groq.com](https://console.groq.com)\n"
                "2. Sign up (free)\n"
                "3. API Keys → Create API key\n"
                "4. Paste above"
            )
    else:
        api_key  = DEFAULT_API_KEY
        base_url = DEFAULT_BASE_URL

    if st.session_state.history:
        st.markdown("---")
        st.markdown("### 🕘 Recent")
        for h in reversed(st.session_state.history[-5:]):
            st.markdown(
                f"<div class='hist-item'><b>{h['topic']}</b> "
                f"<span style='opacity:.5'>({h['lang'].upper()})</span><br>"
                f"{h['words_orig']} → {h['words_para']} words</div>",
                unsafe_allow_html=True,
            )
        if st.button("Clear history", use_container_width=True):
            st.session_state.history = []
            st.rerun()

    st.markdown("---")
    with st.expander("ℹ️ About"):
        st.markdown(
            "Fetches the Wikipedia summary for any topic and paraphrases it "
            "using **Llama 3.3-70b** via Groq.  \n\n"
            "Built with Streamlit · TH Lübeck  \n"
            "[GitHub ↗](https://github.com/SushantKumarPandey/Wikipedia_Paraphraser-Ai)"
        )

# ── hero ───────────────────────────────────────────────────────────────────────
st.markdown("<div class='hero-title'>🧠 Wikipedia Paraphraser AI</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='hero-sub'>Type any topic — get the Wikipedia summary and an AI paraphrase, side by side.</div>",
    unsafe_allow_html=True,
)

# ── input row ────────────────────────────────────────────────────────────────
col_in, col_rand, col_go = st.columns([5, 1, 1.2])
with col_in:
    topic = st.text_input(
        "topic", label_visibility="collapsed",
        value=st.session_state.topic_input,
        placeholder="e.g.  Blockchain  ·  Paris  ·  Artificial Intelligence",
    )
with col_rand:
    if st.button("🎲 Random", use_container_width=True):
        st.session_state.topic_input = random.choice(RANDOM_TOPICS)
        st.rerun()
with col_go:
    go = st.button("🔍 Fetch & Paraphrase", type="primary", use_container_width=True)

# ── main logic ────────────────────────────────────────────────────────────────
if go:
    if not topic.strip():
        st.warning("Please enter a topic.")
        st.stop()
    if not api_key:
        st.warning("Enter your Groq API key in the sidebar.")
        st.stop()

    with st.spinner(f"Fetching Wikipedia ({wiki_lang.upper()}) …"):
        res, err = fetch_wiki(topic, wiki_lang)
        if (err or not res) and wiki_lang == "de":
            res, err = fetch_wiki(topic, "en")
    if err or not res:
        st.error(err or "Nothing found.")
        st.stop()

    original = res.get("extract", "").strip()
    if not original:
        st.error("No summary available for this topic.")
        st.stop()

    with st.spinner("Paraphrasing with AI …"):
        try:
            if streaming:
                parts, box = [], st.empty()
                for piece in paraphrase_stream(original, model=model, temperature=temperature,
                                               api_key=api_key, base_url=base_url):
                    parts.append(piece or "")
                    box.markdown(
                        f"<div class='card'><div class='card-title'>✍️ Paraphrase (AI)</div>"
                        f"<div class='card-text'>{''.join(parts)}</div></div>",
                        unsafe_allow_html=True,
                    )
                para = "".join(parts).strip()
                box.empty()
            else:
                para = (paraphrase(original, model=model, temperature=temperature,
                                   api_key=api_key, base_url=base_url) or "").strip()
        except Exception as e:
            para = ""
            st.error(f"LLM error: {e}")

    # save history
    title_res = res.get("title", topic)
    lang_res  = res.get("lang", wiki_lang)
    st.session_state.history.append({
        "topic":      title_res,
        "lang":       lang_res,
        "words_orig": word_count(original),
        "words_para": word_count(para) if para else 0,
    })

    # ── metrics ──────────────────────────────────────────────────────────────
    sim = similarity_score(original, para) if para else 0
    sim_fg, sim_bg = sim_color(sim)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Original words",   word_count(original))
    m2.metric("Paraphrase words", word_count(para) if para else 0,
              delta=word_count(para) - word_count(original) if para else None)
    m3.metric("Read time (orig)", reading_time(original))
    m4.metric("Read time (para)", reading_time(para) if para else "–")
    m5.metric("Word overlap",     f"{sim}%",
              help="Jaccard similarity — shared vocabulary between original and paraphrase")

    st.markdown("---")

    # ── side-by-side cards ───────────────────────────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        st.markdown(f"""
        <div class='card'>
          <div class='card-title'>📖 Wikipedia Original</div>
          <div class='stat-row'>
            <span class='stat-pill'>{word_count(original)} words</span>
            <span class='stat-pill blue'>{sentence_count(original)} sentences</span>
            <span class='stat-pill green'>{reading_time(original)} read</span>
          </div>
          <div class='card-meta'>
            <a href='{wiki_url(title_res, lang_res)}' target='_blank'>
              Read full article on Wikipedia ↗
            </a>
          </div>
          <div class='card-text'>{original}</div>
        </div>
        """, unsafe_allow_html=True)
        st.download_button("⬇ Download Original (.txt)", original.encode("utf-8"),
                           file_name=f"{title_res}_original.txt", use_container_width=True)

    with c2:
        if para:
            st.markdown(f"""
            <div class='card'>
              <div class='card-title'>✍️ Paraphrase (AI)
                <span class='sim-badge'
                  style='background:{sim_bg}; color:{sim_fg}; border:1px solid {sim_fg}'>
                  {sim}% overlap
                </span>
              </div>
              <div class='stat-row'>
                <span class='stat-pill'>{word_count(para)} words</span>
                <span class='stat-pill blue'>{sentence_count(para)} sentences</span>
                <span class='stat-pill green'>{reading_time(para)} read</span>
              </div>
              <div class='card-meta'>Model: <code>{model}</code> · Strength: {temperature}</div>
              <div class='card-text'>{para}</div>
            </div>
            """, unsafe_allow_html=True)
            st.download_button("⬇ Download Paraphrase (.txt)", para.encode("utf-8"),
                               file_name=f"{title_res}_paraphrase.txt", use_container_width=True)
        else:
            st.markdown("<div class='card'><div class='card-text'>Paraphrase not available.</div></div>",
                        unsafe_allow_html=True)

    st.success(f"Done ✅  —  **{title_res}** ({lang_res.upper()})  ·  Model: `{model}`")

# ── debug ─────────────────────────────────────────────────────────────────────
with st.expander("🐛 Debug"):
    st.write({
        "topic": topic, "wiki_lang": wiki_lang, "model": model,
        "temperature": temperature, "streaming": streaming,
        "server_configured": server_configured,
        "history_count": len(st.session_state.history),
    })

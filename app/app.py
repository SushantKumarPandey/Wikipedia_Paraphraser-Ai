import random
import streamlit as st
from paraphraser_backend import (
    fetch_wiki, paraphrase, paraphrase_stream,
    DEFAULT_MODEL, DEFAULT_API_KEY, DEFAULT_BASE_URL
)

# ── page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Wikipedia Paraphraser", page_icon="🧠", layout="wide")
st.markdown("""
<style>
#MainMenu, footer, #stDecoration { visibility: hidden; }
.stDeployButton { display: none; }
.block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

# ── session state ──────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []   # list of dicts: {topic, lang, words_orig, words_para}
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
    return f"{int(mins * 60)} sec" if mins < 1 else f"{round(mins, 1)} min"

def sentence_count(text):
    return len([s for s in text.replace("?", ".").replace("!", ".").split(".") if s.strip()])

def similarity_score(a, b):
    """Simple word-overlap similarity (Jaccard index)."""
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a or not set_b:
        return 0
    return round(len(set_a & set_b) / len(set_a | set_b) * 100)

def wiki_url(title, lang):
    return f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"

# ── sidebar ────────────────────────────────────────────────────────────────────
server_configured = bool(DEFAULT_API_KEY)

with st.sidebar:
    st.subheader("⚙️ Settings")
    wiki_lang = st.selectbox("Wikipedia Language", ["en", "de"], index=0)
    model = st.selectbox(
        "Model",
        ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        index=0
    )
    temperature = st.slider("Paraphrase Strength", 0.0, 1.0, 0.7, 0.05,
                            help="0 = close to original  |  1 = more creative")
    streaming = st.toggle("Streaming", value=True, help="Watch text generate live")

    st.markdown("---")

    if not server_configured:
        st.subheader("🔑 API Key")
        api_key = st.text_input("Groq API Key", value="", type="password",
                                help="Free at console.groq.com")
        base_url = DEFAULT_BASE_URL
        with st.expander("How to get a free key"):
            st.markdown(
                "1. Go to **[console.groq.com](https://console.groq.com)**\n"
                "2. Sign up (free, no credit card)\n"
                "3. **API Keys → Create API key**\n"
                "4. Paste it above"
            )
    else:
        api_key  = DEFAULT_API_KEY
        base_url = DEFAULT_BASE_URL

    # ── search history ──────────────────────────────────────────────────────
    if st.session_state.history:
        st.markdown("---")
        st.subheader("🕘 Recent Searches")
        for h in reversed(st.session_state.history[-5:]):
            st.markdown(
                f"**{h['topic']}** `{h['lang']}`  \n"
                f"<small>{h['words_orig']} → {h['words_para']} words</small>",
                unsafe_allow_html=True,
            )
        if st.button("Clear history"):
            st.session_state.history = []
            st.rerun()

    st.markdown("---")
    with st.expander("ℹ️ About"):
        st.write(
            "Fetches the short Wikipedia summary for any topic and paraphrases it "
            "using Llama 3.3-70b via Groq. "
            "University project — TH Lübeck."
        )

# ── header ────────────────────────────────────────────────────────────────────
st.title("🧠 Wikipedia Paraphraser AI")
st.caption("Type a topic to get the Wikipedia summary and an AI paraphrase side by side.")

# ── input row ────────────────────────────────────────────────────────────────
col_input, col_btn = st.columns([5, 1])
with col_input:
    topic = st.text_input(
        "Topic / Wikipedia page title",
        value=st.session_state.topic_input,
        placeholder="e.g. Blockchain, Paris, Artificial Intelligence",
        label_visibility="collapsed",
    )
with col_btn:
    if st.button("🎲 Random", help="Pick a random topic"):
        st.session_state.topic_input = random.choice(RANDOM_TOPICS)
        st.rerun()

go = st.button("🔍 Fetch & Paraphrase", type="primary")

# ── main logic ────────────────────────────────────────────────────────────────
if go:
    if not topic.strip():
        st.warning("Please enter a topic.")
        st.stop()
    if not api_key:
        st.warning("Please enter your Groq API key in the sidebar.")
        st.stop()

    # fetch Wikipedia
    with st.spinner(f"Fetching Wikipedia ({wiki_lang}) …"):
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

    # paraphrase
    with st.spinner("Paraphrasing …"):
        try:
            if streaming:
                parts = []
                box = st.empty()
                for piece in paraphrase_stream(original, model=model, temperature=temperature,
                                               api_key=api_key, base_url=base_url):
                    parts.append(piece or "")
                    box.write("".join(parts))
                para = "".join(parts).strip()
            else:
                para = (paraphrase(original, model=model, temperature=temperature,
                                   api_key=api_key, base_url=base_url) or "").strip()
        except Exception as e:
            para = ""
            st.error(f"LLM error: {e}")

    # save to history
    st.session_state.history.append({
        "topic":      res.get("title", topic),
        "lang":       res.get("lang", wiki_lang),
        "words_orig": word_count(original),
        "words_para": word_count(para) if para else 0,
    })

    # ── stats row ────────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Original words",    word_count(original))
    m2.metric("Paraphrase words",  word_count(para) if para else 0,
              delta=word_count(para) - word_count(original) if para else None)
    m3.metric("Reading time (orig)",  reading_time(original))
    m4.metric("Reading time (para)",  reading_time(para) if para else "–")
    m5.metric("Word overlap",  f"{similarity_score(original, para)}%" if para else "–",
              help="How many words the paraphrase shares with the original (Jaccard)")

    st.markdown("---")

    # ── side by side ────────────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    title    = res.get("title", topic)
    lang_res = res.get("lang", wiki_lang)

    with c1:
        st.subheader("📖 Wikipedia (Original)")
        st.caption(
            f"{word_count(original)} words · {sentence_count(original)} sentences · "
            f"{reading_time(original)} read · "
            f"[Read full article ↗]({wiki_url(title, lang_res)})"
        )
        st.write(original)
        st.download_button("⬇ Download Original (.txt)", original.encode("utf-8"),
                           file_name=f"{title}_original.txt")

    with c2:
        st.subheader("✍️ Paraphrase (AI)")
        if para:
            st.caption(
                f"{word_count(para)} words · {sentence_count(para)} sentences · "
                f"{reading_time(para)} read · "
                f"Model: `{model}`"
            )
            st.write(para)
            st.download_button("⬇ Download Paraphrase (.txt)", para.encode("utf-8"),
                               file_name=f"{title}_paraphrase.txt")
        else:
            st.write("Paraphrase not available.")

    st.success(f"Done ✅  —  {title} ({lang_res.upper()})")

# ── debug ────────────────────────────────────────────────────────────────────
with st.expander("🐛 Debug"):
    st.write({
        "topic": topic,
        "wiki_lang": wiki_lang,
        "model": model,
        "temperature": temperature,
        "streaming": streaming,
        "server_configured": server_configured,
        "history_count": len(st.session_state.history),
    })

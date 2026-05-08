import sys
import os
import random
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from paraphraser_backend import (
    fetch_wiki, paraphrase_stream,
    DEFAULT_API_KEY, DEFAULT_BASE_URL, DEFAULT_MODEL,
)

st.set_page_config(page_title="Wikipedia Paraphraser", page_icon="📖", layout="wide")

RANDOM_TOPICS = [
    "Artificial Intelligence", "Black Hole", "Climate Change",
    "Quantum Computing", "DNA", "Bitcoin", "Renaissance",
    "Albert Einstein", "Amazon Rainforest", "Machine Learning",
    "Olympic Games", "Antibiotics", "French Revolution",
    "Solar System", "World War II", "Blockchain",
]

for k, v in [("original", ""), ("paraphrase", ""), ("wiki_title", ""), ("topic_val", "")]:
    if k not in st.session_state:
        st.session_state[k] = v

# sidebar
with st.sidebar:
    st.header("⚙️ Settings")

    lang = st.selectbox("Wikipedia language", ["de", "en"])

    if DEFAULT_API_KEY:
        api_key  = DEFAULT_API_KEY
        base_url = DEFAULT_BASE_URL
    else:
        base_url = st.text_input("API base URL", value="https://api.groq.com/openai/v1")
        api_key  = st.text_input("API key", type="password", placeholder="gsk_...")

    model       = st.text_input("Model", value=DEFAULT_MODEL)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.05,
                            help="Lower = more faithful, higher = more creative")

# main area
st.title("📖 Wikipedia Paraphraser")
st.caption("Enter a topic to fetch its Wikipedia summary and get an AI paraphrase.")

col_topic, col_rand, col_go = st.columns([5, 1, 1.5])

with col_rand:
    if st.button("🎲", help="Random topic"):
        st.session_state.topic_val = random.choice(RANDOM_TOPICS)
        st.rerun()

with col_topic:
    topic = st.text_input(
        "topic",
        label_visibility="collapsed",
        value=st.session_state.topic_val,
        placeholder="e.g. Machine Learning · Paris · Bitcoin",
    )

with col_go:
    go = st.button("🔍 Fetch & Paraphrase", type="primary", use_container_width=True)

if go:
    if not topic.strip():
        st.warning("Please enter a topic.")
        st.stop()
    if not api_key.strip():
        st.warning("Enter your API key in the sidebar.")
        st.stop()

    with st.spinner("Fetching Wikipedia..."):
        result, err = fetch_wiki(topic, lang)
        if err and lang == "de":
            result, err = fetch_wiki(topic, "en")

    if err or not result:
        st.error(err or "Nothing found.")
        st.stop()

    st.session_state.original   = result["extract"]
    st.session_state.wiki_title = result["title"]
    st.session_state.paraphrase = ""

    parts = []
    box = st.empty()
    for piece in paraphrase_stream(
        st.session_state.original,
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
    ):
        parts.append(piece)
        box.markdown("✍️ **Paraphrasing...** " + "".join(parts))

    st.session_state.paraphrase = "".join(parts).strip()
    box.empty()
    st.rerun()

# show results
if st.session_state.original:
    left, right = st.columns(2)

    with left:
        st.subheader("📖 Wikipedia Original")
        st.write(st.session_state.original)
        st.download_button(
            "⬇ Download original (.txt)",
            data=st.session_state.original,
            file_name=f"{st.session_state.wiki_title}_original.txt",
            use_container_width=True,
        )

    with right:
        st.subheader("✍️ Paraphrase")
        if st.session_state.paraphrase:
            st.write(st.session_state.paraphrase)
            st.download_button(
                "⬇ Download paraphrase (.txt)",
                data=st.session_state.paraphrase,
                file_name=f"{st.session_state.wiki_title}_paraphrase.txt",
                use_container_width=True,
            )
        else:
            st.info("Paraphrase will appear here.")
import streamlit as st
from paraphraser_backend import (
    fetch_wiki, paraphrase, paraphrase_stream,
    DEFAULT_MODEL, DEFAULT_API_KEY, DEFAULT_BASE_URL
)

st.set_page_config(page_title="Wikipedia Paraphraser", page_icon="🧠", layout="wide")
st.markdown("""
<style>
#MainMenu, footer, #stDecoration {visibility: hidden;}
.stDeployButton {display:none;}
.block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

st.title("Wikipedia Paraphraser AI")
st.caption(
    "Fetches a Wikipedia article summary and rewrites it using an AI language model. "
    "Configure language, model and options in the sidebar."
)

with st.sidebar:
    st.subheader("Settings")

    wiki_lang = st.selectbox("Wikipedia Language", ["de", "en"], index=1)

    st.markdown("---")
    st.subheader("LLM API")

    # Allow env-var pre-configuration OR manual entry
    api_key = st.text_input(
        "API Key",
        value=DEFAULT_API_KEY,
        type="password",
        help="Groq API key (free at console.groq.com) or any OpenAI-compatible key."
    )
    base_url = st.text_input(
        "API Base URL",
        value=DEFAULT_BASE_URL,
        help="Groq: https://api.groq.com/openai/v1  |  OpenAI: https://api.openai.com/v1"
    )
    model = st.selectbox(
        "Model",
        ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gpt-4o-mini"],
        index=0
    )
    temperature = st.slider("Paraphrase Strength", 0.0, 1.0, 0.7, 0.05,
                            help="0 = close to original, 1 = more creative")
    streaming = st.toggle("Streaming", value=True, help="Show text live as the model generates it")

    st.markdown("---")
    with st.expander("ℹ️ About"):
        st.write(
            "This app fetches the short Wikipedia summary for any topic and paraphrases it "
            "using a large language model via an OpenAI-compatible API. "
            "Built with Streamlit as a university project at TH Lübeck."
        )
    with st.expander("❓ How to get a free API key"):
        st.markdown(
            "1. Go to **[console.groq.com](https://console.groq.com)**\n"
            "2. Sign up for free\n"
            "3. Click **API Keys → Create API key**\n"
            "4. Paste it in the **API Key** field above\n\n"
            "The default Base URL `https://api.groq.com/openai/v1` is already set."
        )

topic = st.text_input("Topic / Wikipedia page title", value="Blockchain")
go = st.button("Fetch & Paraphrase")

if go:
    if not api_key:
        st.warning("Please enter an API key in the sidebar. Get a free one at console.groq.com")
        st.stop()

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

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Wikipedia (Original)")
        st.write(original)
        st.download_button("Download Original (.txt)", original.encode("utf-8"),
                           file_name=f"{res.get('title', 'article')}_original.txt")
    with c2:
        st.subheader("Paraphrase (AI)")
        st.write(para or "Paraphrase not available.")
        if para:
            st.download_button("Download Paraphrase (.txt)", para.encode("utf-8"),
                               file_name=f"{res.get('title', 'article')}_paraphrase.txt")

    st.caption(
        f"Source: Wikipedia REST API · Page: {res.get('title', '–')} · Language: {res.get('lang', '–')} · Model: {model}"
    )
    st.success("Done ✅")

with st.expander("Debug"):
    st.write({
        "topic": topic,
        "wiki_lang": wiki_lang,
        "model": model,
        "temperature": temperature,
        "streaming": streaming,
        "base_url": base_url,
    })

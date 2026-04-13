import streamlit as st
from paraphraser_backend import fetch_wiki, paraphrase, paraphrase_stream, DEFAULT_MODEL

st.set_page_config(page_title="Paraphrasierer", page_icon="🧠", layout="wide")
st.markdown("""
<style>
#MainMenu, footer, #stDecoration {visibility: hidden;}
.stDeployButton {display:none;}
.block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

st.title("Wikipedia Paraphrasierer")
st.caption(
    "Dies ist ein einfacher Wikipedia-Paraphrasierer. "
    "Die App lädt die Kurz-Zusammenfassung eines Wikipedia-Artikels "
    "und formuliert sie mit einem myLab LLM neu. "
    "Links in der Sidebar kannst du Sprache, Modell und Optionen einstellen."
)

with st.sidebar:
    st.subheader("Einstellungen")
    wiki_lang = st.selectbox("Wikipedia-Sprache", ["de", "en"], index=0)
    model = st.selectbox("LLM-Modell", [DEFAULT_MODEL, "chat-default", "chat-large"], index=0)
    temperature = st.slider("Paraphrase-Stärke", 0.0, 1.0, 0.7, 0.05)
    streaming = st.toggle("Streaming", value=True, help="Zeigt den Text live während der Generierung")

    st.markdown("---")

    with st.expander("ℹ️ About"):
        st.write(
            "Diese App lädt die Kurz-Zusammenfassung einer Wikipedia-Seite "
            "und paraphrasiert sie mit einem myLab LLM (z. B. Llama-3.3-70b). "
            "Links kannst du Sprache, Modell und Stärke einstellen. "
            "Das Ergebnis erscheint im Hauptbereich nebeneinander."
        )

    with st.expander("❓ Hilfe"):
        st.markdown(
            "- **Thema**: Seitentitel eingeben (z. B. *Paris*, *Blockchain*).\n"
            "- **Wikipedia-Sprache**: de/en wählen. (de → en Fallback)\n"
            "- **Paraphrase-Stärke**: 0.0 = nah am Original, 1.0 = freier.\n"
            "- **Streaming**: zeigt Text live beim Generieren.\n"
            "- **Downloads**: Original & Paraphrase als .txt speichern."
        )

topic = st.text_input("Thema / Seitentitel", value="Blockchain")
go = st.button("Zusammenfassung abrufen & paraphrasieren")

if go:
    with st.spinner(f"Hole Wikipedia ({wiki_lang}) …"):
        res, err = fetch_wiki(topic, wiki_lang)
        if (err or not res) and wiki_lang == "de":
            res, err = fetch_wiki(topic, "en")
    if err or not res:
        st.error(err or "Nichts gefunden.")
        st.stop()

    original = res.get("extract", "").strip()
    if not original:
        st.error("Keine Zusammenfassung verfügbar.")
        st.stop()

    with st.spinner("Paraphrasiere …"):
        try:
            if streaming:
                parts = []
                box = st.empty()
                for piece in paraphrase_stream(original, model=model, temperature=temperature):
                    parts.append(piece or "")
                    box.write("".join(parts))
                para = "".join(parts).strip()
            else:
                para = (paraphrase(original, model=model, temperature=temperature) or "").strip()
        except Exception as e:
            para = ""
            st.error(f"LLM-Fehler: {e}")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Wikipedia (Original)")
        st.write(original)
        st.download_button("Original als TXT", original.encode("utf-8"),
                           file_name=f"{res.get('title','seite')}_original.txt")
    with c2:
        st.subheader("Paraphrase (myLab)")
        st.write(para or "Paraphrase nicht verfügbar.")
        if para:
            st.download_button("Paraphrase als TXT", para.encode("utf-8"),
                               file_name=f"{res.get('title','seite')}_paraphrase.txt")

    st.caption(f"Quelle: Wikipedia REST API • Seite: {res.get('title','–')} • Sprache: {res.get('lang','–')}")
    st.success("Fertig ✅")

with st.expander("Debug"):
    st.write({
        "topic": topic,
        "wiki_lang": wiki_lang,
        "model": model,
        "temperature": temperature,
        "streaming": streaming
    })

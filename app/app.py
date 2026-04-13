import random
import urllib.parse
import streamlit as st
from paraphraser_backend import (
    fetch_wiki, paraphrase, paraphrase_stream,
    highlight_keywords, flesch_score, flesch_label,
    translate_text, generate_quiz, build_pdf,
    DEFAULT_MODEL, DEFAULT_API_KEY, DEFAULT_BASE_URL,
    TONE_PROMPTS, LENGTH_SETTINGS,
)

LIVE_URL = "https://wikipediaparaphraser-ai-twebnxev5v4d4tagvxjen6.streamlit.app"

# ── page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Wikipedia Paraphraser AI", page_icon="🧠", layout="wide")
st.markdown("""
<style>
#MainMenu, footer, #stDecoration, .stDeployButton { visibility: hidden; }
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
}
[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.03);
    border-right: 1px solid rgba(255,255,255,0.07);
}
.hero-title {
    font-size: 2.8rem; font-weight: 800;
    background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero-sub { color: rgba(255,255,255,0.45); font-size: 1.05rem; margin-bottom: 1.4rem; }
.card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 14px; padding: 1.3rem 1.5rem; margin-bottom: 0.8rem;
}
.card-title {
    font-size: 0.85rem; font-weight: 700; color: #a78bfa;
    text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 0.5rem;
}
.card-meta  { font-size: 0.75rem; color: rgba(255,255,255,0.38); margin-bottom: 0.7rem; }
.card-text  { color: rgba(255,255,255,0.82); line-height: 1.75; font-size: 0.95rem; }
.pill {
    display:inline-block; border-radius:999px; padding:0.18rem 0.65rem;
    font-size:0.72rem; font-weight:600; margin-right:0.3rem;
}
.pill-purple { background:rgba(167,139,250,.15); color:#c4b5fd; border:1px solid rgba(167,139,250,.3); }
.pill-blue   { background:rgba(96,165,250,.12);  color:#93c5fd; border:1px solid rgba(96,165,250,.3); }
.pill-green  { background:rgba(52,211,153,.12);  color:#6ee7b7; border:1px solid rgba(52,211,153,.3); }
.hist-item {
    background:rgba(255,255,255,.04); border-radius:8px; padding:.45rem .7rem;
    margin-bottom:.35rem; font-size:.8rem; border-left:3px solid #a78bfa;
    color:rgba(255,255,255,.65);
}
a { color:#60a5fa !important; }
[data-testid="stMetricLabel"] { font-size:.72rem !important; }
[data-testid="stMetricValue"] { font-size:1.35rem !important; font-weight:700 !important; }
</style>
""", unsafe_allow_html=True)

# ── session state ──────────────────────────────────────────────────────────────
defaults = {
    "history":        [],
    "topic_input":    "",
    "last_original":  "",
    "last_para":      "",
    "last_title":     "",
    "last_lang":      "",
    "translation":    "",
    "quiz_questions": [],
    "quiz_answers":   {},
    "quiz_submitted": False,
    "quiz_topic":     "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── helpers ────────────────────────────────────────────────────────────────────
RANDOM_TOPICS = [
    "Artificial Intelligence", "Quantum Computing", "Climate Change", "Black Hole",
    "DNA", "Internet", "Bitcoin", "Renaissance", "Albert Einstein",
    "Amazon Rainforest", "Machine Learning", "Python (programming language)",
    "World War II", "Solar System", "Elon Musk", "Olympic Games",
    "Antibiotics", "Moon landing", "Blockchain", "French Revolution",
]

def word_count(t):   return len(t.split())
def sent_count(t):   return max(1, len([s for s in t.replace("?",".")
                                         .replace("!",".").split(".") if s.strip()]))
def read_time(t):
    m = word_count(t) / 200
    return f"{int(m*60)}s" if m < 1 else f"{round(m,1)} min"

def sim_score(a, b):
    sa, sb = set(a.lower().split()), set(b.lower().split())
    return round(len(sa & sb) / len(sa | sb) * 100) if sa and sb else 0

def sim_color(s):
    if s >= 50: return "#34d399", "rgba(52,211,153,.15)"
    if s >= 30: return "#fbbf24", "rgba(251,191,36,.15)"
    return "#f87171", "rgba(248,113,113,.15)"

def wiki_url(title, lang):
    return f"https://{lang}.wikipedia.org/wiki/{title.replace(' ','_')}"

# auto-fill topic from share link
url_topic = st.query_params.get("topic", "")
if url_topic and not st.session_state.topic_input:
    st.session_state.topic_input = url_topic

# ── sidebar ────────────────────────────────────────────────────────────────────
server_configured = bool(DEFAULT_API_KEY)

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    wiki_lang   = st.selectbox("Language",         ["en", "de"])
    model       = st.selectbox("Model", [
        "llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"
    ])
    tone        = st.selectbox("Tone", list(TONE_PROMPTS.keys()))
    length      = st.selectbox("Length", list(LENGTH_SETTINGS.keys()), index=1)
    temperature = st.slider("Strength", 0.0, 1.0, 0.7, 0.05,
                            help="0 = faithful · 1 = creative")
    streaming   = st.toggle("Live Streaming", value=True)

    st.markdown("---")
    if not server_configured:
        st.markdown("### 🔑 API Key")
        api_key  = st.text_input("Groq API Key", value="", type="password")
        base_url = DEFAULT_BASE_URL
        with st.expander("Get a free key"):
            st.markdown("1. [console.groq.com](https://console.groq.com)\n"
                        "2. Sign up (free)\n3. API Keys → Create\n4. Paste above")
    else:
        api_key  = DEFAULT_API_KEY
        base_url = DEFAULT_BASE_URL

    if st.session_state.history:
        st.markdown("---")
        st.markdown("### 🕘 History")
        for h in reversed(st.session_state.history[-5:]):
            st.markdown(
                f"<div class='hist-item'><b>{h['topic']}</b> ({h['lang'].upper()})<br>"
                f"{h['words_orig']} → {h['words_para']} words</div>",
                unsafe_allow_html=True,
            )
        if st.button("Clear", use_container_width=True):
            st.session_state.history = []
            st.rerun()

    st.markdown("---")
    with st.expander("ℹ️ About"):
        st.markdown("Wikipedia Paraphraser AI · TH Lübeck  \n"
                    "[GitHub ↗](https://github.com/SushantKumarPandey/Wikipedia_Paraphraser-Ai)")

# ── hero ───────────────────────────────────────────────────────────────────────
st.markdown("<div class='hero-title'>🧠 Wikipedia Paraphraser AI</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-sub'>Type a topic · get the Wikipedia summary · see the AI paraphrase.</div>",
            unsafe_allow_html=True)

# ── input row ────────────────────────────────────────────────────────────────
ci, cr, cg = st.columns([5, 1, 1.4])
with ci:
    topic = st.text_input("t", label_visibility="collapsed",
                          value=st.session_state.topic_input,
                          placeholder="e.g.  Blockchain  ·  Paris  ·  Machine Learning")
with cr:
    if st.button("🎲", help="Random topic", use_container_width=True):
        st.session_state.topic_input = random.choice(RANDOM_TOPICS)
        st.rerun()
with cg:
    go = st.button("🔍 Fetch & Paraphrase", type="primary", use_container_width=True)

# ── fetch & paraphrase ────────────────────────────────────────────────────────
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
        st.error("No summary available.")
        st.stop()

    with st.spinner("Paraphrasing …"):
        try:
            if streaming:
                parts, box = [], st.empty()
                for piece in paraphrase_stream(original, model=model, temperature=temperature,
                                               api_key=api_key, base_url=base_url,
                                               tone=tone, length=length):
                    parts.append(piece or "")
                    box.markdown(
                        f"<div class='card'><div class='card-title'>✍️ Generating…</div>"
                        f"<div class='card-text'>{''.join(parts)}</div></div>",
                        unsafe_allow_html=True)
                para = "".join(parts).strip()
                box.empty()
            else:
                para = (paraphrase(original, model=model, temperature=temperature,
                                   api_key=api_key, base_url=base_url,
                                   tone=tone, length=length) or "").strip()
        except Exception as e:
            para = ""
            st.error(f"LLM error: {e}")

    title_res = res.get("title", topic)
    lang_res  = res.get("lang",  wiki_lang)

    # persist results
    st.session_state.last_original  = original
    st.session_state.last_para      = para
    st.session_state.last_title     = title_res
    st.session_state.last_lang      = lang_res
    st.session_state.translation    = ""
    st.session_state.quiz_questions = []
    st.session_state.quiz_answers   = {}
    st.session_state.quiz_submitted = False

    # save history
    st.session_state.history.append({
        "topic": title_res, "lang": lang_res,
        "words_orig": word_count(original),
        "words_para": word_count(para) if para else 0,
    })

# ── results (persist after button click) ─────────────────────────────────────
if st.session_state.last_original:
    original  = st.session_state.last_original
    para      = st.session_state.last_para
    title_res = st.session_state.last_title
    lang_res  = st.session_state.last_lang

    # ── metrics row ──────────────────────────────────────────────────────────
    sim      = sim_score(original, para) if para else 0
    sim_fg, sim_bg = sim_color(sim)
    f_orig   = flesch_score(original)
    f_para   = flesch_score(para) if para else 0.0
    fl_orig  = flesch_label(f_orig)
    fl_para  = flesch_label(f_para)

    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("Words (original)", word_count(original))
    m2.metric("Words (paraphrase)", word_count(para) if para else 0,
              delta=word_count(para)-word_count(original) if para else None)
    m3.metric("Read time", read_time(original))
    m4.metric("Readability (orig)", f"{f_orig}  {fl_orig[1]}", help=fl_orig[0])
    m5.metric("Readability (para)", f"{f_para}  {fl_para[1]}" if para else "–", help=fl_para[0] if para else "")
    m6.metric("Word overlap", f"{sim}%" if para else "–", help="Jaccard similarity score")

    st.markdown("---")

    # ── side-by-side cards ───────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class='card'>
          <div class='card-title'>📖 Wikipedia Original</div>
          <div class='card-meta'>
            <span class='pill pill-purple'>{word_count(original)} words</span>
            <span class='pill pill-blue'>{sent_count(original)} sentences</span>
            <span class='pill pill-green'>{read_time(original)} read</span>
            &nbsp;<a href='{wiki_url(title_res, lang_res)}' target='_blank'>Full article ↗</a>
          </div>
          <div class='card-text'>{original}</div>
        </div>""", unsafe_allow_html=True)
        st.download_button("⬇ Download Original (.txt)", original.encode(),
                           file_name=f"{title_res}_original.txt", use_container_width=True)

    with c2:
        if para:
            st.markdown(f"""
            <div class='card'>
              <div class='card-title'>✍️ Paraphrase (AI)
                <span style='float:right;background:{sim_bg};color:{sim_fg};
                  border:1px solid {sim_fg};border-radius:999px;padding:1px 10px;font-size:.75rem'>
                  {sim}% overlap
                </span>
              </div>
              <div class='card-meta'>
                <span class='pill pill-purple'>{word_count(para)} words</span>
                <span class='pill pill-blue'>{sent_count(para)} sentences</span>
                <span class='pill pill-green'>{read_time(para)} read</span>
                &nbsp;Tone: <b>{tone}</b> · Length: <b>{length}</b>
              </div>
              <div class='card-text'>{para}</div>
            </div>""", unsafe_allow_html=True)
            st.download_button("⬇ Download Paraphrase (.txt)", para.encode(),
                               file_name=f"{title_res}_paraphrase.txt", use_container_width=True)
        else:
            st.markdown("<div class='card'><div class='card-text'>Paraphrase not available.</div></div>",
                        unsafe_allow_html=True)

    st.success(f"**{title_res}** ({lang_res.upper()}) · Model: `{model}` · Tone: {tone} · Length: {length}")

    # ── feature tabs ─────────────────────────────────────────────────────────
    st.markdown("### 🛠️ More Tools")
    t_kw, t_read, t_trans, t_quiz, t_compare, t_share, t_pdf = st.tabs([
        "🔑 Keywords", "📊 Readability", "🌍 Translate",
        "📝 Quiz", "⚖️ Compare Topics", "🔗 Share", "📄 PDF",
    ])

    # ── Keywords ─────────────────────────────────────────────────────────────
    with t_kw:
        st.markdown("Top keywords highlighted in the paraphrase:")
        st.markdown(
            f"<div class='card'><div class='card-text'>{highlight_keywords(para)}</div></div>",
            unsafe_allow_html=True)
        st.caption("Also highlighted in the original:")
        st.markdown(
            f"<div class='card'><div class='card-text'>{highlight_keywords(original)}</div></div>",
            unsafe_allow_html=True)

    # ── Readability ───────────────────────────────────────────────────────────
    with t_read:
        st.markdown("**Flesch Reading Ease** — higher score = easier to read (0–100)")
        r1, r2 = st.columns(2)
        with r1:
            label, icon = flesch_label(f_orig)
            st.metric("Original", f"{f_orig} / 100")
            st.markdown(f"**{icon} {label}**")
            st.progress(int(f_orig) / 100)
        with r2:
            label2, icon2 = flesch_label(f_para)
            st.metric("Paraphrase", f"{f_para} / 100")
            st.markdown(f"**{icon2} {label2}**")
            st.progress(int(f_para) / 100)
        delta = round(f_para - f_orig, 1)
        if delta > 0:
            st.success(f"The paraphrase is **{delta} points easier** to read than the original.")
        elif delta < 0:
            st.info(f"The paraphrase is **{abs(delta)} points harder** to read than the original.")
        else:
            st.info("Both texts have the same readability score.")

    # ── Translate ─────────────────────────────────────────────────────────────
    with t_trans:
        target_lang = st.selectbox("Translate paraphrase to:",
                                   ["German", "English", "Spanish", "French", "Italian", "Portuguese", "Arabic", "Hindi"])
        if st.button("🌍 Translate", use_container_width=True):
            with st.spinner(f"Translating to {target_lang} …"):
                st.session_state.translation = translate_text(para, target_lang, api_key, base_url)
        if st.session_state.translation:
            st.markdown(
                f"<div class='card'><div class='card-title'>Translation ({target_lang})</div>"
                f"<div class='card-text'>{st.session_state.translation}</div></div>",
                unsafe_allow_html=True)
            st.download_button("⬇ Download Translation (.txt)",
                               st.session_state.translation.encode(),
                               file_name=f"{title_res}_{target_lang}.txt",
                               use_container_width=True)

    # ── Quiz ──────────────────────────────────────────────────────────────────
    with t_quiz:
        if not st.session_state.quiz_questions:
            st.markdown(f"Generate a 4-question quiz about **{title_res}**:")
            if st.button("📝 Generate Quiz", use_container_width=True):
                with st.spinner("Generating quiz …"):
                    qs = generate_quiz(original, api_key, base_url)
                if qs:
                    st.session_state.quiz_questions = qs
                    st.session_state.quiz_answers   = {}
                    st.session_state.quiz_submitted = False
                    st.session_state.quiz_topic     = title_res
                    st.rerun()
                else:
                    st.error("Quiz generation failed — try again.")
        else:
            st.caption(f"Quiz: **{st.session_state.quiz_topic}**")
            for i, q in enumerate(st.session_state.quiz_questions):
                st.markdown(f"**Q{i+1}. {q['question']}**")
                chosen = st.radio("", q["options"], key=f"quiz_q{i}",
                                  index=None, label_visibility="collapsed")
                if chosen:
                    st.session_state.quiz_answers[i] = chosen[0]  # letter A/B/C/D
                st.markdown("")

            all_done = len(st.session_state.quiz_answers) == len(st.session_state.quiz_questions)

            if not st.session_state.quiz_submitted:
                sub_col, reset_col = st.columns([3, 1])
                with sub_col:
                    if st.button("✅ Submit Answers", disabled=not all_done,
                                 use_container_width=True):
                        st.session_state.quiz_submitted = True
                        st.rerun()
                with reset_col:
                    if st.button("🔄 New Quiz", use_container_width=True):
                        st.session_state.quiz_questions = []
                        st.rerun()

            if st.session_state.quiz_submitted:
                correct = sum(1 for i, q in enumerate(st.session_state.quiz_questions)
                              if st.session_state.quiz_answers.get(i) == q.get("answer"))
                total   = len(st.session_state.quiz_questions)
                score_pct = int(correct / total * 100)
                if score_pct == 100:
                    st.balloons()
                    st.success(f"🏆 Perfect score! {correct}/{total}")
                elif score_pct >= 50:
                    st.success(f"✅ Score: {correct}/{total} ({score_pct}%)")
                else:
                    st.warning(f"📚 Score: {correct}/{total} ({score_pct}%) — try reading again!")

                for i, q in enumerate(st.session_state.quiz_questions):
                    ua   = st.session_state.quiz_answers.get(i, "?")
                    ca   = q.get("answer", "?")
                    icon = "✅" if ua == ca else "❌"
                    st.markdown(f"{icon} **Q{i+1}:** Your answer **{ua}** — Correct: **{ca}**")

                if st.button("🔄 Try Again", use_container_width=True):
                    st.session_state.quiz_questions = []
                    st.session_state.quiz_answers   = {}
                    st.session_state.quiz_submitted = False
                    st.rerun()

    # ── Compare Topics ────────────────────────────────────────────────────────
    with t_compare:
        st.markdown("Compare two Wikipedia topics side by side:")
        cc1, cc2 = st.columns(2)
        with cc1:
            topic_a = st.text_input("Topic A", placeholder="e.g. Python", key="cmp_a")
            if st.button("Fetch A", use_container_width=True, key="fetch_a"):
                with st.spinner("Fetching …"):
                    res_a, err_a = fetch_wiki(topic_a, wiki_lang)
                    if (err_a or not res_a) and wiki_lang == "de":
                        res_a, err_a = fetch_wiki(topic_a, "en")
                if err_a or not res_a:
                    st.error(err_a or "Not found.")
                else:
                    st.session_state["cmp_result_a"] = res_a
            if "cmp_result_a" in st.session_state:
                r = st.session_state["cmp_result_a"]
                st.markdown(
                    f"<div class='card'><div class='card-title'>{r['title']}</div>"
                    f"<div class='card-meta'>"
                    f"<span class='pill pill-purple'>{word_count(r['extract'])} words</span>"
                    f"<a href='{wiki_url(r['title'], r['lang'])}' target='_blank'>Wikipedia ↗</a>"
                    f"</div><div class='card-text'>{r['extract']}</div></div>",
                    unsafe_allow_html=True)
        with cc2:
            topic_b = st.text_input("Topic B", placeholder="e.g. Java", key="cmp_b")
            if st.button("Fetch B", use_container_width=True, key="fetch_b"):
                with st.spinner("Fetching …"):
                    res_b, err_b = fetch_wiki(topic_b, wiki_lang)
                    if (err_b or not res_b) and wiki_lang == "de":
                        res_b, err_b = fetch_wiki(topic_b, "en")
                if err_b or not res_b:
                    st.error(err_b or "Not found.")
                else:
                    st.session_state["cmp_result_b"] = res_b
            if "cmp_result_b" in st.session_state:
                r = st.session_state["cmp_result_b"]
                st.markdown(
                    f"<div class='card'><div class='card-title'>{r['title']}</div>"
                    f"<div class='card-meta'>"
                    f"<span class='pill pill-purple'>{word_count(r['extract'])} words</span>"
                    f"<a href='{wiki_url(r['title'], r['lang'])}' target='_blank'>Wikipedia ↗</a>"
                    f"</div><div class='card-text'>{r['extract']}</div></div>",
                    unsafe_allow_html=True)
        if "cmp_result_a" in st.session_state and "cmp_result_b" in st.session_state:
            sim_cmp = sim_score(
                st.session_state["cmp_result_a"]["extract"],
                st.session_state["cmp_result_b"]["extract"],
            )
            st.info(f"Word overlap between the two topics: **{sim_cmp}%**")

    # ── Share ─────────────────────────────────────────────────────────────────
    with t_share:
        share_url = f"{LIVE_URL}/?topic={urllib.parse.quote(title_res)}"
        st.markdown("Share this topic — anyone who opens the link sees it pre-filled:")
        st.code(share_url, language="")
        st.caption("Copy the link above and paste it in your CV, email, or social media.")

    # ── PDF ───────────────────────────────────────────────────────────────────
    with t_pdf:
        st.markdown(f"Export **{title_res}** — original + paraphrase — as a PDF document:")
        if st.button("📄 Generate PDF", use_container_width=True):
            with st.spinner("Building PDF …"):
                pdf_bytes = build_pdf(title_res, original, para)
            st.download_button(
                "⬇ Download PDF", pdf_bytes,
                file_name=f"{title_res.replace(' ','_')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

# ── debug ─────────────────────────────────────────────────────────────────────
with st.expander("🐛 Debug"):
    st.write({
        "topic": topic if "topic" in dir() else "",
        "wiki_lang": wiki_lang, "model": model, "tone": tone, "length": length,
        "temperature": temperature, "streaming": streaming,
        "server_configured": server_configured,
        "history_count": len(st.session_state.history),
        "quiz_questions": len(st.session_state.quiz_questions),
    })

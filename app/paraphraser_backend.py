import os
import re
import json
import collections
import urllib.parse
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

HEADERS = {
    "User-Agent": "Wikipedia-Paraphraser/1.0",
    "Accept": "application/json",
    "Accept-Language": "de,en;q=0.8"
}

DEFAULT_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
DEFAULT_API_KEY  = os.getenv("LLM_API_KEY", "")
DEFAULT_MODEL    = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

# ── tone & length presets ─────────────────────────────────────────────────────
TONE_PROMPTS = {
    "Default":
        "Paraphrase the input text clearly, precisely and faithfully to the facts. Do not invent new facts.",
    "Simple":
        "Rewrite the following text in simple, everyday language anyone can understand. Keep all facts.",
    "Academic":
        "Rewrite the following text in formal academic style with precise vocabulary. Keep all facts.",
    "Bullet Points":
        "Rewrite the following text as concise bullet points, each starting with •. Keep all key facts.",
    "ELI5":
        "Explain the following text as if teaching a 5-year-old. Use very simple words and fun analogies.",
}

LENGTH_SETTINGS = {
    "Short":    {"max_tokens": 150, "instruction": " Keep it to 2-3 sentences maximum."},
    "Medium":   {"max_tokens": 500, "instruction": ""},
    "Detailed": {"max_tokens": 900, "instruction": " Be thorough and expand with more context."},
}

STOP_WORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with","by",
    "from","is","are","was","were","be","been","being","have","has","had","do",
    "does","did","will","would","could","should","may","might","it","its","this",
    "that","these","those","he","she","they","we","you","i","his","her","their",
    "our","your","my","also","as","which","who","what","when","where","how","not",
    "no","so","if","then","than","into","about","after","before","during","while",
    "all","more","most","other","some","such","there","here","very","just","one",
    "two","three","can","over","new","use","used","using","make","made","first",
}


def _client(api_key: str, base_url: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url)


# ── Wikipedia ─────────────────────────────────────────────────────────────────
def fetch_wiki(title: str, lang: str = "en", timeout: int = 10):
    url = (
        f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
        f"{urllib.parse.quote(title.strip())}?redirect=true"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if not r.ok:
            return None, f"Wikipedia error (HTTP {r.status_code})"
        data = r.json()
        if data.get("type") == "disambiguation":
            return None, "Disambiguation page — try a more specific title."
        extract = (data.get("extract") or "").strip()
        if not extract:
            return None, "No summary found for this topic."
        return {"title": data.get("title") or title, "extract": extract, "lang": lang}, None
    except requests.RequestException as e:
        return None, f"Network error: {e}"


# ── paraphrase ────────────────────────────────────────────────────────────────
def paraphrase(text: str, model: str, temperature: float, api_key: str, base_url: str,
               tone: str = "Default", length: str = "Medium") -> str:
    if not text.strip():
        return ""
    cfg    = LENGTH_SETTINGS.get(length, LENGTH_SETTINGS["Medium"])
    system = TONE_PROMPTS.get(tone, TONE_PROMPTS["Default"]) + cfg["instruction"]
    resp   = _client(api_key, base_url).chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": text}],
        temperature=temperature,
        max_tokens=cfg["max_tokens"],
    )
    return (resp.choices[0].message.content or "").strip()


def paraphrase_stream(text: str, model: str, temperature: float, api_key: str, base_url: str,
                      tone: str = "Default", length: str = "Medium"):
    if not text.strip():
        return
    cfg    = LENGTH_SETTINGS.get(length, LENGTH_SETTINGS["Medium"])
    system = TONE_PROMPTS.get(tone, TONE_PROMPTS["Default"]) + cfg["instruction"]
    stream = _client(api_key, base_url).chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": text}],
        stream=True,
        temperature=temperature,
        max_tokens=cfg["max_tokens"],
    )
    for chunk in stream:
        if chunk.choices and not chunk.choices[0].finish_reason:
            piece = chunk.choices[0].delta.content or ""
            if piece:
                yield piece


# ── keyword highlight (no LLM) ────────────────────────────────────────────────
def highlight_keywords(text: str, top_n: int = 8) -> str:
    import html as _html
    words = re.findall(r"[a-zA-Z]+", text.lower())
    freq  = collections.Counter(w for w in words if len(w) > 4 and w not in STOP_WORDS)
    keywords = {w for w, _ in freq.most_common(top_n)}
    result = _html.escape(text)   # escape BEFORE adding mark tags
    for kw in keywords:
        result = re.sub(
            rf"\b({re.escape(kw)})\b",
            r'<mark style="background:rgba(167,139,250,0.35);color:#c4b5fd;'
            r'border-radius:3px;padding:0 3px;font-weight:600">\1</mark>',
            result, flags=re.IGNORECASE,
        )
    return result


# ── readability (Flesch-Kincaid) ──────────────────────────────────────────────
def _syllables(word: str) -> int:
    return max(1, len(re.findall(r"[aeiouy]+", re.sub(r"[^a-z]", "", word.lower()))))

def flesch_score(text: str) -> float:
    words     = text.split()
    if not words:
        return 0.0
    sentences = max(1, len(re.findall(r"[.!?]+", text)))
    syllables = sum(_syllables(w) for w in words)
    score     = 206.835 - 1.015 * (len(words) / sentences) - 84.6 * (syllables / len(words))
    return round(max(0.0, min(100.0, score)), 1)

def flesch_label(score: float) -> tuple:
    if score >= 70: return "Easy",           "🟢"
    if score >= 50: return "Moderate",       "🟡"
    if score >= 30: return "Difficult",      "🟠"
    return           "Very Difficult",       "🔴"


# ── translate ─────────────────────────────────────────────────────────────────
def translate_text(text: str, target_lang: str, api_key: str, base_url: str) -> str:
    resp = _client(api_key, base_url).chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": f"Translate the following text to {target_lang}. Output only the translation, no explanations."},
            {"role": "user",   "content": text},
        ],
        temperature=0.2,
        max_tokens=800,
    )
    return (resp.choices[0].message.content or "").strip()


# ── quiz generator ────────────────────────────────────────────────────────────
def generate_quiz(text: str, api_key: str, base_url: str) -> list:
    prompt = (
        "Generate exactly 4 multiple-choice comprehension questions from the text below.\n"
        "Respond ONLY with a valid JSON array, no markdown, no extra text:\n"
        '[{"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A"}]\n'
        "The 'answer' field is just the correct letter (A, B, C, or D).\n\n"
        f"Text:\n{text[:1500]}"
    )
    resp = _client(api_key, base_url).chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=900,
    )
    raw = (resp.choices[0].message.content or "").strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
    try:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        return json.loads(match.group()) if match else []
    except Exception:
        return []


# ── PDF export ────────────────────────────────────────────────────────────────
def build_pdf(title: str, original: str, para: str) -> bytes:
    from fpdf import FPDF

    def safe(s: str) -> str:
        return s.encode("latin-1", "replace").decode("latin-1")

    pdf = FPDF()
    pdf.set_margins(20, 20, 20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(0, 10, safe(title))
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(140, 140, 140)
    pdf.cell(0, 6, "Generated by Wikipedia Paraphraser AI", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(200, 200, 200)
    pdf.line(20, pdf.get_y() + 2, 190, pdf.get_y() + 2)
    pdf.ln(6)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Wikipedia Original", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, safe(original))
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "AI Paraphrase", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, safe(para))

    return bytes(pdf.output())

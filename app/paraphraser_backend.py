import os
import urllib.parse
import requests
from openai import OpenAI
from dotenv import load_dotenv

HEADERS = {
    "User-Agent": "THL-Paraphrasierer/1.0 (+https://uber-16703.edu.k8s.th-luebeck.dev; contact: <deine THL-Mail>)",
    "Accept": "application/json",
    "Accept-Language": "de,en;q=0.8"
}

load_dotenv()
MYLAB_BASE_URL = os.getenv("MYLAB_BASE_URL", "https://models.mylab.th-luebeck.dev/v1")
MYLAB_API_KEY  = os.getenv("MYLAB_API_KEY", "local-dev")
DEFAULT_MODEL  = os.getenv("MYLAB_MODEL", "llama-3.3-70b")

client = OpenAI(base_url=MYLAB_BASE_URL, api_key=MYLAB_API_KEY)

def fetch_wiki(title: str, lang: str = "de", timeout: int = 10):
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title.strip())}?redirect=true"
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if not r.ok:
            return None, f"Wikipedia-Fehler (HTTP {r.status_code}) für {url}"
        data = r.json()
        if data.get("type") == "disambiguation":
            return None, "Begriffsklärungsseite – bitte präziser eingeben (z. B. „Blockchain (Informatik)“)."
        extract = (data.get("extract") or "").strip()
        if not extract:
            return None, "Keine Kurz-Zusammenfassung gefunden."
        return {"title": data.get("title") or title, "extract": extract, "lang": lang}, None
    except requests.RequestException as e:
        return None, f"Netzwerkfehler: {e}"

def paraphrase(text: str, model: str, temperature: float) -> str:
    if not text.strip():
        return ""
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Paraphrasiere den Eingabetext klar, präzise und faktengetreu. Keine neuen Fakten erfinden."},
            {"role": "user", "content": text},
        ],
        temperature=temperature,
        max_tokens=800,
    )
    return (resp.choices[0].message.content or "").strip()

def paraphrase_stream(text: str, model: str, temperature: float):
    if not text.strip():
        return ""
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Paraphrasiere den Eingabetext klar, präzise und faktengetreu. Keine neuen Fakten erfinden."},
            {"role": "user", "content": text},
        ],
        stream=True,
        temperature=temperature,
        max_tokens=800,
    )
    for chunk in stream:
        if chunk.choices and not chunk.choices[0].finish_reason:
            piece = chunk.choices[0].delta.content or ""
            if piece:
                yield piece

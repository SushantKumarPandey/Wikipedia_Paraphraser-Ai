import os
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

# Default: Groq free API (OpenAI-compatible, supports Llama 3.3-70b)
DEFAULT_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
DEFAULT_API_KEY  = os.getenv("LLM_API_KEY", "")
DEFAULT_MODEL    = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")


def _client(api_key: str, base_url: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url)


def fetch_wiki(title: str, lang: str = "de", timeout: int = 10):
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
            return None, "Disambiguation page — try a more specific title (e.g. 'Blockchain (technology)')."
        extract = (data.get("extract") or "").strip()
        if not extract:
            return None, "No summary found for this topic."
        return {"title": data.get("title") or title, "extract": extract, "lang": lang}, None
    except requests.RequestException as e:
        return None, f"Network error: {e}"


def paraphrase(text: str, model: str, temperature: float, api_key: str, base_url: str) -> str:
    if not text.strip():
        return ""
    client = _client(api_key, base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Paraphrase the input text clearly, precisely and faithfully to the facts. Do not invent new facts."},
            {"role": "user", "content": text},
        ],
        temperature=temperature,
        max_tokens=800,
    )
    return (resp.choices[0].message.content or "").strip()


def paraphrase_stream(text: str, model: str, temperature: float, api_key: str, base_url: str):
    if not text.strip():
        return
    client = _client(api_key, base_url)
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Paraphrase the input text clearly, precisely and faithfully to the facts. Do not invent new facts."},
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

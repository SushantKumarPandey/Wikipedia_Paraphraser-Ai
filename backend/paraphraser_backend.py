import os
import urllib.parse
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DEFAULT_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
DEFAULT_API_KEY  = os.getenv("LLM_API_KEY", "")
DEFAULT_MODEL    = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

WIKI_HEADERS = {"User-Agent": "WikiParaphraser/1.0 (student project)"}


def fetch_wiki(topic, lang="en"):
    url = (
        f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
        f"{urllib.parse.quote(topic.strip())}?redirect=true"
    )
    try:
        r = requests.get(url, headers=WIKI_HEADERS, timeout=8)
        if not r.ok:
            return None, f"Wikipedia returned HTTP {r.status_code}"
        data = r.json()
        if data.get("type") == "disambiguation":
            return None, "That's a disambiguation page — try a more specific title."
        text = (data.get("extract") or "").strip()
        if not text:
            return None, "No summary found for this topic."
        return {"title": data.get("title", topic), "extract": text, "lang": lang}, None
    except requests.RequestException as e:
        return None, f"Network error: {e}"


def paraphrase_stream(text, api_key, base_url, model, temperature=0.7):
    client = OpenAI(api_key=api_key, base_url=base_url)
    system = (
        "Paraphrase the following text clearly and faithfully. "
        "Keep all facts intact. Do not add anything that isn't in the original."
    )
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": text},
        ],
        temperature=temperature,
        max_tokens=600,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and not chunk.choices[0].finish_reason:
            piece = chunk.choices[0].delta.content
            if piece:
                yield piece
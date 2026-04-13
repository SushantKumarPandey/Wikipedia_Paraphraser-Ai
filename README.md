# Wikipedia Paraphraser AI

A Streamlit web app that fetches Wikipedia article summaries and rewrites them using an AI language model. Built as a university project at **TH Lübeck**.

![App Architecture](visualization.png)

---

## Features

- Search any topic (e.g. *Blockchain*, *Paris*, *Artificial Intelligence*)
- Fetches the short Wikipedia summary via the Wikipedia REST API
- Paraphrases it using an LLM via any OpenAI-compatible API (default: **Groq / Llama 3.3-70b** — free)
- German / English support with automatic fallback
- Optional streaming output while the LLM generates text
- Side-by-side view: Original vs. Paraphrase
- Download original and paraphrase as `.txt`
- Adjustable creativity (temperature slider)

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Python, Streamlit |
| Backend | `requests`, `openai`, `python-dotenv` |
| LLM API | OpenAI-compatible (Groq / Llama 3.3-70b by default) |
| Container | Docker |
| CI/CD | GitLab CI/CD |
| Deployment | Kubernetes (Deployment, Service, Ingress) |

---

## Quick Start — Get a Free API Key

This app uses [Groq](https://console.groq.com) (free tier, no credit card needed):

1. Sign up at **https://console.groq.com**
2. Go to **API Keys → Create API key**
3. Paste the key into the sidebar when running the app

Works with any OpenAI-compatible API (OpenAI, Ollama, LM Studio, etc.).

---

## Run Locally

```bash
git clone https://github.com/SushantKumarPandey/Wikipedia_Paraphraser-Ai.git
cd Wikipedia_Paraphraser-Ai/app
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open **http://localhost:8501**, enter your Groq API key in the sidebar, and start paraphrasing.

### Optional: pre-configure via `.env`

Create `app/.env` to avoid entering the key every time:

```env
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=your-groq-api-key
LLM_MODEL=llama-3.3-70b-versatile
```

---

## Run with Docker

```bash
docker build -t paraphraser:local ./app
docker run --rm -p 8501:8501 --env-file ./app/.env paraphraser:local
```

---

## Deploy on Streamlit Community Cloud (free)

1. Fork this repo on GitHub
2. Go to **https://share.streamlit.io** and sign in with GitHub
3. Click **New app** → select this repo
4. Set **Main file path**: `app/app.py`
5. Under **Secrets**, add:
   ```toml
   LLM_BASE_URL = "https://api.groq.com/openai/v1"
   LLM_API_KEY = "your-groq-api-key"
   LLM_MODEL = "llama-3.3-70b-versatile"
   ```
6. Click **Deploy** — you get a public `*.streamlit.app` URL

---

## Architecture

```
User Input (Topic)
    │
    ▼
fetch_wiki() ──► Wikipedia REST API
                 GET /{lang}.wikipedia.org/api/rest_v1/page/summary/{title}
    │
    ▼
paraphrase() / paraphrase_stream()
    └──► POST /chat/completions  (OpenAI-compatible LLM)
    │
    ▼
Streamlit UI
    ├── Left column:  Original Wikipedia summary
    └── Right column: AI Paraphrase
         + Download buttons (.txt)
```

---

## Project Structure

```
├── app/
│   ├── app.py                  # Streamlit UI
│   ├── paraphraser_backend.py  # Wikipedia fetch + LLM calls
│   ├── requirements.txt
│   └── Dockerfile
├── deploy/
│   ├── app-dep.yaml            # Kubernetes Deployment
│   ├── app-svc.yaml            # Kubernetes Service
│   └── project-ing.yaml        # Kubernetes Ingress
├── .gitlab-ci.yml              # CI/CD pipeline
└── visualization.png
```

---

## Limitations

- Wikipedia summaries can be brief or missing for niche topics
- Paraphrase quality depends on the model and temperature setting
- Requires a Groq (or other OpenAI-compatible) API key

---

*University project — TH Lübeck*

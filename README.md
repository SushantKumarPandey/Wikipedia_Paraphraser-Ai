# Wikipedia Paraphraser AI

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white)
![LLM](https://img.shields.io/badge/LLM-Llama%203.3--70b-blueviolet)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

A web application that fetches Wikipedia article summaries and rewrites them using a large language model.  
Type a topic, get the original Wikipedia text, and see an AI-generated paraphrase side by side — with one-click download.

> University project — TH Lübeck · Built with Python & Streamlit · Powered by Groq / Llama 3.3-70b

---

## Live Demo

> **[Try it here →](https://wikipediaparaphraser-ai-twebnxev5v4d4tagvxjen6.streamlit.app)** — no sign-up, no API key needed, works instantly

![App preview](visualization.png)

---

## Features

| Feature | Description |
|---|---|
| Wikipedia fetch | Retrieves the official short summary via Wikipedia REST API |
| AI paraphrase | Rewrites the text using Llama 3.3-70b (via Groq, free) |
| DE / EN support | Searches in German first, falls back to English automatically |
| Streaming output | Watch the AI generate text in real time |
| Side-by-side view | Compare original and paraphrase at a glance |
| Download | Export original or paraphrase as `.txt` |
| Flexible LLM | Works with any OpenAI-compatible API (Groq, OpenAI, Ollama, LM Studio) |
| Temperature control | Adjust creativity from 0.0 (faithful) to 1.0 (creative) |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| UI Framework | Streamlit |
| LLM Client | `openai` (OpenAI-compatible) |
| Default LLM | Groq API — `llama-3.3-70b-versatile` (free tier) |
| HTTP | `requests`, `python-dotenv` |
| Container | Docker |
| Orchestration | Kubernetes (Deployment, Service, Ingress) |
| CI/CD | GitLab CI/CD |

---

## Getting Started

### 1. Get a free API key (2 minutes)

This app runs on [Groq](https://console.groq.com) — free, no credit card required.

1. Sign up at **https://console.groq.com**
2. Go to **API Keys → Create API key**
3. Copy the key

Any OpenAI-compatible API also works (OpenAI, Ollama, LM Studio).

---

### 2. Run locally

```bash
git clone https://github.com/SushantKumarPandey/Wikipedia_Paraphraser-Ai.git
cd Wikipedia_Paraphraser-Ai/app

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

Open **http://localhost:8501** and paste your API key in the sidebar.

**Optional — skip the sidebar by using a `.env` file:**

```env
# app/.env
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=your-groq-api-key
LLM_MODEL=llama-3.3-70b-versatile
```

---

### 3. Run with Docker

```bash
docker build -t paraphraser ./app
docker run --rm -p 8501:8501 --env-file ./app/.env paraphraser
```

---

### 4. Deploy on Streamlit Community Cloud (free public URL)

1. Fork this repo on GitHub
2. Go to **https://share.streamlit.io** → sign in with GitHub
3. **New app** → select this repo
4. Main file path: `app/app.py`
5. Under **Secrets**, add:

```toml
LLM_BASE_URL = "https://api.groq.com/openai/v1"
LLM_API_KEY  = "your-groq-api-key"
LLM_MODEL    = "llama-3.3-70b-versatile"
```

6. Click **Deploy** → you get a permanent public `*.streamlit.app` link

---

## How It Works

```
User types a topic
        │
        ▼
fetch_wiki()  ──────►  Wikipedia REST API
                        GET /{lang}.wikipedia.org/api/rest_v1/page/summary/{title}
        │
        ▼
paraphrase() / paraphrase_stream()
        └──────►  POST /chat/completions   (OpenAI-compatible LLM)
        │
        ▼
Streamlit UI
   ┌────────────────────┬────────────────────────┐
   │  Wikipedia Original│   AI Paraphrase        │
   │  (fetched text)    │   (LLM output)         │
   │  [Download .txt]   │   [Download .txt]      │
   └────────────────────┴────────────────────────┘
```

---

## Project Structure

```
Wikipedia_Paraphraser-Ai/
├── app/
│   ├── app.py                   # Streamlit UI — layout, sidebar, user interaction
│   ├── paraphraser_backend.py   # Wikipedia fetch + LLM paraphrase logic
│   ├── requirements.txt         # Python dependencies
│   └── Dockerfile               # Container image definition
├── deploy/
│   ├── app-dep.yaml             # Kubernetes Deployment
│   ├── app-svc.yaml             # Kubernetes Service (ClusterIP)
│   └── project-ing.yaml         # Kubernetes Ingress + TLS
├── .gitlab-ci.yml               # CI/CD pipeline (build → deploy)
├── visualization.png            # Architecture diagram
└── README.md
```

---

## Notes

- Wikipedia summaries may be short or unavailable for niche topics
- Paraphrase quality varies with model choice and temperature setting
- Groq free tier has generous rate limits suitable for personal/demo use

---

## Author

**Sushant Kumar Pandey**  
TH Lübeck — University of Applied Sciences  
[GitHub](https://github.com/SushantKumarPandey)

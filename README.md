# Wikipedia Paraphraser AI

A Streamlit web app that fetches Wikipedia article summaries and rewrites them using an AI language model (Llama 3.3-70b). Built as a university project at **TH Lübeck**.

![App Architecture](visualization.png)

---

## Features

- Search any topic (e.g. *Blockchain*, *Paris*, *Science*)
- Fetches the short Wikipedia summary via the Wikipedia REST API
- Paraphrases it using an OpenAI-compatible LLM (default: `llama-3.3-70b`)
- German / English support with automatic fallback (tries `de` first, then `en`)
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
| LLM API | OpenAI-compatible endpoint (myLab / Llama 3.3-70b) |
| Container | Docker |
| CI/CD | GitLab CI/CD |
| Deployment | Kubernetes (Deployment, Service, Ingress) |

---

## Run Locally

### 1. Clone & install

```bash
git clone https://github.com/<your-username>/wikipedia-paraphraser-ai.git
cd wikipedia-paraphraser-ai/app
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

Create `app/.env`:

```env
MYLAB_BASE_URL=https://models.mylab.th-luebeck.de/v1
MYLAB_API_KEY=your-api-key-here
MYLAB_MODEL=llama-3.3-70b
```

> Any OpenAI-compatible API endpoint works (e.g. OpenAI, Ollama, LM Studio).

### 3. Start the app

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Open **http://localhost:8501**

---

## Run with Docker

```bash
docker build -t paraphraser:local ./app
docker run --rm -p 8501:8501 --env-file ./app/.env paraphraser:local
```

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
- Requires an OpenAI-compatible API key to run

---

*University project — TH Lübeck*

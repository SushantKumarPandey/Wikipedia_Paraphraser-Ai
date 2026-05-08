# Wikipedia Paraphraser AI

A Streamlit web app that fetches a Wikipedia article summary and paraphrases it using an LLM. Results are shown side by side with download buttons for both texts.

> University project — TH Lübeck · Python & Streamlit · Groq / Llama 3.3-70b

---

## Features

- Fetches Wikipedia summaries via the REST API — tries German first, falls back to English
- Paraphrases the text using any OpenAI-compatible LLM (Groq by default, free)
- Live streaming output so you see the paraphrase as it generates
- Side-by-side layout to compare original and paraphrase
- Download either text as a `.txt` file
- Temperature slider to control creativity (0 = faithful, 1 = creative)
- Works with Groq, OpenAI, Ollama, LM Studio — anything OpenAI-compatible

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| UI | Streamlit |
| LLM client | `openai` SDK (OpenAI-compatible) |
| Default model | `llama-3.3-70b-versatile` via Groq |
| HTTP | `requests`, `python-dotenv` |
| Container | Docker |
| Orchestration | Kubernetes |
| CI/CD | GitLab CI/CD |

---

## Project Structure

```
backend/
  paraphraser_backend.py  Wikipedia fetch + LLM streaming

frontend/
  app.py                  Streamlit UI

assets/
  rocket.png
  visualization.png

deploy/
  app-dep.yaml            Kubernetes Deployment + Secret
  app-svc.yaml            Kubernetes Service (ClusterIP)
  project-ing.yaml        Kubernetes Ingress with TLS

Dockerfile
requirements.txt
.env.example
.gitignore
.gitlab-ci.yml
README.md
```

---

## Run locally

**1. Get a free Groq API key**

Sign up at [console.groq.com](https://console.groq.com), go to API Keys → Create. It's free.

**2. Clone and install**

```bash
git clone https://github.com/SushantKumarPandey/Wikipedia_Paraphraser-Ai.git
cd Wikipedia_Paraphraser-Ai

python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**3. Configure the API key**

Copy the example env file and fill in your key:

```bash
cp .env.example .env
```

```env
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=your_groq_key_here
LLM_MODEL=llama-3.3-70b-versatile
```

Or skip this step and enter the key in the sidebar when the app opens.

**4. Start the app**

```bash
streamlit run frontend/app.py
```

Open [http://localhost:8501](http://localhost:8501).

---

## Run with Docker

```bash
docker build -t wiki-paraphraser .
docker run -p 8501:8501 --env-file .env wiki-paraphraser
```

Open [http://localhost:8501](http://localhost:8501).

---

## Deploy to Kubernetes (GitLab CI)

Set `DEPLOY=yes` in your GitLab CI/CD variables (or run the pipeline manually with that value).

Required CI/CD variable:
- `LLM_API_KEY` — your API key, stored as a protected variable in GitLab

Pipeline stages:
1. **prepare** — creates the image pull secret in the cluster
2. **build** — builds and pushes the Docker image to the GitLab registry
3. **deploy** — applies the Deployment and Service manifests
4. **deploy (manual)** — applies the Ingress for HTTPS access

The app will be available at `https://uber-<project-id>.edu.k8s.th-luebeck.dev`.

---

## Author

**Sushant Kumar Pandey** — TH Lübeck
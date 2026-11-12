<div align="center">

# 🍽️ [RAGtaurant](https://rag-taurant.up.railway.app/)

**A fictional restaurant where AI helps guests explore the menu and its allergens.**

[![Python](https://img.shields.io/badge/Python-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-blue?logo=react&logoColor=white)](https://react.dev/)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?logo=langchain&logoColor=white)](https://www.langchain.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-green?logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Docker](https://img.shields.io/badge/Docker-darkblue?logo=docker&logoColor=white)](https://www.docker.com/)
[![AWS](https://custom-icon-badges.demolab.com/badge/S3-orange.svg?logo=aws&logoColor=white)](https://aws.amazon.com)
[![Railway](https://img.shields.io/badge/Railway-grey?logo=railway)](https://rag-taurant.up.railway.app/)
[![License: AGPL v3](https://img.shields.io/badge/Open%20Source-darkgrey?logo=opensourceinitiative&logoColor=white)](./LICENSE)


**[🌐 Open RAGtaurant](https://rag-taurant.up.railway.app/)**

[The story](#-the-story) · [Key features](#-key-features) · [How I built it](#️-how-i-built-it) ·
[Architecture](#️-architecture) · [Next steps](#-next-steps) · [Getting started](#-getting-started) ·
[CI/CD](#-cicd) · [License](#-license)

</div>

## 📖 The story

People close to me have serious food allergies, so I have often paid attention to how restaurants describe their
dishes and allergens. I noticed that this information is not always as clear as it should be.

I built RAGtaurant to explore a modern way to make that information easier to navigate, using AI and
Retrieval-Augmented Generation (RAG), technologies I learned about through my professional experience.
The restaurant and its menu are fictional; this project is a portfolio demonstration.

**Allergy information is illustrative.** The assistant can make mistakes and cannot guarantee the absence of an
allergen or cross-contact. Always confirm ingredients and preparation with restaurant staff.

## ✨ Key features

- 🍽️ **Andalusian menu:** Explore fictional dishes and drinks with dietary labels and recorded allergens.
- 🤖 **RAG assistant:** Ask about the menu, restaurant information or local weather in a conversation grounded in
  retrieved content.
- 📅 **Reservations:** Create, look up, update and cancel a reservation; lookup and changes require its code and
  contact details.
- ☀️ **Local information:** Discover the fictional restaurant, San Juan del Puerto and the local weather forecast.
- 🐳 **Local and deployed:** Run the stack with Docker Compose or visit the Railway deployment.

The demo sends chat content and text used for embeddings to Google Gemini. Use fictional contact details when
trying reservations; see the [development guide](./docs/local-development.md) for privacy and operational notes.

## 🛠️ How I built it

I used this project to explore four challenges:

1. 🧠 **From local models to grounded AI:** I first evaluated local models with Ollama, but latency and inconsistent
   grounding on the available hardware led me to move to hosted Google Gemini models. I combined Gemini, LangChain
   tools and embeddings with guardrails intended to keep answers grounded and within the app's scope, while
   recognizing that these safeguards cannot eliminate every risk. Read the
   [local model research](./docs/research/local-model-selection.md).
2. 🔗 **Connecting systems:** I integrated Google Gemini for chat and embeddings, Open-Meteo for weather forecasts,
   and S3-compatible storage for images: LocalStack locally and a Railway bucket in production.
3. 🍃 **Search across environments:** I used MongoDB Atlas Local vector search for development and an in-process
   cosine similarity fallback for Railway's MongoDB, where Atlas Vector Search is not available.
4. 🚀 **From local to live:** I built a React interface and FastAPI backend, orchestrated local services with Docker
   Compose, added GitHub Actions checks and deployed separate services to Railway.

## 🏗️ Architecture

```mermaid
flowchart LR
    subgraph Pipeline["🔁 GitHub CI/CD"]
        direction LR
        Develop["🌿 develop"] --> PR["🔀 Pull request"]
        PR --> CI["✅ GitHub Actions<br/>Backend · Frontend · Secrets · Docker"]
        CI -->|Checks pass and merge| Main["🌳 main"]
    end

    subgraph Railway["🚂 Railway"]
        direction LR
        Frontend["🌐 Frontend · public<br/>React + Nginx"]
        Backend["⚙️ Backend · private<br/>FastAPI + LangChain"]
        Mongo[("🍃 MongoDB<br/>menu · reservations · embeddings")]
        Volume[("💾 Persistent volume")]
        Bucket[("🪣 Private S3-compatible bucket<br/>menu images")]
        Frontend -->|API and images| Backend
        Backend --> Mongo
        Mongo --- Volume
        Backend -->|Authenticated HTTPS| Bucket
    end

    User["👤 Guest"] -->|HTTPS| Frontend
    Backend -->|Chat and embeddings| Gemini["✨ Google Gemini"]
    Backend -->|Weather forecast| Weather["☀️ Open-Meteo"]
    Main -->|Deploy| Frontend
    Main -->|Deploy| Backend

    classDef github fill:#e8eaf6,stroke:#3949ab,color:#1a237e
    classDef service fill:#e0f2f1,stroke:#00897b,color:#004d40
    classDef data fill:#fff3e0,stroke:#ef6c00,color:#4e2600
    class Develop,PR,CI,Main github
    class Frontend,Backend service
    class Mongo,Volume,Bucket data
```

In local development, MongoDB Atlas Local and LocalStack replace the Railway database and bucket.

## 🔭 Next steps

- **Evaluate the assistant:** Build a repeatable evaluation for retrieval quality, allergen questions and response latency.
- **Automate asset deployment:** Provision and synchronize the Railway bucket as part of a controlled deployment pipeline.
- **Strengthen reservation security:** Improve access controls and privacy protections for customer data.

## 🚀 Getting started

Clone the repository, copy `.env.example` to `.env` and add a Google Gemini API key:

```bash
git clone https://github.com/patriciorr/rag-taurant.git
cd rag-taurant
cp .env.example .env
# Set GOOGLE_API_KEY in .env; never commit the file.
docker compose up -d --build
```

Open [localhost](http://localhost). For prerequisites, manual setup, tests, configuration and deployment details, see
the [development guide](./docs/local-development.md).

## 🧪 CI/CD

Changes move from `develop` to `main` through a pull request. GitHub Actions checks the backend, frontend, secrets
and Docker builds; Railway deploys the connected services from `main`.

## 📜 License

Copyright © 2026 Patricio Rodríguez Ramírez. Licensed under the
[GNU Affero General Public License v3.0 only](./LICENSE). The menu photographs have separate
[source and licensing information](./docs/image-attribution.md).

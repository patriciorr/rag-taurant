<div align="center">

# 🍽️ RAGtaurant

**A modern, full-stack AI-powered restaurant platform with Retrieval-Augmented Generation (RAG).**

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.x-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5.x-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3%2B-1C3C3C?logo=langchain&logoColor=white)](https://www.langchain.com/)
[![MongoDB Atlas Local](https://img.shields.io/badge/MongoDB%20Atlas%20Local-Vector_Search-47A248?logo=mongodb&logoColor=white)](https://www.mongodb.com/products/platform/atlas-vector-search)
[![Ollama](https://img.shields.io/badge/Ollama-Qwen3_8B-black?logo=ollama&logoColor=white)](https://ollama.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![AWS](https://custom-icon-badges.demolab.com/badge/AWS-S3-%23FF999.svg?logo=aws&logoColor=white)](https://aws.amazon.com)
[![License: All Rights Reserved](https://img.shields.io/badge/License-All%20Rights%20Reserved-lightgrey?logo=data:image/svg%2bxml;base64,PHN2ZyB3aWR0aD0iMTk3cHgiIGhlaWdodD0iMTk3cHgiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgdmVyc2lvbj0iMS4xIj4KCTxjaXJjbGUgY3g9Ijk4IiBjeT0iOTgiIHI9Ijk4IiBmaWxsPSJibGFjayIvPgoJPGNpcmNsZSBjeD0iOTgiIGN5PSI5OCIgcj0iNzgiIGZpbGw9IndoaXRlIi8+Cgk8Y2lyY2xlIGN4PSI5OCIgY3k9Ijk4IiByPSI1NSIgZmlsbD0iYmxhY2siLz4KCTxjaXJjbGUgY3g9Ijk4IiBjeT0iOTgiIHI9IjMwIiBmaWxsPSJ3aGl0ZSIvPgoJPHJlY3QgeD0iMTE1IiB5PSI4NSIgd2lkdGg9IjQ1IiBoZWlnaHQ9IjI1IiBmaWxsPSJ3aGl0ZSIvPgo8L3N2Zz4=)](./LICENSE)

[Key Features](#-key-features) • [Tech Stack](#-tech-stack) • [Project Structure](#-project-structure) • [Getting Started](#-getting-started) • [API & Tools](#-api--tools) • [License](#-license--usage-restrictions)

</div>

---

## 📖 Overview

**RAGtaurant** is a full-stack, intelligent restaurant application that seamlessly bridges modern web design with local AI agent technology. By leveraging **Retrieval-Augmented Generation (RAG)**, **LangChain Tool Calling**, and local Ollama embeddings stored in **MongoDB Atlas Local** vector indexes, RAGtaurant provides customers with an interactive assistant capable of answering menu queries, checking local weather conditions, and preparing table reservations.

The application features a sleek **React + Material UI** frontend served through **Nginx**, backed by a high-performance **FastAPI** REST API and a containerized **Ollama** LLM runner.

---

## ✨ Key Features

- 🤖 **AI-Powered Gourmet Assistant:** Local chatbot powered by **Qwen3 8B** with tool calling and conversational memory.
- 🥗 **Andalusian digital menu:** A responsive Spanish-first restaurant experience with illustrated entrantes, principales and postres, clear vegetarian/vegan badges, listed allergens and an allergy safety notice.
- 📅 **Reservation management:** Create, look up, update and cancel reservations. Protected lookup and changes require the reservation code, email and phone.
- 🪣 **Local photo storage:** Licensed stock images are seeded into a local-only S3-compatible LocalStack bucket; no AWS account or credentials are needed.
- 🔍 **Vector Search & RAG:** Semantic search over menu items and restaurant information using **MongoDB Atlas Local** vector search and local Ollama embeddings.
- 🛠️ **Autonomous Agent Tools:**
  - 📖 `search_menu_and_info`: Performs vector similarity search for dish recommendations and details.
  - ☀️ `get_weather_forecast`: Retrieves the Open-Meteo forecast for the restaurant's configured location, covering today and the next 13 days.
  - 📅 `make_table_reservation`: Handles table reservations with date, time, and guest count validation.
- ⚡ **Asynchronous REST API:** Lightweight FastAPI backend with CORS middleware and Pydantic schema validations.
- 🐳 **Full-Stack Docker Orchestration:** Complete multi-container setup (Nginx Frontend, FastAPI Backend, Ollama Engine) managed via Docker Compose.

---

## 🛠️ Tech Stack

### Frontend & Web Server

| Technology                 | Badge                                                                                               | Purpose                                       |
| :------------------------- | :-------------------------------------------------------------------------------------------------- | :-------------------------------------------- |
| **React**                  | ![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB) | Single Page Application (SPA) client          |
| **Vite**                   | ![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)     | Next-generation frontend tooling              |
| **Material UI (MUI)**      | ![MUI](https://img.shields.io/badge/MUI-007FFF?style=for-the-badge&logo=mui&logoColor=white)        | Elegant UI component system and styling       |
| **Nginx**                  | ![Nginx](https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white)  | Reverse proxy & static content web server     |
| **AWS (LocalStack 4.4.0)** | ![AWS](https://img.shields.io/badge/AWS-005000?style=for-the-badge&logo=iCloud&logoColor=white)     | Local menu-image S3 bucket, seeded at startup |

### Backend, AI & Vector Database

| Technology              | Badge                                                                                                          | Purpose                                          |
| :---------------------- | :------------------------------------------------------------------------------------------------------------- | :----------------------------------------------- |
| **Python**              | ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)          | Core backend language runtime                    |
| **FastAPI**             | ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)       | Asynchronous RESTful API framework               |
| **LangChain**           | ![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white) | AI agent orchestration and tool execution        |
| **MongoDB Atlas Local** | ![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white)       | Local document and vector database               |
| **Ollama (Qwen3 8B)**   | ![Ollama](https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white)          | Local LLM inference engine with function calling |
| **Docker**              | ![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)          | Multi-container environment orchestration        |

---

## 📁 Project Structure

```text
rag-taurant/
├── 📂 backend/                   # FastAPI Backend & RAG Engine
│   ├── 📂 app/
│   │   ├── 📂 api/               # API endpoints (menu, chat)
│   │   ├── 📂 core/              # Global settings & environment configs
│   │   ├── 📂 db/                # Database setup and seed data loader
│   │   └── 📂 rag/               # LangChain agent, prompt engineering & tools
│   ├── 📄 Dockerfile             # Backend container image definition
│   ├── 📄 main.py                # FastAPI entry point & CORS configuration
│   └── 📄 requirements.txt       # Python dependencies
├── 📂 frontend/                  # React + MUI Client Application
│   ├── 📂 src/
│   │   ├── 📂 components/        # UI components (ChatWidget, Navbar, MenuCard)
│   │   ├── 📂 services/          # API client service (Axios)
│   │   ├── 📂 theme/             # Material UI custom theme palette
│   │   ├── 📄 App.jsx            # Main view
│   │   └── 📄 main.jsx           # React app entry point
│   ├── 📄 Dockerfile             # Multi-stage Docker build for React + Nginx
│   ├── 📄 nginx.conf             # Nginx reverse proxy routing
│   ├── 📄 package.json           # Frontend dependencies
│   └── 📄 vite.config.js         # Vite configuration
├── 📄 .gitignore                 # Exclusion rules for git version control
├── 📄 docker-compose.yml         # Full-stack container orchestration
└── 📄 README.md                  # Project documentation
```

---

## 🚀 Getting Started

### Prerequisites

Ensure you have installed on your host system:

- **Docker Desktop** / **Docker Engine**: `v24.0+`
- **Docker Compose**: `v2.20+`
- _(Optional)_ **Python 3.11+** & **Node.js 20+** (if developing locally without Docker)

---

### 🐳 Quick Start with Docker Compose (Recommended)

Launch the stack (Nginx, React, FastAPI, MongoDB Atlas Local, and Ollama) with Docker Compose:

#### 1. Clone the Repository

```bash
git clone https://github.com/patriciorr/rag-taurant.git
cd rag-taurant
```

#### 2. Start Ollama and download the configured local models

Ollama runs in its Docker image. Pull the chat and embedding models into its persistent volume before starting the backend:

```bash
docker compose up -d ollama
docker exec ollama_restaurant ollama pull qwen3:8b
docker exec ollama_restaurant ollama pull bge-m3
```

#### 3. Start the application

```bash
docker compose up -d --build
```

#### 4. Access the Platform

- **Web Application:** `http://localhost`
- **REST API Documentation (Swagger):** `http://localhost:8000/docs`
- **Ollama Engine API:** `http://localhost:11435` (host port; container port remains `11434`)

The host port can be changed with `OLLAMA_HOST_PORT`. The backend container uses the internal Compose address `http://ollama:11434`.

If MongoDB already contains vectors made with another embedding model, reindex them before starting the backend:

```bash
docker compose up -d ollama mongodb
docker compose run --build --rm --no-deps backend python scripts/reindex_embeddings.py
```

The script generates and validates every replacement vector before changing indexes or stored embeddings. It regenerates every menu vector and every existing restaurant-knowledge vector, then updates each vector-search index to the selected model's dimension.

---

### 💻 Manual Local Development Setup

If you prefer to run services manually outside Docker:

#### 1. Start the Ollama Docker service

```bash
docker compose up -d ollama
docker exec ollama_restaurant ollama pull qwen3:8b
docker exec ollama_restaurant ollama pull bge-m3
```

The local backend defaults to `http://localhost:11435`; Ollama itself still runs inside Docker.

#### 2. Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

#### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The Vite development server proxies `/api` to `http://localhost:8000` and
`/assets` to the local S3 endpoint at `http://localhost:4566`. Start
LocalStack alongside MongoDB before opening the page to make the locally
stored photos available:

```bash
docker compose up -d --wait mongodb localstack
```

LocalStack runs only for local development/demo and is pinned to
`localstack/localstack:4.4.0`. Its startup hook idempotently creates the
`ragtaurant-assets` bucket, applies a local public-read policy, and syncs the
bundled stock photos. Both Vite and Nginx expose them through the browser-safe
same-origin `/assets/menu/...` path; the browser never needs a Docker hostname
or AWS credentials. The LocalStack endpoint is published on
`127.0.0.1:4566`, not on external interfaces.

For the full application, `docker compose up --wait` also waits for the
LocalStack image seed to finish before starting the frontend. The AI assistant
is still available from the floating chat button; browsing the menu itself
does not include search or diet/allergen filters.

The curated catalog seed adds or updates only its own stable dish IDs and
rebuilds embeddings for changed seed records. Other existing menu documents
are retained.

### Frontend Checks

```bash
cd frontend
npm ci
npm test
npm run lint
npm run build
```

Component and API contract tests use Vitest, React Testing Library and a DOM
test environment. The complete suite covers menu categories and dietary
labels, allergen guidance, reservation creation/lookup/update/cancellation,
API contact headers, and accessible error messages.

### Reservation policy

Reservations accept 1–20 guests, on the hour or half-hour between 12:00 and
23:00, on today or any of the next 13 days in the restaurant's Europe/Madrid
timezone. The UI enforces matching date/time/party-size inputs. A returned
reservation code is needed along with the original email and phone for lookup,
updates and cancellation. The displayed menu allergen information and dish
photos are illustrative; customers with allergies must always confirm
ingredients and cross-contact with restaurant staff.

See [photo source and licensing details](./docs/image-attribution.md) for the
stock-image asset list.

---

## 🧪 Running the tests

Run everything from the repository root. The backend integration tests need the
local MongoDB container; Ollama is not required.

```bash
# Frontend (Vitest + React Testing Library)
cd frontend && npm ci && npm test && npm run lint && cd ..

# Backend (pytest, unit + MongoDB integration)
pip install -r backend/requirements-dev.txt
docker compose up --wait mongodb
cd backend && python -m pytest -c pytest.ini
```

See [Frontend Checks](#frontend-checks) and [Backend Tests](#backend-tests) for
what each suite covers and how to point the integration tests at another
MongoDB instance.

---

## 📡 API & Tools

### REST API Endpoints

| Method   | Endpoint                        | Description                                     |
| :------- | :------------------------------ | :---------------------------------------------- |
| `GET`    | `/api/v1/menu/`                 | Fetches the restaurant menu                     |
| `POST`   | `/api/v1/menu/`                 | Creates a menu item                             |
| `GET`    | `/api/v1/menu/{dish_id}`        | Fetches a menu item                             |
| `PUT`    | `/api/v1/menu/{dish_id}`        | Replaces a menu item                            |
| `PATCH`  | `/api/v1/menu/{dish_id}`        | Partially updates a menu item                   |
| `DELETE` | `/api/v1/menu/{dish_id}`        | Deletes a menu item                             |
| `GET`    | `/api/v1/menu/search?query=...` | Searches menu items                             |
| `POST`   | `/api/v1/reservations/`         | Creates a reservation                           |
| `GET`    | `/api/v1/reservations/{id}`     | Reads a reservation with contact verification   |
| `PUT`    | `/api/v1/reservations/{id}`     | Replaces reservation date, time, and party size |
| `PATCH`  | `/api/v1/reservations/{id}`     | Partially updates date, time, or party size     |
| `DELETE` | `/api/v1/reservations/{id}`     | Cancels a reservation                           |
| `POST`   | `/api/v1/chat/`                 | Sends a message to the RAG Chatbot agent        |

Reservation detail, update, and cancellation requests require `X-Reservation-Email` and `X-Reservation-Phone` headers. The reservation collection intentionally has no public list endpoint.

### Backend Tests

Install the development test dependencies and start only the local MongoDB service:

```bash
pip install -r backend/requirements-dev.txt
docker compose up --wait mongodb
cd backend
python -m pytest -c pytest.ini
```

The `mongodb` service runs MongoDB Atlas Local from the official `mongodb/mongodb-atlas-local` image and publishes port `27017` for tests run on the host. `--wait` does not return until its health check succeeds. The full test command includes both unit and MongoDB integration tests; Ollama is not required because embeddings are stubbed.

The integration tests use a unique `rag_taurant_test_*` database per test and drop it during cleanup. To use another MongoDB instance, set `TEST_MONGODB_URI` before running the tests and ensure it points to a disposable test deployment; test databases are deleted automatically.

### Local Model Evaluation

The versioned Spanish evaluation set compares Qwen3 8B with Llama 3.2 3B for tool selection, arguments, and grounded responses; it compares BGE-M3 with Nomic Embed Text for retrieval. Reservation tools only return canned simulated results and never modify MongoDB. The tests use deterministic inputs and do not call Ollama or the network.

With the Ollama container running and all four models pulled, run the CPU and GPU profiles from `backend/`:

```bash
python scripts/evaluate_local_models.py \
  --base-url http://localhost:11435 \
  --hardware cpu,gpu \
  --output ../docs/research/local-model-benchmark.json
```

The runner records total response latency, peak Ollama-container memory, peak GPU memory, tool/argument accuracy, grounding, and retrieval Recall@3/MRR. It unloads each model between profiles. See [the model-selection report](./docs/research/local-model-selection.md) for the chosen defaults and measured results.

### Agent Autonomous Tools

1. **`search_menu(query, vegan_only, vegetarian_only, exclude_allergens, available_only)`**: Searches the menu using stored vector matches and structured dietary/allergen filters.
2. **`search_info(query)`**: Queries the restaurant knowledge collection through MongoDB vector search.
3. **`get_weather_forecast(date: str | None)`**: Retrieves the 14-day Open-Meteo forecast or a specific available date; a verified active reservation date can provide the context.
4. **`make_table_reservation(customer_name, email, phone, date, time, guests)`**: Prepares and summarizes a new reservation without creating it until explicit confirmation.
5. **`get_table_reservation(reservation_id, email, phone)`**: Verifies and reads an existing reservation.
6. **`edit_table_reservation(reservation_id, email, phone, date, time, guests)`**: Prepares a reservation change without mutating it before confirmation.
7. **`delete_table_reservation(reservation_id, email, phone)`**: Prepares a cancellation without applying it before confirmation.

---

## 🔒 Security & Best Practices

- 🔐 **Environment Configuration:** Sensitive URLs and model choices are parameterized via Pydantic settings.
- 🛡️ **Git Hygiene:** Local dependencies (`node_modules/`, `.venv/`) and build artifacts are strictly excluded in `.gitignore`.
- 🌐 **CORS Management:** Managed via FastAPI `CORSMiddleware` and Nginx reverse proxying to prevent cross-origin errors in production setups.

---

## 📜 License & Usage Restrictions

<div align="center">

Copyright (c) 2026 Patricio Rodríguez Ramírez. All rights reserved.

</div>

**1. PROPRIETARY RIGHTS & RESTRICTIONS**
This source code and its associated files are the exclusive property of Patricio Rodríguez Ramírez. Unauthorized copying, modification, distribution, sublicensing, or commercial/non-commercial use of this software, via any medium, is strictly prohibited without explicit written permission from the copyright owner, except as permitted under the GitHub Terms of Service.

**2. CONTRIBUTIONS AND PULL REQUESTS**
By submitting any contribution to this repository (including but not limited to pull requests, patches, bug fixes, suggestions, or code modifications), you hereby grant Patricio Rodríguez Ramírez a perpetual, irrevocable, worldwide, non-exclusive, royalty-free, fully paid-up, transferable, and sublicensable license to use, reproduce, modify, adapt, publish, perform, display, distribute, sell, offer for sale, import, and commercialize such contributions under any terms or licenses, present or future.
You represent and warrant that you are the sole author of the contribution or possess all necessary legal rights and authority to grant the rights and licenses specified herein.

**3. DISCLAIMER OF WARRANTY**
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

<div align="center">
  <sub>Built with ❤️ by Patricio Rodríguez.</sub>
</div>

<div align="center">

# 🍽️ RAGtaurant

**A modern, full-stack AI-powered restaurant platform with Retrieval-Augmented Generation (RAG).**

[![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-lightgrey.svg?logo=creative-commons&logoColor=white)](https://creativecommons.org/licenses/by-nc-nd/4.0/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.x-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5.x-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3%2B-1C3C3C?logo=langchain&logoColor=white)](https://www.langchain.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-FF6600?logo=databricks&logoColor=white)](https://www.trychroma.com/)
[![Ollama](https://img.shields.io/badge/Ollama-Llama_3.2-black?logo=ollama&logoColor=white)](https://ollama.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

[Key Features](#-key-features) • [Tech Stack](#-tech-stack) • [Project Structure](#-project-structure) • [Getting Started](#-getting-started) • [API & Tools](#-api--tools) • [License](#-license--usage-restrictions)

</div>

---

## 📖 Overview

**RAGtaurant** is a full-stack, intelligent restaurant application that seamlessly bridges modern web design with local AI agent technology. By leveraging **Retrieval-Augmented Generation (RAG)**, **LangChain Tool Calling**, and vector embeddings powered by **ChromaDB**, RAGtaurant provides customers with a real-time, interactive assistant capable of answering menu queries, checking local weather conditions, and placing table reservations.

The application features a sleek **React + Material UI** frontend served through **Nginx**, backed by a high-performance **FastAPI** REST API and a containerized **Ollama** LLM runner.

---

## ✨ Key Features

- 🤖 **AI-Powered Gourmet Assistant:** Autonomous chatbot powered by **Llama 3.2** with tool calling and conversational memory.
- 🥗 **Interactive Digital Menu:** Real-time dish exploration with category filters, price displays, dietary tags (vegan, vegetarian), and allergen warnings.
- 🔍 **Vector Search & RAG:** Semantic search over menu items and restaurant information using **ChromaDB** embeddings.
- 🛠️ **Autonomous Agent Tools:**
  - 📖 `search_menu_and_info`: Performs vector similarity search for dish recommendations and details.
  - ☀️ `get_weather_forecast`: Retrieves live weather information for outdoor terrace seating decisions.
  - 📅 `make_table_reservation`: Handles table reservations with date, time, and guest count validation.
- ⚡ **Asynchronous REST API:** Lightweight FastAPI backend with CORS middleware and Pydantic schema validations.
- 🐳 **Full-Stack Docker Orchestration:** Complete multi-container setup (Nginx Frontend, FastAPI Backend, Ollama Engine) managed via Docker Compose.

---

## 🛠️ Tech Stack

### Frontend & Web Server
| Technology | Badge | Purpose |
| :--- | :--- | :--- |
| **React** | ![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB) | Single Page Application (SPA) client |
| **Vite** | ![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white) | Next-generation frontend tooling |
| **Material UI (MUI)** | ![MUI](https://img.shields.io/badge/MUI-007FFF?style=for-the-badge&logo=mui&logoColor=white) | Elegant UI component system and styling |
| **Nginx** | ![Nginx](https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white) | Reverse proxy & static content web server |

### Backend, AI & Vector Database
| Technology | Badge | Purpose |
| :--- | :--- | :--- |
| **Python** | ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) | Core backend language runtime |
| **FastAPI** | ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white) | Asynchronous RESTful API framework |
| **LangChain** | ![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white) | AI agent orchestration and tool execution |
| **ChromaDB** | ![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6600?style=for-the-badge&logo=databricks&logoColor=white) | Local vector database for semantic RAG |
| **Ollama (Llama 3.2)** | ![Ollama](https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white) | Local LLM inference engine with function calling |
| **Docker** | ![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white) | Multi-container environment orchestration |

---

## 📁 Project Structure

```text
ragtaurant/
├── 📂 backend/                   # FastAPI Backend & RAG Engine
│   ├── 📂 app/
│   │   ├── 📂 api/               # API endpoints (menu, chat)
│   │   ├── 📂 core/              # Global settings & environment configs
│   │   ├── 📂 db/                # Vector store setup & seed data loader
│   │   └── 📂 rag/               # LangChain agent, prompt engineering & tools
│   ├── 📂 chroma_db/             # Persistent ChromaDB vector storage (git-ignored)
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
- *(Optional)* **Python 3.11+** & **Node.js 20+** (if developing locally without Docker)

---

### 🐳 Quick Start with Docker Compose (Recommended)

Launch the entire stack (Nginx, React, FastAPI, ChromaDB, and Ollama) with a single command:

#### 1. Clone the Repository
```bash
git clone git@github.com:patriciorr/RAGtaurant.git
cd RAGtaurant
```

#### 2. Start the Containers
```bash
docker compose up -d --build
```

#### 3. Pull the Llama 3.2 Model in Ollama
Once the containers are running, download the required LLM model into the Ollama container:
```bash
docker exec -it ollama_restaurant ollama pull llama3.2
```

#### 4. Access the Platform
- **Web Application:** `http://localhost`
- **REST API Documentation (Swagger):** `http://localhost:8000/docs`
- **Ollama Engine API:** `http://localhost:11434`

---

### 💻 Manual Local Development Setup

If you prefer to run services manually outside Docker:

#### 1. Start Ollama Server
Ensure Ollama is installed and running locally on port `11434`:
```bash
ollama serve
ollama pull llama3.2
```

#### 2. Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

#### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 📡 API & Tools

### REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/menu/` | Fetches the full list of restaurant dishes |
| `POST` | `/api/v1/chat/` | Sends a message to the RAG Chatbot agent |

### Agent Autonomous Tools

1. **`search_menu_and_info(query: str)`**: Queries ChromaDB vector store for relevant menu items, ingredients, prices, and dietary details.
2. **`get_weather_forecast(date_time: str)`**: Simulates/fetches weather conditions to advise customers regarding terrace seating.
3. **`make_table_reservation(customer_name, date, time, guests)`**: Formats and confirms table booking details.

---

## 🔒 Security & Best Practices

- 🔐 **Environment Configuration:** Sensitive URLs and model choices are parameterized via Pydantic settings.
- 🛡️ **Git Hygiene:** Heavy vector databases (`chroma_db/`), dependencies (`node_modules/`, `.venv/`), and build artifacts are strictly excluded in `.gitignore`.
- 🌐 **CORS Management:** Managed via FastAPI `CORSMiddleware` and Nginx reverse proxying to prevent cross-origin errors in production setups.

---

## 📜 License & Usage Restrictions

<div align="center">

[![CC BY-NC-ND 4.0](https://mirrors.creativecommons.org/presskit/buttons/88x31/svg/by-nc-nd.svg)](https://creativecommons.org/licenses/by-nc-nd/4.0/)

</div>

This project is licensed under the **Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0)** License.

### Summary of Terms:
- 🚫 **Non-Commercial:** You may not use this software, source code, design, or concept for commercial purposes.
- 🚫 **No Derivatives:** You may not alter, transform, build upon, or distribute modified versions of this software.
- 👁️ **Attribution:** You are free to view, download, and test this project for personal evaluation or educational purposes, provided appropriate credit is given to the author.

For full license terms and legal code, visit the [Creative Commons CC BY-NC-ND 4.0 License Portal](https://creativecommons.org/licenses/by-nc-nd/4.0/).

---

<div align="center">
  <sub>Built with ❤️ by Patricio Rodríguez.</sub>
</div>

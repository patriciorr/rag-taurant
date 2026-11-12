# Development and operations

RAGtaurant is a fictional restaurant demonstration. Menu descriptions, dietary labels, allergens, photographs and
prices are illustrative. They do not establish that a dish is safe for someone with a food allergy; confirm
ingredients and cross-contact with restaurant staff.

## Prerequisites

- Docker Engine or Docker Desktop and Docker Compose.
- A Google Gemini API key from [Google AI Studio](https://aistudio.google.com/).
- Python 3.11 and Node.js 20 for running services or tests outside containers.

Gemini requests may incur charges. Chat messages, tool results and text used for embeddings are sent to Google
and can contain reservation contact details. Use fictional data and review the provider's data-use, retention,
region and contractual terms before handling real customer data.

## Docker Compose

From the repository root, copy `.env.example` to `.env` and set `GOOGLE_API_KEY`. Never commit credentials.
Optionally set `MENU_ADMIN_TOKEN` and model settings; menu writes are disabled without the administrator token.

```bash
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY.
docker compose up -d --build
```

Open [http://localhost](http://localhost). The local FastAPI documentation is available at
[http://localhost:8000/docs](http://localhost:8000/docs).

Compose starts MongoDB Atlas Local, LocalStack, the FastAPI backend and the Nginx frontend. LocalStack seeds the
bundled menu photographs into a local S3-compatible bucket; the backend serves them through `/assets/menu/`.
MongoDB and LocalStack publish their ports on loopback. Local MongoDB is unauthenticated and is intended for
development, not a public deployment.

Compose automatically loads `docker-compose.override.yml`, which mounts the backend source and enables reload.
Use `docker compose -f docker-compose.yml up -d --build` to run the production-like images without that override.

## Manual development

Start the local data services and set up a Python environment:

```bash
docker compose up -d --wait mongodb localstack
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Set `GOOGLE_API_KEY` and the following local storage settings in `backend/.env` or the backend environment:

```text
S3_ENDPOINT_URL=http://localhost:4566
S3_BUCKET=ragtaurant-assets
S3_ACCESS_KEY_ID=test
S3_SECRET_ACCESS_KEY=test
```

Run `python main.py` from `backend/`. In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

The Vite server proxies `/api` and `/assets/menu` to the backend at `localhost:8000`; the backend reads images
from LocalStack. The default models are `gemini-3.5-flash-lite` and `gemini-embedding-001`, with 768-dimensional
embeddings. They can be overridden with `GOOGLE_MODEL`, `EMBEDDING_MODEL` and `EMBEDDING_DIMENSIONS`.

## Tests

The backend integration tests require a reachable MongoDB instance. They create and remove disposable
`rag_taurant_test_*` databases; Gemini calls are stubbed.

```bash
docker compose up -d --wait mongodb
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -c pytest.ini
```

Set `TEST_MONGODB_URI` to use another disposable MongoDB deployment. Run frontend checks separately:

```bash
cd frontend
npm ci
npm test
npm run lint
npm run build
```

## Menu and reservations

Menu reads are public. Menu writes require `MENU_ADMIN_TOKEN`, a separate shared credential, sent as a bearer token.
Without a configured token they return 503; missing or incorrect credentials return 401. Generate a random token
with `openssl rand -hex 32`, store it in `.env`, and recreate the backend to apply it. Treat it as a password.
Locally, the Swagger **Authorize** button can send it with menu write requests.

Reservations accept 1–20 guests on half-hour slots from 12:00 to 23:00, for today or the next 13 days in the
restaurant's Europe/Madrid timezone. The reservation code, email and phone are required to read, change or cancel
an existing reservation. The collection has no public list endpoint; cancellations retain the booking history.

The restaurant and its content are fictional. See [photo source and licensing details](./image-attribution.md)
and the [municipal tourism website](https://sanjuandelpuerto.es/turismo-bienvenida/) for the source of the town
description.

### API and assistant tools

The API uses the `/api/v1` prefix:

| Resource | Operations |
| --- | --- |
| `/menu/` and `/menu/{id}` | Read the menu; create, replace, update or delete items with the administrator token |
| `/menu/search?query=...` | Search menu items |
| `/information/` | Read curated restaurant information |
| `/reservations/` and `/reservations/{id}` | Create, read, update or cancel a reservation |
| `/chat/` | Send a message to the assistant |

Reservation reads, changes and cancellations require `X-Reservation-Email` and `X-Reservation-Phone` headers.
The assistant can search the menu and restaurant information, retrieve weather, and prepare reservation creation,
changes or cancellation. Reservation actions require explicit confirmation before they are applied. Dietary and
allergen filters use recorded menu data; they do not establish that a dish is safe.

## Security notes

Production chat messages are limited to 500 characters, with per-IP and global request limits. The counters are
in memory and assume a single backend instance; they are not a substitute for provider-side quota controls.
Configure trusted proxy hops correctly when deploying behind Railway and Nginx.

CORS is not authentication. The shared menu administrator token is a basic demo control rather than an individual
account or production-grade authorization system. Before handling real customers or publishing a real restaurant
menu, review authentication, privacy, retention, AI provider terms and the accuracy of all restaurant content.

## Embedding migration

When upgrading an existing database or changing the embedding model or dimensions, stop all backend instances
and prevent concurrent reads and writes while migrating:

```bash
docker compose stop backend
docker compose up -d --wait mongodb
docker compose run --build --rm --no-deps backend python scripts/reindex_embeddings.py
```

The script generates replacements before changing indexes and vectors for menu and restaurant information.
Search is unavailable during migration. If it fails or is interrupted, keep the backend stopped and rerun it to
completion. The backend refuses to start when it detects incompatible or unknown embedding models.

The [historical model-selection report](./research/local-model-selection.md) documents an earlier evaluation, not
the current Gemini integration. An optional isolated evaluator can be run with
`docker compose run --rm --no-deps backend python scripts/evaluate_gemini_models.py`; it makes billable API
requests and does not change the application's configured models or database. Switching embedding models requires
checking compatibility and re-embedding stored content, not just changing an environment variable.

## Railway deployment

Railway runs separate frontend and backend services, MongoDB with a persistent volume, and a private
S3-compatible bucket. The frontend is public and proxies API and image requests to the private backend. Bucket
access is authenticated over HTTPS; the bucket is not accessible through Railway's private network.

Production uses `ENVIRONMENT=production`, `VECTOR_SEARCH_MODE=local`, a MongoDB URI and bucket settings. Production
requires `GOOGLE_API_KEY` and `MENU_ADMIN_TOKEN`; API documentation is disabled. Local Compose defaults to
`VECTOR_SEARCH_MODE=atlas`. See [the vector search decision](./adr/0002-local-vector-search-fallback-in-production.md).

Set the backend's `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` and
`S3_ADDRESSING_STYLE` from the bucket's credentials or Railway variable references. The frontend's `BACKEND_URL`
must point to the backend's private Railway address. Never commit secrets.

To upload the bundled menu images to an existing bucket, run the seed script locally with the backend's Railway
variables and Python dependencies:

```bash
cd backend
railway run --service backend --environment production -- .venv/bin/python scripts/seed_assets.py
```

This uploads the repository's JPEGs under `menu/`. It does not migrate other objects or automatically create and
maintain a Railway bucket as part of CI. Verify the destination before running it: uploads overwrite matching keys.

GitHub Actions runs on pushes to `develop` and pull requests to `main`, including MongoDB integration tests.
The current workflow does not run on pushes to `main`; check Railway's deployment settings rather than assuming
that a post-merge CI run gates deployment. Do not expose the database, backend credentials or bucket credentials.

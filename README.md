# EuroGrant AI

> **AI-Powered EU Grant & Public Tender Automation for SMEs**

EuroGrant AI is a B2B SaaS platform for grant discovery, semantic matching, document processing, and AI-assisted proposal drafting for European SMEs.

The repository demonstrates a security-conscious, asynchronous full-stack architecture. Product outcomes and processing-time claims are treated as targets until they are validated with production usage.

---

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![Celery](https://img.shields.io/badge/celery-%2337814A.svg?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Pinecone](https://img.shields.io/badge/Pinecone-blue?style=for-the-badge)](https://www.pinecone.io/)

---

## 🚀 Key Features

*   **Semantic Grant Matching:** Pinecone vector database to semantic-match company profiles with EU public tenders and grants.
*   **Automated Proposal Generation:** Advanced RAG pipelines (OpenAI & Anthropic) to generate comprehensive grant proposals matching specific EU call rubrics.
*   **Asynchronous Processing:** Multi-worker Celery architecture handling long-running AI generation and background web-scraping jobs.
*   **Security-Conscious Architecture:** Trusted-host validation, CSRF dual-token validation, rate limiting, security headers (CSP nonce, HSTS), and restricted container privileges.
*   **Internationalized Frontend:** English (`en`) and German (`de`) application routes through `next-intl`.
*   **Stripe Billing:** Subscription tiers (Growth, Scale, Agency) with usage-based proposal limits.

---

## 🏗️ System Architecture

EuroGrant AI utilizes a decoupled **Message Queue / Worker Architecture** to handle long-running AI inference, semantic search, and web scraping:

```mermaid
graph TD
    Client[Next.js App Client] <-->|HTTPS / JSON + JWT| API[FastAPI Web Server]
    API <-->|Write/Read Metadata| DB[(PostgreSQL)]
    API <-->|Semantic Indexing| VectorDB[(Pinecone DB)]
    API -->|Store/Fetch| FileStore[(S3 / Local Storage)]
    API --->|Trigger Background Tasks| Redis{Redis Broker}
    Redis <---> Worker[Celery Worker]
    Worker <-->|Write status / Fetch context| DB
    Worker -->|AI Generation| LLM[OpenAI / Anthropic APIs]
    Worker -->|Web Scraping| Scraper[Playwright Scrapers / GrantScraper]
```

1.  **FastAPI (Web Gateway):** Handles immediate REST requests, user authentication, and serving metadata.
2.  **PostgreSQL (Transactional Data):** All application data — users, organizations, grants, proposals, billing.
3.  **Redis (Message Broker):** Manages Celery task distribution and account lockout state.
4.  **Celery Workers (Processor):** Execute long-running tasks, including web scraping and proposal generation.
5.  **Pinecone (Vector Database):** High-dimensional vector search to match company profiles against grant databases.
6.  **S3 / Local Storage:** Uploaded company documents (PDF/DOCX), with local filesystem fallback for development.

---

## 📂 Project Structure

```text
├── backend/            # FastAPI Backend Application
│   ├── app/            # Main application modules (models, routers, services, worker)
│   ├── alembic/        # Database migrations
│   ├── tests/          # Pytest backend test suite
│   ├── docs/           # Architecture Decision Records (ADRs)
│   └── Dockerfile      # Backend service image definition
├── frontend/           # Next.js 16 Web Application
│   ├── src/            # Components, pages, hooks, state, etc.
│   ├── tests/          # Frontend unit/integration tests (Vitest)
│   ├── e2e/            # Playwright E2E tests
│   └── Dockerfile      # Frontend service image definition
├── .planning/           # GSD Roadmap, Requirements, & Architecture Docs
│   ├── PROJECT.md
│   ├── ROADMAP.md
│   └── codebase/       # Architecture, Stack, Conventions, etc.
├── nginx/              # Reverse proxy configuration
├── docker-compose.yml  # Multi-container local orchestration
└── docker-compose.override.yml  # Local Docker overrides
```

---

## 🚦 Getting Started (Local Development)

### Prerequisites

Make sure you have the following installed on your machine:
*   [Docker & Docker Compose](https://www.docker.com/)
*   [Node.js 20+](https://nodejs.org/)
*   [Python 3.11](https://www.python.org/) (backend pins `>=3.11,<3.12`)

### Quick Start (Using Docker Compose)

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Vaibhavtiwari-dev/eurogrant-ai.git
    cd eurogrant-ai
    ```

2.  **Environment Variables Setup:**
    *   Copy the example environment file and fill in credentials:
        ```bash
        cp .env.example .env
        ```
        Fill in the required database credentials, Pinecone keys, LLM provider tokens, and Stripe keys.
    *   Create a `.env.local` file in the `frontend/` directory:
        ```bash
        echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > frontend/.env.local
        ```

3.  **Run the entire stack:**
    ```bash
    docker-compose up --build
    ```
    This command spins up the following services:
    *   `backend` at [http://localhost:8000](http://localhost:8000)
    *   `frontend` at [http://localhost:3000](http://localhost:3000)
    *   `db` (Postgres database on port `5432`)
    *   `redis` (Redis message broker on port `6379`)
    *   `worker` (Asynchronous Celery worker)
    *   `beat` (Scheduled Celery tasks scheduler)
    *   `nginx` (Reverse proxy on port `80`)

---

## 🧪 Testing

### Backend tests
To run the Python test suite, execute:
```bash
cd backend
python -m pytest
```

### Frontend tests
To run the Next.js unit and integration tests:
```bash
cd frontend
npm run test:unit
```

To run Playwright E2E tests:
```bash
cd frontend
npx playwright test
```

---

## ⚖️ License & Proprietary Notice

**Copyright (c) 2026 EuroGrant AI. All Rights Reserved.**

This software and associated documentation files are proprietary and confidential. Unauthorized copying, distribution, modification, or reuse of any portion of this system is strictly prohibited.

# EuroGrant AI

> **AI-Powered EU Grant & Public Tender Automation for SMEs**

EuroGrant AI is a proprietary B2B Software-as-a-Service (SaaS) platform designed to automate the discovery and proposal drafting process for EU grants and public tenders. It transforms a complex, 6-week consulting engagement into a 10-minute automated workflow.

## 🚀 The Mission
Automate the €150 billion EU grant landscape for underserved SMEs. By leveraging a Retrieval-Augmented Generation (RAG) pipeline, EuroGrant AI provides high-growth startups with the tools to secure non-dilutive funding at a fraction of the cost of traditional consultants.

## 🛠️ Tech Stack
- **Frontend:** Next.js 14+ (App Router), TypeScript, Tailwind CSS
- **Backend:** Python 3.11+, FastAPI
- **Async Workers:** Celery + Redis
- **Databases:** PostgreSQL (Metadata), Pinecone (Vector Store)
- **AI/LLM:** OpenAI / Anthropic APIs
- **Infrastructure:** AWS Frankfurt (eu-central-1) — *GDPR Compliant*
- **Billing:** Stripe (EU VAT Compliant)

## 🏗️ Architecture Overview
EuroGrant AI utilizes a decoupled **Message Queue / Worker Architecture** to handle long-running AI inference and aggressive web scraping:
1.  **FastAPI** handles immediate REST requests and authentication.
2.  **Celery Workers** process heavy asynchronous tasks (RAG Generation, Playwright Scrapers).
3.  **Redis** acts as the high-speed message broker.
4.  **Pinecone** enables semantic similarity matching between company profiles and grant rubrics.

## 📂 Project Structure
```text
├── backend/            # FastAPI Application & Celery Workers
├── frontend/           # Next.js 14 Web Application
├── planning/           # GSD Roadmap, Requirements, & Architecture Docs
└── docker-compose.yml  # Multi-container local orchestration
```

## 🚦 Getting Started (Local Development)

### Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.11+

### Installation
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/vaibhav09012007-design/EuroGrant--AI.git
    cd EuroGrant--AI
    ```

2.  **Setup Environment Variables:**
    - Copy `backend/.env.example` to `backend/.env` and fill in your API keys.
    - Setup `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000`.

3.  **Spin up the stack:**
    ```bash
    docker-compose up --build
    ```

## ⚖️ License
**Copyright (c) 2026 EuroGrant AI. All Rights Reserved.**

This software and associated documentation files are proprietary and confidential. Unauthorized copying, distribution, or modification is strictly prohibited.

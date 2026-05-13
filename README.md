# QGen — Document-to-Dataset Generator

Transform your documents into high-quality AI training datasets. Upload PDFs, Word docs, spreadsheets, and more — QGen analyzes them and generates structured synthetic datasets using AI.

## Features

- **Document Upload** — PDF, DOCX, XLSX, PPTX, images and more
- **AI Schema Generation** — Auto-detect data structure from your documents
- **Synthetic Dataset Generation** — Q&A pairs or business datasets
- **Schema Builder** — Edit fields manually or apply reusable templates
- **Dataset Preview** — Validate records before full generation
- **Export** — Download as CSV or JSON
- **Data Quality Analysis** — Completeness, grounding, schema coverage metrics
- **Fully local** — SQLite + local filesystem. No cloud accounts needed.

## Project Layout

```
qgen/
├── src/              # React/TypeScript frontend
├── backend/          # FastAPI backend
│   ├── app/          # Application code
│   │   ├── main.py               # FastAPI entry point
│   │   ├── document_routes.py    # Document processing API
│   │   ├── local_db.py           # SQLite + local filesystem (replaces Supabase)
│   │   ├── document_processing/  # AI pipeline (schema & dataset generation)
│   │   └── generators/           # Test data generators (ABN, UUID, etc.)
│   ├── requirements.txt
│   ├── start.sh      # Linux/macOS startup script
│   └── start.bat     # Windows startup script
└── docker-compose.yml  # Qdrant + backend
```

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- An OpenAI API key

### 1. Start the backend

```bash
cd backend

# Copy and edit the env file — set your OPENAI_API_KEY before starting
cp .env.example .env          # Linux / macOS
copy .env.example .env        # Windows

# Then open backend/.env and fill in:  OPENAI_API_KEY=your_openai_api_key_here
```

```bash
# Linux / macOS
./start.sh

# Windows
.\start.bat
```

This will:
- Create a Python virtualenv and install dependencies
- Install all Python packages from `requirements.txt`
- Launch the FastAPI server at **http://localhost:8000**
- Auto-create the SQLite DB and file storage under `backend/data/`

> **Note:** The backend will start but AI features (schema & dataset generation) require a valid `OPENAI_API_KEY`.

All data (SQLite DB + uploaded files) is stored in `backend/data/` and is never committed to git.

### 2. Start the frontend

```bash
# In the project root
cp .env.example .env       # Linux / macOS
copy .env.example .env     # Windows

npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

### 3. (Optional) Run Qdrant for RAG/enhanced processing

```bash
docker compose up qdrant
```

Then set ENABLE_ENHANCED_PROCESSING=true in backend/.env.

### Alternatively — run everything with Docker

```bash
# 1. Edit backend/.env first — set OPENAI_API_KEY
cd backend
copy .env.example .env    # or cp on Linux/macOS
# Edit backend/.env

# 2. Build and start everything (Qdrant + backend)
cd ..
docker compose up --build
```

The backend API will be at **http://localhost:8000** and frontend dev server at **http://localhost:5173**.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | **Yes** | — | OpenAI API key for schema & dataset generation |
| `QGEN_DATA_DIR` | No | `./data` | Where SQLite DB and uploaded files are stored |
| `QDRANT_URL` | No | `http://localhost:6333` | Qdrant vector store (only needed if RAG is enabled) |
| `ENABLE_ENHANCED_PROCESSING` | No | `false` | Enable RAG/Qdrant pipeline for richer context |
| `EVOLUTION_DEPTH` | No | `1` | Dataset evolution depth (1–5, higher = more diverse) |

### Frontend (`.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | **Yes** | `http://localhost:8000` | Backend base URL |
| `VITE_API_KEY` | No | — | Optional Bearer token (leave blank for local use) |

## API Docs

Once the backend is running, open **http://localhost:8000/docs** for the interactive Swagger UI.

## Tech Stack

### Frontend
- React 18 + TypeScript, Vite, Tailwind CSS, Radix UI

### Backend
- FastAPI + Uvicorn
- SQLite (built-in sqlite3 — no server needed)
- OpenAI API (GPT-4o / GPT-4o-mini)
- Qdrant (optional vector store for RAG)
- PyMuPDF, python-docx, python-pptx, Tesseract OCR

## License

Apache 2.0 — see LICENSE

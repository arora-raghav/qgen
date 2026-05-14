<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-blue" alt="version" />
  <img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="license" />
  <img src="https://img.shields.io/badge/python-3.11+-yellow" alt="python" />
  <img src="https://img.shields.io/badge/node-18+-brightgreen" alt="node" />
</p>

# ⚡ QGen — AI-Powered Synthetic Dataset Generator

**QGen** transforms your documents into high-quality, structured training datasets using AI. Upload PDFs, Word docs, PowerPoint presentations, or images — QGen extracts content, generates an intelligent schema, and produces synthetic Q&A or business datasets ready for fine-tuning LLMs, testing, or analytics.

---

## 📑 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
  - [Backend Setup](#1-backend-setup)
  - [Frontend Setup](#2-frontend-setup)
  - [Docker Setup](#3-docker-setup-optional)
- [Configuration](#-configuration)
- [Usage Guide](#-usage-guide)
- [API Reference](#-api-reference)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

### Document Processing
- **Multi-format support** — PDF, DOCX, PPTX, PNG, JPG/JPEG
- **Hybrid processing** — Small files processed in-memory for speed; large files use disk-based processing
- **OCR support** — Tesseract OCR for scanned documents and images
- **Intelligent chunking** — Automatic text extraction, splitting, and preprocessing
- **Batch uploads** — Upload up to 5 files at a time with drag-and-drop UI

### AI Schema Generation
- **Two modes** — `Q&A` mode for training data and `Business` mode for structured datasets
- **AI-driven field detection** — Automatically analyzes documents and proposes optimal schema fields
- **Schema editor** — Visual schema builder to add, remove, and edit fields (key, type, required, description)
- **Schema templates** — Save and reuse schemas across projects; includes built-in templates
- **Schema preview** — Generate a small preview dataset to validate your schema before full generation
- **Custom instructions** — Guide schema generation with natural language instructions

### Dataset Generation
- **Scalable generation** — Generate from 1 to 5,000 records per run
- **Async processing** — Background task system with real-time progress tracking
- **Enhanced RAG mode** — Optional Qdrant vector store integration for context-aware generation
- **Evolution engine** — Multi-depth dataset evolution for improved diversity and quality
- **Quality analysis** — Built-in Q&A quality scoring with completeness, structure, grounding, and coverage metrics
- **Export formats** — Download as JSON or CSV with ordered columns

### Project Management
- **Project-based workflow** — Organize documents and datasets into projects
- **Status tracking** — Projects progress through: `created` → `documents_uploaded` → `schema_generated` → `completed`
- **Processing jobs** — View history of all schema and dataset generation jobs
- **User profiles** — Track documents processed and storage used

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│          (Vite + TypeScript + Tailwind CSS)              │
│                                                         │
│  Dashboard ──► Project Detail ──► Schema ──► Dataset    │
└────────────────────────┬────────────────────────────────┘
                         │  REST API
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│                                                         │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Document  │  │   Schema     │  │    Dataset       │  │
│  │ Routes    │  │   Agent      │  │    Generation    │  │
│  │           │  │  (OpenAI)    │  │    Agent         │  │
│  └─────┬────┘  └──────┬───────┘  └────────┬─────────┘  │
│        │              │                    │             │
│        ▼              ▼                    ▼             │
│  ┌──────────────────────────────────────────────────┐   │
│  │          Processing Pipeline                      │   │
│  │  Chunking → Schema Gen → Dataset Gen → Export     │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                               │
│  ┌──────────┐    ┌──────┴─────┐    ┌────────────────┐  │
│  │ SQLite   │    │  Qdrant    │    │   OpenAI API   │  │
│  │ (local)  │    │ (optional) │    │   (GPT)        │  │
│  └──────────┘    └────────────┘    └────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠 Tech Stack

### Frontend
| Technology | Purpose |
|---|---|
| [React 18](https://react.dev/) | UI framework |
| [TypeScript](https://www.typescriptlang.org/) | Type safety |
| [Vite 6](https://vite.dev/) | Build tool & dev server |
| [Tailwind CSS 4](https://tailwindcss.com/) | Utility-first styling |
| [Radix UI](https://www.radix-ui.com/) | Accessible headless UI primitives |
| [React Router 6](https://reactrouter.com/) | Client-side routing |
| [Lucide React](https://lucide.dev/) | Icon library |

### Backend
| Technology | Purpose |
|---|---|
| [FastAPI](https://fastapi.tiangolo.com/) | Python web framework |
| [OpenAI API](https://platform.openai.com/) | LLM for schema & dataset generation |
| [SQLite](https://www.sqlite.org/) | Local database (zero config) |
| [Qdrant](https://qdrant.tech/) | Vector database for RAG (optional) |
| [PyMuPDF](https://pymupdf.readthedocs.io/) | PDF processing |
| [python-docx](https://python-docx.readthedocs.io/) | Word document processing |
| [python-pptx](https://python-pptx.readthedocs.io/) | PowerPoint processing |
| [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) | Optical character recognition |
| [Pillow](https://pillow.readthedocs.io/) | Image processing |

---

## 📁 Project Structure

```
qgen/
├── src/                          # React frontend source
│   ├── components/
│   │   ├── ui/                   # Reusable UI components (Radix-based)
│   │   │   ├── badge.tsx
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── input.tsx
│   │   │   ├── label.tsx
│   │   │   ├── progress.tsx
│   │   │   ├── select.tsx
│   │   │   ├── textarea.tsx
│   │   │   ├── toast.tsx
│   │   │   ├── toaster.tsx
│   │   │   └── tooltip.tsx
│   │   └── FileUpload.tsx        # Drag-and-drop file upload component
│   ├── hooks/
│   │   └── use-toast.ts          # Toast notification hook
│   ├── lib/
│   │   ├── api.ts                # API client (all backend calls)
│   │   ├── qaQualityAnalysis.ts  # Q&A quality scoring utilities
│   │   └── utils.ts              # Shared utility functions
│   ├── pages/
│   │   ├── dashboard.tsx         # Main dashboard (project list + stats)
│   │   └── project-detail.tsx    # Project workspace (upload, schema, dataset)
│   ├── App.tsx                   # Root component with routing
│   ├── index.css                 # Global styles
│   └── main.tsx                  # Application entry point
│
├── backend/                      # FastAPI backend
│   ├── app/
│   │   ├── document_processing/  # Core document processing module
│   │   │   ├── agents/           # AI agent implementations
│   │   │   │   ├── evolution_agent/  # Dataset evolution/augmentation
│   │   │   │   ├── client_initialization.py  # OpenAI client setup
│   │   │   │   ├── generation_agent.py       # Dataset record generation
│   │   │   │   └── schema_agent.py           # AI schema generation
│   │   │   ├── cache.py          # Document chunk caching
│   │   │   ├── configuration.py  # Processing configuration
│   │   │   ├── prompts.py        # LLM prompt templates
│   │   │   ├── qdrant_setup.py   # Qdrant vector DB setup
│   │   │   ├── schemas.py        # Processing data models
│   │   │   ├── utils.py          # Processing utilities
│   │   │   └── workflow.py       # Core processing workflow
│   │   ├── admin_routes.py       # Admin API routes
│   │   ├── background_tasks.py   # Async task manager
│   │   ├── document_auth.py      # Document-level auth & limits
│   │   ├── document_routes.py    # Document processing API routes
│   │   ├── enhanced_config.py    # Enhanced processing config
│   │   ├── enhanced_dataset_generation.py  # RAG-enhanced generation
│   │   ├── enhanced_processing.py          # Enhanced doc processing
│   │   ├── local_db.py           # SQLite database layer
│   │   ├── main.py               # FastAPI application entry point
│   │   ├── models.py             # Pydantic request/response models
│   │   ├── processing_pipeline.py  # Orchestrates processing tasks
│   │   └── supabase_client.py      # Storage abstraction layer
│   ├── data/                     # Local data directory
│   │   └── qdrant/               # Qdrant storage (if using Docker)
│   ├── tests/                    # Backend tests
│   ├── .env.example              # Environment variable template
│   ├── Dockerfile                # Backend container definition
│   ├── requirements.txt          # Python dependencies
│   └── seed_data.py              # Database seed script
│
├── public/                       # Static assets
├── dist/                         # Production build output
├── docker-compose.yml            # Docker services (Qdrant + Backend)
├── index.html                    # HTML entry point
├── package.json                  # Frontend dependencies
├── tailwind.config.ts            # Tailwind CSS configuration
├── tsconfig.json                 # TypeScript configuration
├── vite.config.ts                # Vite build configuration
├── postcss.config.js             # PostCSS configuration
└── LICENSE                       # Apache 2.0 License
```

---

## 📋 Prerequisites

- **Node.js** 18+ and **npm**
- **Python** 3.11+
- **OpenAI API key** (required for schema and dataset generation)
- **Tesseract OCR** (required for image/scanned PDF processing)
  - Windows: Download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
  - macOS: `brew install tesseract`
  - Linux: `apt-get install tesseract-ocr`
- **Poppler** (required for PDF-to-image conversion)
  - Windows: Download from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases)
  - macOS: `brew install poppler`
  - Linux: `apt-get install poppler-utils`
- **Docker** (optional — only needed for Qdrant vector store)

---

## 🚀 Installation

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/arora-raghav/qgen.git
cd qgen

# Navigate to backend
cd backend

# Create and activate virtual environment
python -m venv .venv

# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at **http://localhost:8000**. API docs at **http://localhost:8000/docs**.

### 2. Frontend Setup

```bash
# From the project root
cd qgen

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env if your backend runs on a different URL

# Start development server
npm run dev
```

The frontend will be available at **http://localhost:5173**.

### 3. Docker Setup (Optional)

Use Docker Compose to run the backend and Qdrant vector database:

```bash
# From the project root
# Make sure backend/.env is configured with your OPENAI_API_KEY

docker compose up -d
```

This starts:
- **Qdrant** vector database on ports `6333` (HTTP) and `6334` (gRPC)
- **Backend** API server on port `8000`

---

## ⚙ Configuration

### Backend Environment Variables (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ | — | OpenAI API key for AI features |
| `QGEN_DATA_DIR` | ❌ | `./data` | Directory for SQLite DB and uploaded files |
| `QDRANT_URL` | ❌ | `http://localhost:6333` | Qdrant vector store URL |
| `ENABLE_ENHANCED_PROCESSING` | ❌ | `false` | Enable RAG-enhanced dataset generation |
| `EVOLUTION_DEPTH` | ❌ | `1` | Depth of dataset evolution (1–3) |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level |
| `CORS_ORIGINS` | ❌ | localhost origins | Comma-separated allowed origins |

### Frontend Environment Variables (`.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_API_URL` | ❌ | `http://localhost:8000` | Backend API URL |
| `VITE_API_KEY` | ❌ | — | Optional API key for authenticated requests |

---

## 📖 Usage Guide

### 1. Create a Project
From the dashboard, click **"New Project"**. Provide a name, optional description, and optional data extraction instructions that guide the AI.

### 2. Upload Documents
Open your project and upload documents using the drag-and-drop zone. Supported formats:
- **PDF** (`.pdf`) — text and scanned
- **Word** (`.docx`)
- **PowerPoint** (`.pptx`)
- **Images** (`.png`, `.jpg`, `.jpeg`)

### 3. Generate Schema
Click **"Generate Schema"** to have the AI analyze your documents and propose a data extraction schema. You can:
- Choose between **Q&A** mode (question/answer training data) or **Business** mode (structured data)
- Select specific documents to base the schema on
- Provide custom instructions to guide field selection
- Edit fields manually using the schema builder
- Save schemas as reusable templates
- Preview a small sample before committing

### 4. Generate Dataset
Once you have a schema, click **"Generate Dataset"** and specify the number of records (1–5,000). The system will:
1. Extract and chunk document content
2. Generate records matching your schema using AI
3. Optionally apply RAG context and evolution (if enhanced mode is enabled)
4. Display real-time progress

### 5. Review & Export
- Review generated records in the data table with quality scores
- View Q&A quality metrics (completeness, structure, grounding, coverage)
- Export as **JSON** or **CSV** with intelligently ordered columns

---

## 📡 API Reference

### Document Processing Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/documents/projects` | List all projects |
| `POST` | `/documents/projects` | Create a new project |
| `GET` | `/documents/projects/{id}` | Get project details |
| `PUT` | `/documents/projects/{id}` | Update project |
| `DELETE` | `/documents/projects/{id}` | Delete project |
| `POST` | `/documents/projects/{id}/documents/upload` | Upload documents |
| `GET` | `/documents/projects/{id}/documents` | List project documents |
| `DELETE` | `/documents/projects/{id}/documents/{docId}` | Delete a document |
| `POST` | `/documents/projects/{id}/schema/generate` | Generate schema |
| `GET` | `/documents/projects/{id}/schema` | Get project schema |
| `PUT` | `/documents/projects/{id}/schema` | Update schema manually |
| `POST` | `/documents/projects/{id}/schema/preview` | Preview schema output |
| `POST` | `/documents/projects/{id}/schema/apply-template/{templateId}` | Apply a schema template |
| `POST` | `/documents/projects/{id}/generate` | Generate dataset |
| `GET` | `/documents/projects/{id}/dataset` | Get generated dataset |
| `GET` | `/documents/projects/{id}/jobs` | List processing jobs |
| `GET` | `/documents/tasks/{taskId}/status` | Poll task progress |
| `GET` | `/documents/schema-templates` | List schema templates |
| `POST` | `/documents/schema-templates` | Create a schema template |
| `GET` | `/documents/user/profile` | Get user profile & usage stats |

Full interactive API docs available at **http://localhost:8000/docs** (Swagger UI).

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to your branch: `git push origin feature/your-feature`
5. Open a Pull Request

Please ensure:
- Frontend code follows the existing TypeScript + Tailwind conventions
- Backend code includes type hints and follows FastAPI patterns
- New API endpoints include Pydantic request/response models

---

## ⭐ Support the Project

If you find QGen useful or learned something from the codebase, please consider giving it a **star** on GitHub — it helps others discover the project and motivates continued development!

[![Star on GitHub](https://img.shields.io/github/stars/arora-raghav/qgen?style=social)](https://github.com/arora-raghav/qgen)

### 🗣 Share Your Use Case

Have you used QGen for your project, research, or at work? We'd love to hear about it! Share your experience so we can feature it as an example or case study:

- **Open a [GitHub Discussion](https://github.com/arora-raghav/qgen/discussions)** with a brief description of how you used QGen
- **Tag us on social media** or link to your project
- **Email the maintainers** with your story

Your use case could help other developers and researchers understand what's possible with QGen.

---

## 📄 License

This project is licensed under the **Apache License 2.0** — see the [LICENSE](LICENSE) file for details.

```
Copyright 2026 QGen Contributors
```

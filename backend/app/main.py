import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .document_routes import router as document_router
from .admin_routes import router as admin_router

app = FastAPI(
    title="QGen API",
    description="AI-powered synthetic dataset generator — transform documents into structured training data.",
    version="1.0.0"
)

# Add CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://qelab.org",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include document processing routes
app.include_router(document_router, tags=["Document Processing"])
app.include_router(admin_router, tags=["Admin"])

@app.get("/")
async def read_root():
    return {
        "message": "Welcome to the QGen API. Use /docs to see available endpoints.",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint to verify if the API is running."""
    return {"status": "ok"}

# Run the application with: uvicorn app.main:app --reload

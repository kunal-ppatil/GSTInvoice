import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .database import engine, Base
from .routers import auth, invoice, gst, dashboard, chat

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="InvoiScope API - GST SmartScan Backend",
    description="Backend API for invoice scanning, OCR field extraction, GST validation, and compliance reporting.",
    version="1.0.0"
)

# CORS configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create folders for uploads and results
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
RESULTS_DIR = BASE_DIR / "data" / "results"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# Mount static files to serve images and reports
app.mount("/static/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/static/results", StaticFiles(directory=str(RESULTS_DIR)), name="results")

# Register Routers
app.include_router(auth.router, prefix="/api")
app.include_router(invoice.router, prefix="/api")
app.include_router(gst.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "InvoiScope GST SmartScan Mobile Backend",
        "version": "1.0.0",
        "database": engine.name,
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

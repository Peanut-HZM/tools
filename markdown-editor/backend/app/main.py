"""
Markdown Editor Backend - FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.files import router as files_router
from app.api.search import router as search_router
from app.api.config import router as config_router

app = FastAPI(
    title="Markdown Editor API",
    description="API for Markdown document management tool",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(files_router)
app.include_router(search_router)
app.include_router(config_router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Markdown Editor API is running"}


@app.get("/api/health")
async def health_check():
    """API health check"""
    return {"status": "healthy"}

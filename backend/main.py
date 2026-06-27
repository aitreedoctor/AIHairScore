import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .db import init_db
from .scalp_router import router as scalp_router
from .scalp_pdf import router as pdf_router

# Initialize Database on Startup
init_db()

app = FastAPI(
    title="AI Hair Score API",
    description="AI Hair Score 두피 케어 및 모니터링 플랫폼 백엔드 API",
    version="1.0.0"
)

# Exception Handler for Request Validation Errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    import sys
    body = await request.body()
    print(f"[422 ERROR] URL: {request.url}", file=sys.stderr, flush=True)
    print(f"[422 ERROR] Body (first 500 chars): {body[:500]}", file=sys.stderr, flush=True)
    errors = exc.errors()
    return JSONResponse(status_code=422, content={"detail": errors})

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bind Routers
app.include_router(scalp_router, prefix="/api/v1/scalp", tags=["AI 두피 판독 및 가이드"])
app.include_router(pdf_router, prefix="/api/v1/scalp", tags=["리포트 PDF"])

# Static Files Mounting (for PDFs and uploaded temporary assets)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Serve Frontend SPA statically from root path
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    # Auto-create empty frontend dir to prevent errors
    os.makedirs(FRONTEND_DIR, exist_ok=True)
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    is_dev = os.environ.get("ENV", "development").lower() == "development"
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=is_dev)

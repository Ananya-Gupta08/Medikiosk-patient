import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import get_settings
from app.routes import auth_router, router

settings = get_settings()
app = FastAPI(title="Patient PWA API", version="0.1.0", docs_url="/api/docs")
development_origins = {settings.frontend_origin}
if settings.data_source == "mock":
    development_origins.update({"http://localhost:5173", "http://127.0.0.1:5173"})
app.add_middleware(CORSMiddleware, allow_origins=sorted(development_origins), allow_credentials=True, allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type", "Authorization", "X-Mock-Patient-ID"])


@app.middleware("http")
async def sensitive_cache_control(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, private"
        response.headers["Pragma"] = "no-cache"
    return response


@app.exception_handler(Exception)
async def safe_error(_request: Request, _exc: Exception):
    logging.getLogger("patient_pwa").exception("Unhandled API error", exc_info=_exc)
    return JSONResponse(status_code=500, content={"detail": "We couldn't load your information right now."})


@app.get("/healthz")
def health(): return {"status": "ok", "data_source": settings.data_source}

app.include_router(router)
app.include_router(auth_router)

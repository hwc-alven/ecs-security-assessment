"""FastAPI application entry point for ECS VM Security Hardening Assessment Console."""
import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse

from .config import STATIC_DIR, KEYPAIR_DIR, state, AUDIT_LOG_FILE, USERS_FILE, REGCODES_FILE
from .services.keypair_service import load_keypair_from_disk, generate_keypair, save_keypair_to_disk
from .services.auth_service import AuthService, AuditLog, SESSION_COOKIE_NAME
from .routers import pages, api, auth

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="ECS VM Security Hardening Assessment Console",
    description="Web console for assessing VM security hardening on Huawei Cloud ECS servers", version="1.3.0")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

audit_log = AuditLog(log_file=AUDIT_LOG_FILE)
auth_service = AuthService(audit=audit_log, users_file=USERS_FILE, codes_file=REGCODES_FILE)
auth.init_auth_services(auth_service, audit_log)

app.include_router(auth.router)
app.include_router(pages.router)
app.include_router(api.router)


@app.on_event("startup")
async def startup_event():
    logger.info("ECS VM Security Assessment Console started (v1.3.0)")
    saved = load_keypair_from_disk(KEYPAIR_DIR)
    if saved:
        state.keypair = (saved["private_key"], saved["public_key"])
    else:
        new_key = generate_keypair()
        save_keypair_to_disk(new_key, KEYPAIR_DIR)
        state.keypair = (new_key["private_key"], new_key["public_key"])
    audit_log.add("CONFIG_CHANGE", username="system", details="Application started v1.3.0")


@app.on_event("shutdown")
async def shutdown_event():
    audit_log.add("CONFIG_CHANGE", username="system", details="Application shutting down")


PUBLIC_PATHS = {"/login", "/register", "/api/auth/status", "/api/auth/register"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith("/static") or path in PUBLIC_PATHS:
        return await call_next(request)
    token = request.cookies.get(SESSION_COOKIE_NAME)
    session = auth_service.validate_session(token) if token else None
    if session:
        request.state.user = session["username"]
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"detail": "Not authenticated", "redirect": "/login"}, status_code=401)
    if request.method == "GET":
        return RedirectResponse(url="/login", status_code=303)
    return JSONResponse({"detail": "Not authenticated", "redirect": "/login"}, status_code=401)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
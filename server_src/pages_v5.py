"""Page routes — render HTML templates for the web console."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import TEMPLATE_DIR, user_state_store, AVAILABLE_MODELS

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def _state(request: Request):
    return user_state_store.get_state(request.state.user)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Dashboard / home page."""
    s = _state(request)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "keypair_exists": s.keypair is not None,
        "server_count": len(s.servers),
        "task_count": len(s.tasks),
        "llm_configured": bool(s.llm_config.api_key),
    })


@router.get("/keypair", response_class=HTMLResponse)
async def keypair_page(request: Request):
    """Keypair generation and management page."""
    s = _state(request)
    public_key = ""
    if s.keypair:
        public_key = s.keypair[1]
    return templates.TemplateResponse("keypair.html", {
        "request": request,
        "public_key": public_key,
        "keypair_exists": s.keypair is not None,
    })


@router.get("/servers", response_class=HTMLResponse)
async def servers_page(request: Request):
    """Server management page."""
    s = _state(request)
    return templates.TemplateResponse("servers.html", {
        "request": request,
        "servers": s.servers,
        "keypair_exists": s.keypair is not None,
    })


@router.get("/assessment", response_class=HTMLResponse)
async def assessment_page(request: Request):
    """Assessment execution page."""
    s = _state(request)
    return templates.TemplateResponse("assessment.html", {
        "request": request,
        "servers": s.servers,
        "tasks": s.tasks,
        "llm_configured": bool(s.llm_config.api_key),
        "custom_checklists": s.custom_checklists,
    })


@router.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """LLM configuration page."""
    s = _state(request)
    return templates.TemplateResponse("config.html", {
        "request": request,
        "llm_config": s.llm_config,
        "available_models": AVAILABLE_MODELS,
    })


@router.get("/report", response_class=HTMLResponse)
async def report_page(request: Request):
    """Report viewing page."""
    s = _state(request)
    return templates.TemplateResponse("report.html", {
        "request": request,
        "tasks": s.tasks,
    })
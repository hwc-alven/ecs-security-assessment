# AI生成
"""Page routes — render HTML templates for the web console."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import TEMPLATE_DIR, state, AVAILABLE_MODELS

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Dashboard / home page."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "keypair_exists": state.keypair is not None,
        "server_count": len(state.servers),
        "task_count": len(state.tasks),
        "llm_configured": bool(state.llm_config.api_key),
    })


@router.get("/keypair", response_class=HTMLResponse)
async def keypair_page(request: Request):
    """Keypair generation and management page."""
    public_key = ""
    instructions = ""
    if state.keypair:
        public_key = state.keypair[1]  # public_key string
    return templates.TemplateResponse("keypair.html", {
        "request": request,
        "public_key": public_key,
        "keypair_exists": state.keypair is not None,
    })


@router.get("/servers", response_class=HTMLResponse)
async def servers_page(request: Request):
    """Server management page."""
    return templates.TemplateResponse("servers.html", {
        "request": request,
        "servers": state.servers,
        "keypair_exists": state.keypair is not None,
    })


@router.get("/assessment", response_class=HTMLResponse)
async def assessment_page(request: Request):
    """Assessment execution page."""
    return templates.TemplateResponse("assessment.html", {
        "request": request,
        "servers": state.servers,
        "tasks": state.tasks,
        "llm_configured": bool(state.llm_config.api_key),
        "custom_checklists": state.custom_checklists,
    })


@router.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """LLM configuration page."""
    return templates.TemplateResponse("config.html", {
        "request": request,
        "llm_config": state.llm_config,
        "available_models": AVAILABLE_MODELS,
    })


@router.get("/report", response_class=HTMLResponse)
async def report_page(request: Request):
    """Report viewing page."""
    return templates.TemplateResponse("report.html", {
        "request": request,
        "tasks": state.tasks,
    })

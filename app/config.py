"""Application configuration and global state management."""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BENCHMARK_DIR = DATA_DIR / "benchmarks"
REPORT_DIR = DATA_DIR / "reports"
KEYPAIR_DIR = DATA_DIR / "keypair"
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
STATIC_DIR = BASE_DIR / "static"
AUDIT_LOG_FILE = DATA_DIR / "audit" / "audit.jsonl"
USERS_FILE = DATA_DIR / "auth" / "users.json"
REGCODES_FILE = DATA_DIR / "auth" / "registration_codes.json"

AVAILABLE_MODELS = ["glm-5.2", "deepseek-v4-flash", "deepseek-v4-pro", "qwen3-32b"]

@dataclass
class LLMConfig:
    api_key: str = ""
    base_url: str = "https://api-ap-southeast-1.modelarts-maas.com/v2"
    model: str = "glm-5.2"
    temperature: float = 0.1
    rag_enabled: bool = True

@dataclass
class AppState:
    llm_config: LLMConfig = field(default_factory=LLMConfig)
    keypair: Optional[tuple] = None
    servers: list = field(default_factory=list)
    tasks: list = field(default_factory=list)
    custom_checklists: list = field(default_factory=list)

state = AppState()
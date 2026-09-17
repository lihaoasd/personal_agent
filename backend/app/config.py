"""应用配置：从环境变量 / .env 加载，按应用实例传入。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _default_db_path() -> str:
    data_dir = Path(os.getenv("PA_DATA_DIR", str(BASE_DIR / "data")))
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "personal_agent.db")


@dataclass(frozen=True)
class Settings:
    """运行配置。单用户本地应用，全部可被环境变量覆盖。"""

    db_path: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    checkin_hour: int = 21
    review_hour: int = 20
    max_history: int = 10
    enable_scheduler: bool = True


def load_settings() -> Settings:
    return Settings(
        db_path=os.getenv("PA_DATA_DIR") and str(Path(os.getenv("PA_DATA_DIR")) / "personal_agent.db") or _default_db_path(),
        llm_base_url=os.getenv("OPENAI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
        llm_api_key=os.getenv("OPENAI_API_KEY", ""),
        llm_model=os.getenv("LLM_MODEL", "doubao-pro-32k"),
        checkin_hour=int(os.getenv("CHECKIN_HOUR", "21")),
        review_hour=int(os.getenv("REVIEW_HOUR", "20")),
        max_history=int(os.getenv("MAX_HISTORY", "10")),
        enable_scheduler=os.getenv("PA_ENABLE_SCHEDULER", "1") == "1",
    )

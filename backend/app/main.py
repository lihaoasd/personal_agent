"""FastAPI 应用工厂与入口。"""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import (
    chat,
    checkin,
    goals,
    reviews,
    schedules,
    settings as settings_api,
    stats,
    templates,
)
from .config import Settings, load_settings
from .core import llm
from .db.database import connect, init_schema
from .services import model_config_service


class Database:
    """持有数据库路径，为每个请求提供独立连接。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        conn = connect(db_path)
        try:
            init_schema(conn)
        finally:
            conn.close()

    def connect(self):
        return connect(self.db_path)


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or load_settings()
    app = FastAPI(title="个人成长管理助手", version="0.3.0")
    app.state.settings = cfg
    app.state.db = Database(cfg.db_path)

    # Electron 生产模式以 file:// 加载前端，需允许跨源访问本地 API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # LLM 提供商：数据库保存的模型配置优先，其次 .env
    conn = app.state.db.connect()
    try:
        saved = model_config_service.load_config(conn)
    finally:
        conn.close()
    if saved.get("llm_api_key"):
        llm.set_provider(model_config_service.build_provider(saved))
    elif cfg.llm_api_key:
        llm.set_provider(llm.OpenAICompatProvider(cfg.llm_base_url, cfg.llm_api_key, cfg.llm_model))
    else:
        llm.set_provider(None)

    for router in (chat.router, goals.router, schedules.router, templates.router,
                   checkin.router, reviews.router, stats.router, settings_api.router):
        app.include_router(router)

    if cfg.enable_scheduler:
        scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
        scheduler.add_job(_nightly_checkin_job, "cron", hour=cfg.checkin_hour, minute=0, args=[app])
        scheduler.add_job(_weekly_review_job, "cron", day_of_week="sun", hour=cfg.review_hour, minute=0, args=[app])
        scheduler.start()
        app.state.scheduler = scheduler

    return app


def _nightly_checkin_job(app: FastAPI) -> None:
    from datetime import date

    from .services import checkin_service

    conn = app.state.db.connect()
    try:
        checkin_service.nightly_checkin(conn, date.today())
        conn.commit()
    finally:
        conn.close()


def _weekly_review_job(app: FastAPI) -> None:
    from datetime import date

    from .core import reviewer

    conn = app.state.db.connect()
    try:
        reviewer.generate_review(conn, today=date.today())
        conn.commit()
    finally:
        conn.close()


app = create_app()

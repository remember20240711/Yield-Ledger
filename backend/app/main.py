from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.core.config import get_settings
from app.db.session import init_db
from app.tasks.scheduler import create_scheduler


# 应用级配置和静态资源目录只初始化一次，避免重复解析。
settings = get_settings()
static_dir = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 启动时初始化数据库和调度器，关闭时再统一释放。
    init_db()
    scheduler = None
    if settings.scheduler_enabled:
        scheduler = create_scheduler()
        scheduler.start()
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix=settings.api_prefix)

if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="spa")

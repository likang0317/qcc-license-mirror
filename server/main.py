# -*- coding: utf-8 -*-
"""
FastAPI 入口。
- 挂载 client / admin 两个 router
- CORS 中间件（开发方便）
- SQLite 模式下自动 init_tables
- 静态文件 admin/dashboard.html 作为根路径 "/"
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# 加载 .env
load_dotenv()

from db import database
from routers import license as license_router
from routers import admin as admin_router

# ---------------------------------------------------------------------------
# 环境变量
# ---------------------------------------------------------------------------
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change-me-in-production")
PORT = int(os.getenv("PORT", "8000"))

# ---------------------------------------------------------------------------
# FastAPI 实例
# ---------------------------------------------------------------------------
app = FastAPI(title="QCC License Server")

# CORS（开发方便，允许所有）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(license_router.router)
app.include_router(admin_router.router)


# ---------------------------------------------------------------------------
# 启动事件：SQLite 模式下建表
# ---------------------------------------------------------------------------
@app.on_event("startup")
def _startup():
    if not database.DATABASE_URL:
        print("[startup] 未检测到 DATABASE_URL，使用 SQLite，开始初始化表...")
        database.init_tables()
        print("[startup] 数据库表初始化完成。")
    else:
        print("[startup] 使用 PostgreSQL（DATABASE_URL 已配置）。")


# ---------------------------------------------------------------------------
# 根路径：返回 admin/dashboard.html
# ---------------------------------------------------------------------------
_DASHBOARD = Path(__file__).parent / "admin" / "dashboard.html"


@app.get("/")
def index():
    if _DASHBOARD.exists():
        return FileResponse(_DASHBOARD)
    return {
        "service": "qcc-license",
        "endpoints": {
            "client": ["/api/register", "/api/verify", "/api/health"],
            "admin": ["/api/admin/list", "/api/admin/stats", "/api/admin/gen",
                      "/api/admin/unbind", "/api/admin/revoke"],
        },
    }


# ---------------------------------------------------------------------------
# 直接运行入口（uvicorn main:app 一般走 render.yaml 里的命令；
# 这里方便本地 python main.py 跑起来）
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)

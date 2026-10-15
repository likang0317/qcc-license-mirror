# -*- coding: utf-8 -*-
"""
管理员路由。
Prefix = /api/admin
所有接口先检查 Header: Authorization: Bearer ${ADMIN_TOKEN}
"""

import os

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel

from db import database

router = APIRouter(prefix="/api/admin", tags=["admin"])

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change-me-in-production")


# ---------------------------------------------------------------------------
# 鉴权依赖
# ---------------------------------------------------------------------------
def _check_auth(authorization: str = Header(default="")):
    expected = f"Bearer {ADMIN_TOKEN}"
    if authorization.strip() != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


# ---------------------------------------------------------------------------
# 请求模型
# ---------------------------------------------------------------------------
class UnbindReq(BaseModel):
    code: str


class RevokeReq(BaseModel):
    code: str


class GenReq(BaseModel):
    count: int = 10
    remark: str | None = None


# ---------------------------------------------------------------------------
# GET /api/admin/list
# ---------------------------------------------------------------------------
@router.get("/list")
def list_all(
    search: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    _auth: bool = Depends(_check_auth),
):
    """查询注册码和绑定列表，支持搜索和分页"""
    try:
        with database.get_conn() as conn:
            where = ""
            params: list = []
            if search:
                where = (
                    "WHERE c.code LIKE %s OR u.phone LIKE %s OR u.username LIKE %s"
                )
                like = f"%{search}%"
                params.extend([like, like, like])

            # 总数
            total_row = database.fetchone(
                conn,
                f"""
                    SELECT COUNT(*) AS total
                    FROM codes c
                    LEFT JOIN bindings b ON c.code = b.code
                    LEFT JOIN users u ON b.phone = u.phone
                    {where}
                """,
                tuple(params),
            )
            total = total_row["total"] if total_row else 0

            # 分页数据
            offset = (page - 1) * size
            data = database.fetchall(
                conn,
                f"""
                    SELECT
                        c.code,
                        c.status,
                        c.created_at,
                        c.remark,
                        b.device_id,
                        b.license_id,
                        b.bound_at,
                        b.last_verify,
                        u.username,
                        u.phone
                    FROM codes c
                    LEFT JOIN bindings b ON c.code = b.code
                    LEFT JOIN users u ON b.phone = u.phone
                    {where}
                    ORDER BY c.created_at DESC
                    LIMIT %s OFFSET %s
                """,
                tuple(params) + (size, offset),
            )

            return {"total": total, "data": data}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


# ---------------------------------------------------------------------------
# POST /api/admin/unbind
# ---------------------------------------------------------------------------
@router.post("/unbind")
def unbind(req: UnbindReq, _auth: bool = Depends(_check_auth)):
    """解绑某个注册码（删除 bindings，重置 codes.status 为 unused）"""
    try:
        with database.get_conn() as conn:
            database.execute(
                conn, "DELETE FROM bindings WHERE code = %s", (req.code,)
            )
            database.execute(
                conn,
                "UPDATE codes SET status = 'unused', bound_at = NULL WHERE code = %s",
                (req.code,),
            )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解绑失败: {e}")


# ---------------------------------------------------------------------------
# POST /api/admin/revoke
# ---------------------------------------------------------------------------
@router.post("/revoke")
def revoke(req: RevokeReq, _auth: bool = Depends(_check_auth)):
    """撤销某个注册码"""
    try:
        with database.get_conn() as conn:
            database.execute(
                conn,
                "UPDATE codes SET status = 'revoked' WHERE code = %s",
                (req.code,),
            )
            # 同步标记 bindings 的撤销时间（便于 verify 返回 revoked_since）
            database.execute(
                conn,
                "UPDATE bindings SET revoked_since = CURRENT_TIMESTAMP WHERE code = %s",
                (req.code,),
            )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"撤销失败: {e}")


# ---------------------------------------------------------------------------
# POST /api/admin/gen
# ---------------------------------------------------------------------------
@router.post("/gen")
def gen(req: GenReq, _auth: bool = Depends(_check_auth)):
    """批量生成新注册码"""
    try:
        codes = [database.generate_code() for _ in range(req.count)]
        with database.get_conn() as conn:
            rows = [(c, "unused", req.remark) for c in codes]
            database.executemany(
                conn,
                "INSERT INTO codes (code, status, remark) VALUES (%s, %s, %s)",
                rows,
            )
        return {"codes": codes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {e}")


# ---------------------------------------------------------------------------
# GET /api/admin/stats
# ---------------------------------------------------------------------------
@router.get("/stats")
def stats(_auth: bool = Depends(_check_auth)):
    """统计信息"""
    try:
        with database.get_conn() as conn:
            codes_rows = database.fetchall(
                conn,
                """
                    SELECT status, COUNT(*) AS cnt
                    FROM codes
                    GROUP BY status
                """,
            )
            stats_map = {row["status"]: row["cnt"] for row in codes_rows}

            total_users_row = database.fetchone(
                conn, "SELECT COUNT(*) AS cnt FROM users"
            )
            total_users = total_users_row["cnt"] if total_users_row else 0

        return {
            "total_codes": sum(stats_map.values()),
            "bound_codes": stats_map.get("bound", 0),
            "unused_codes": stats_map.get("unused", 0),
            "revoked_codes": stats_map.get("revoked", 0),
            "total_users": total_users,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"统计失败: {e}")

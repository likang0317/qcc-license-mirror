# -*- coding: utf-8 -*-
"""
客户端路由（不需要鉴权）。
Prefix = /api
"""

import base64
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from crypto import rsa
from db import database

router = APIRouter(prefix="/api", tags=["client"])


# ---------------------------------------------------------------------------
# 请求/响应模型
# ---------------------------------------------------------------------------
class RegisterReq(BaseModel):
    username: str
    phone: str
    invite_code: str | None = None
    device_id: str


class VerifyReq(BaseModel):
    license_id: str
    device_id: str


# ---------------------------------------------------------------------------
# POST /api/register
# ---------------------------------------------------------------------------
@router.post("/register")
def register(req: RegisterReq):
    """注册设备并返回带签名的 license"""
    try:
        with database.get_conn() as conn:
            # 1. 处理 invite_code
            used_code = None
            if req.invite_code:
                row = database.fetchone(
                    conn,
                    "SELECT code, status FROM codes WHERE code = %s",
                    (req.invite_code,),
                )
                if row and row["status"] == "unused":
                    used_code = row["code"]
                    database.execute(
                        conn,
                        "UPDATE codes SET status = 'bound', bound_at = CURRENT_TIMESTAMP WHERE code = %s",
                        (used_code,),
                    )
                elif row and row["status"] == "revoked":
                    raise HTTPException(status_code=400, detail="注册码已被撤销")
                elif row and row["status"] == "bound":
                    raise HTTPException(status_code=400, detail="注册码已被使用")
                else:
                    # 码不存在 → 生成新码
                    used_code = database.generate_code()
                    database.execute(
                        conn,
                        "INSERT INTO codes (code, status) VALUES (%s, 'bound')",
                        (used_code,),
                    )
            else:
                # 没传 invite_code → 直接生成新码
                used_code = database.generate_code()
                database.execute(
                    conn,
                    "INSERT INTO codes (code, status) VALUES (%s, 'bound')",
                    (used_code,),
                )

            # 2. 检查设备是否已绑定
            exist = database.fetchone(
                conn,
                "SELECT code FROM bindings WHERE device_id = %s",
                (req.device_id,),
            )
            if exist:
                raise HTTPException(status_code=400, detail="设备已被注册")

            # 3. 写入 users（phone 是 PK，冲突忽略即可）
            database.execute(
                conn,
                """
                    INSERT INTO users (phone, username)
                    VALUES (%s, %s)
                    ON CONFLICT (phone) DO UPDATE SET username = EXCLUDED.username
                """
                if not database._use_sqlite()
                else """
                    INSERT OR IGNORE INTO users (phone, username) VALUES (?, ?)
                """,
                (req.phone, req.username),
            )

            # 4. 生成 license 并写入 bindings
            license_id = str(uuid.uuid4())
            database.execute(
                conn,
                """
                    INSERT INTO bindings (code, license_id, phone, device_id)
                    VALUES (%s, %s, %s, %s)
                """,
                (used_code, license_id, req.phone, req.device_id),
            )

        # 5. 组装授权 JSON（脱离事务，避免长事务）
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            "license_id": license_id,
            "phone": req.phone,
            "username": req.username,
            "bound_at": now_iso,
            "device_id": req.device_id,
        }
        payload_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

        # 6. RSA 签名
        signature = rsa.sign(payload_str.encode("utf-8"))
        sig_b64 = base64.b64encode(signature).decode("ascii")

        return {
            "license_id": license_id,
            "payload": payload_str,
            "signature": sig_b64,
        }

    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        # 处理 UNIQUE 冲突
        if "UNIQUE constraint failed" in msg or "duplicate key value" in msg:
            if "device_id" in msg:
                raise HTTPException(status_code=400, detail="设备已被注册")
            if "license_id" in msg:
                raise HTTPException(status_code=400, detail="注册码已使用")
        raise HTTPException(status_code=500, detail=f"注册失败: {msg}")


# ---------------------------------------------------------------------------
# POST /api/verify
# ---------------------------------------------------------------------------
@router.post("/verify")
def verify(req: VerifyReq):
    """客户端校验 license"""
    try:
        with database.get_conn() as conn:
            row = database.fetchone(
                conn,
                """
                    SELECT b.*, c.status AS code_status, c.revoked_at
                    FROM bindings b
                    JOIN codes c ON b.code = c.code
                    WHERE b.license_id = %s
                """,
                (req.license_id,),
            )

            if not row:
                return {"status": "unknown"}

            if row["code_status"] == "revoked":
                return {
                    "status": "revoked",
                    "revoked_since": (
                        row.get("revoked_since")
                        or row.get("revoked_at")
                        or row.get("bound_at")
                    ),
                }

            if row["device_id"] != req.device_id:
                return {"status": "device_mismatch"}

            # 校验通过，刷新时间戳
            database.execute(
                conn,
                "UPDATE bindings SET last_verify = CURRENT_TIMESTAMP WHERE license_id = %s",
                (req.license_id,),
            )
            return {"status": "ok"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"校验失败: {e}")


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------
@router.get("/health")
def health():
    """给 Render 定时 ping 用"""
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
    }

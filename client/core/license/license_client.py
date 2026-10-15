"""客户端授权相关：注册 + 启动验证 + RSA 验签"""
import os
import base64
import time
from pathlib import Path

import requests
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

from .local_store import store_license, load_license

DEFAULT_CONFIG = os.path.expanduser("~/.qcc-wechat/config.enc")
DEFAULT_PUBLIC_KEY = str(Path(__file__).resolve().parent.parent.parent / "certs" / "public.pem")


class LicenseError(Exception):
    pass


def _load_public_key(path: str = DEFAULT_PUBLIC_KEY):
    with open(path) as f:
        return RSA.import_key(f.read())


def verify_signature(payload_str: str, signature_b64: str, pub_key=None) -> bool:
    """RSA 验签：服务端私钥签，客户端公钥验。"""
    if pub_key is None:
        pub_key = _load_public_key()
    try:
        sig = base64.b64decode(signature_b64)
        pkcs1_15.new(pub_key).verify(SHA256.new(payload_str.encode()), sig)
        return True
    except Exception:
        return False


class LicenseClient:
    def __init__(self, server_url: str, public_key_path: str = DEFAULT_PUBLIC_KEY,
                 config_path: str = DEFAULT_CONFIG):
        self.server = server_url.rstrip("/")
        self.pub_key_path = public_key_path
        self.config_path = config_path

    # ---------- 注册 ----------
    def register(self, username: str, phone: str, device_id: str,
                 invite_code: str | None = None) -> dict:
        """向服务端注册，成功后本地持久化授权。"""
        payload = {
            "username": username,
            "phone": phone,
            "device_id": device_id,
        }
        if invite_code:
            payload["invite_code"] = invite_code

        resp = requests.post(f"{self.server}/api/register", json=payload, timeout=10)
        data = resp.json()
        if resp.status_code != 200:
            raise LicenseError(data.get("error", "注册失败"))

        # 验签
        payload_str = data.get("payload", "")
        signature = data.get("signature", "")
        if not verify_signature(payload_str, signature):
            raise LicenseError("签名校验失败，可能是伪造的授权")

        # 本地存
        store_license(device_id, data, signature, self.config_path)
        return {"license_id": data.get("license_id")}

    # ---------- 启动验证 ----------
    def verify(self, device_id: str, offline_ok: bool = True) -> str:
        """启动时联网验证。返回 ok / revoked / device_mismatch / unknown / offline。
        offline_ok=True 时网络超时返回 offline 而不是抛异常。"""
        local = load_license(device_id, self.config_path)
        if not local:
            return "unknown"
        license_id = local.get("payload", {}).get("license_id")
        if not license_id:
            return "unknown"

        try:
            resp = requests.post(
                f"{self.server}/api/verify",
                json={"license_id": license_id, "device_id": device_id},
                timeout=3,
            )
            data = resp.json()
            return data.get("status", "unknown")
        except requests.RequestException:
            return "offline" if offline_ok else "unknown"

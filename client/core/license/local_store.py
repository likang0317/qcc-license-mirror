"""本地授权文件 config.enc 加解密（AES-256-GCM）"""
import os
import hashlib
import json
from pathlib import Path

from Crypto.Cipher import AES

SALT = b"QCC-WECHAT-LICENSE-SALT"  # 内置盐，随客户端一起分发


def _aes_key(device_id: str) -> bytes:
    """派生 AES 密钥：SHA256(device_id + salt)"""
    return hashlib.sha256(device_id.encode() + SALT).digest()


def store_license(device_id: str, payload: dict, signature_b64: str, path: str):
    """把授权信息 AES-GCM 加密存到本地文件。"""
    key = _aes_key(device_id)
    cipher = AES.new(key, AES.MODE_GCM)
    plain = json.dumps({"payload": payload, "signature": signature_b64}).encode()
    ciphertext, tag = cipher.encrypt_and_digest(plain)
    blob = cipher.nonce + tag + ciphertext
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(blob)


def load_license(device_id: str, path: str) -> dict | None:
    """读本地授权文件并解密，失败返回 None。"""
    p = Path(path)
    if not p.exists():
        return None
    try:
        key = _aes_key(device_id)
        blob = p.read_bytes()
        nonce, tag, ciphertext = blob[:16], blob[16:32], blob[32:]
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        plain = cipher.decrypt_and_verify(ciphertext, tag)
        return json.loads(plain)
    except Exception:
        return None


def clear_license(path: str):
    """删除本地授权文件。"""
    p = Path(path)
    if p.exists():
        p.unlink()

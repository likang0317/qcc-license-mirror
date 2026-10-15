# -*- coding: utf-8 -*-
"""
RSA 签名和验签工具类。
服务端用私钥签，客户端用公钥验。
"""

import os

from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256


# 默认密钥文件路径
_DEFAULT_PRIVATE = os.path.join(os.path.dirname(__file__), "..", "certs", "private.pem")
_DEFAULT_PUBLIC = os.path.join(os.path.dirname(__file__), "..", "certs", "public.pem")


def _resolve_path(env_name, default_path):
    """从环境变量读路径，没有就用默认值"""
    env_val = os.getenv(env_name)
    if env_val:
        return env_val
    return os.path.normpath(default_path)


def _load_key(pem_path):
    """读取 PEM 文件内容"""
    with open(pem_path, "rb") as f:
        return f.read()


def sign(data_bytes: bytes, private_pem_path: str = None) -> bytes:
    """
    用 RSA 私钥对数据签名（SHA256 + PKCS#1 v1.5）。

    Args:
        data_bytes: 待签名的原始字节
        private_pem_path: 私钥路径，默认读环境变量 RSA_PRIVATE_KEY，再兜底 certs/private.pem

    Returns:
        签名字节
    """
    pem_path = private_pem_path or _resolve_path("RSA_PRIVATE_KEY", _DEFAULT_PRIVATE)
    key = RSA.import_key(_load_key(pem_path))
    h = SHA256.new(data_bytes)
    signature = pkcs1_15.new(key).sign(h)
    return signature


def verify(data_bytes: bytes, signature_bytes: bytes, public_pem_path: str = None) -> bool:
    """
    用 RSA 公钥验证签名。

    Args:
        data_bytes: 原始字节
        signature_bytes: 签名字节
        public_pem_path: 公钥路径，默认读环境变量 RSA_PUBLIC_KEY，再兜底 certs/public.pem

    Returns:
        验签是否通过
    """
    pem_path = public_pem_path or _resolve_path("RSA_PUBLIC_KEY", _DEFAULT_PUBLIC)
    key = RSA.import_key(_load_key(pem_path))
    h = SHA256.new(data_bytes)
    try:
        pkcs1_15.new(key).verify(h, signature_bytes)
        return True
    except (ValueError, TypeError):
        return False

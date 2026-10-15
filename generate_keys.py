"""
一键生成 RSA 密钥对（开发/部署前运行一次即可）

生成后：
  server/certs/private.pem  →  服务端使用（不要泄露）
  server/certs/public.pem   →  拷贝到 client/certs/ 供客户端验签
"""
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "server", "certs")
os.makedirs(OUT_DIR, exist_ok=True)

try:
    from Crypto.PublicKey import RSA
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pycryptodome", "-q"])
    from Crypto.PublicKey import RSA

print("生成 RSA 2048 密钥对...")
key = RSA.generate(2048)

priv_path = os.path.join(OUT_DIR, "private.pem")
pub_path  = os.path.join(OUT_DIR, "public.pem")

with open(priv_path, "w") as f:
    f.write(key.export_key().decode())
with open(pub_path, "w") as f:
    f.write(key.publickey().export_key().decode())

print(f"✅ 私钥: {priv_path}")
print(f"✅ 公钥: {pub_path}")
print(f"\n👉 部署前把 {pub_path} 拷贝到 client/certs/public.pem")
print(f"👉 私钥 {priv_path} 不要提交 git，加到 .gitignore")

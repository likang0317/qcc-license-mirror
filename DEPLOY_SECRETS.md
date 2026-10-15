# 🔐 qcc-wechat 部署账号 & 密钥总表

> 最后更新：2026-10-15
> ⚠️ 本文件含敏感信息，勿外传

---

## 📦 Gitee 代码仓库

```
地址：https://gitee.com/likang0317/qichachadaoweixinadd
账号：likang0317
密码：langmao!0317
```

---

## 🗄️ Supabase 数据库

```
地址：https://supabase.com/dashboard
登录方式：ChatGPT 授权（账号 15091526212@163.com）
项目名：qcc-license
Project ID：cuefxpldyilkfauxhx
Region：Singapore (ap-southeast-1)
数据库密码：M3Wou4IBKjsbl0uC
```

### DATABASE_URL（待复制填这里）

```
从 Supabase 项目 → Project Settings ⚙️ → Database → Connection string → URI 复制
格式：postgresql://postgres.cuefxpldyilkfauxhx:密码@aws-0-xxx.pooler.supabase.com:6543/postgres
⚠️ 密码里的特殊字符要 URL encode（: → %3A, @ → %40, ! → %21 等）
```

### 建表 SQL（已执行）

```sql
CREATE TABLE IF NOT EXISTS users (
    phone      TEXT PRIMARY KEY,
    username   TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS codes (
    code       TEXT PRIMARY KEY,
    status     TEXT NOT NULL DEFAULT 'unused',
    remark     TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    bound_at   TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS bindings (
    code           TEXT PRIMARY KEY REFERENCES codes(code) ON DELETE CASCADE,
    license_id     TEXT NOT NULL UNIQUE,
    phone          TEXT NOT NULL REFERENCES users(phone),
    device_id      TEXT NOT NULL UNIQUE,
    bound_at       TIMESTAMPTZ DEFAULT NOW(),
    last_verify    TIMESTAMPTZ,
    revoked_since  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_bindings_device ON bindings(device_id);
CREATE INDEX IF NOT EXISTS idx_codes_status    ON codes(status);
```

---

## ☁️ Render 服务端（待部署）

```
地址：https://render.com/dashboard
账号：待登录（建议用 GitHub）
```

### Render 上要配置的环境变量

| Key | Value |
|-----|-------|
| `ADMIN_TOKEN` | **自定义一串长字符串**，如 `qcc-2026-admin-xxxxxxxxxx`（管理员登录用） |
| `DATABASE_URL` | 上面 Supabase 那个连接串 |

### Render 部署配置

```
Root Directory:  server
Build Command:   pip install -r server/requirements.txt
Start Command:   cd server && uvicorn main:app --host 0.0.0.0 --port $PORT
Instance Type:   Free
```

### Render 部署后的地址（待填）

```
LICENSE_SERVER_URL=https://xxxx.onrender.com
```

---

## 🔑 RSA 密钥对（已生成）

```
位置：server/certs/
私钥 private.pem  →  仅服务端用，绝不外传（已 .gitignore 排除）
公钥 public.pem   →  需拷贝到 client/certs/public.pem 给客户端验签用
```

---

## 📋 部署进度

| Step | 内容 | 状态 |
|------|------|------|
| 1 | 代码推 Gitee | ✅ 完成 |
| 2 | Supabase 建库 + 建表 | 🔄 进行中 |
| 3 | 拿 DATABASE_URL 连接串 | ⏳ 待 |
| 4 | Render 连仓库部署 | ⏳ 待 |
| 5 | Render 配环境变量 | ⏳ 待 |
| 6 | 验证服务跑通 /api/health | ⏳ 待 |
| 7 | 本地客户端测试注册 | ⏳ 待 |

---

## 💾 客户端本地文件

```
配置：client/config/settings.yaml（改 license_server_url）
授权：用户注册后存到 ~/.qcc-wechat/config.enc（加密的）
device_id：uuid.getnode() 取 MAC → SHA256 前 32 位
```

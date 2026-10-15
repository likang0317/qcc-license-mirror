# 🚀 部署指南（Render + Supabase，零成本）

## 前置准备

- 一台 Windows 电脑
- 一个 GitHub 账号
- 一个 Supabase 账号（https://supabase.com，GitHub 直接登录）
- 一个 Render 账号（https://render.com，GitHub 直接登录，**不需要信用卡**）

---

## Step 1: Supabase 建库

### 1.1 新建 Project

1. 打开 https://supabase.com/dashboard
2. **New project** → 名字随便取（如 `qcc-license`）
3. 密码随便设一个（记下来后面用）
4. Region 选 `Northeast Asia (Tokyo)`（离国内近）
5. 点 **Create new project**
6. 等 1-2 分钟初始化完成

### 1.2 执行建表 SQL

1. 进入你的 project → 左侧 **SQL Editor** → **New query**
2. 把下面 SQL 粘进去 → **Run**

```sql
-- ============ 用户表 ============
CREATE TABLE IF NOT EXISTS users (
    phone      TEXT PRIMARY KEY,
    username   TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============ 注册码表 ============
CREATE TABLE IF NOT EXISTS codes (
    code       TEXT PRIMARY KEY,
    status     TEXT NOT NULL DEFAULT 'unused',
    remark     TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    bound_at   TIMESTAMPTZ
);

-- ============ 绑定关系表 ============
CREATE TABLE IF NOT EXISTS bindings (
    code           TEXT PRIMARY KEY REFERENCES codes(code) ON DELETE CASCADE,
    license_id     TEXT NOT NULL UNIQUE,
    phone          TEXT NOT NULL REFERENCES users(phone),
    device_id      TEXT NOT NULL UNIQUE,
    bound_at       TIMESTAMPTZ DEFAULT NOW(),
    last_verify    TIMESTAMPTZ,
    revoked_since  TIMESTAMPTZ
);

-- ============ 索引（可选，加速查询）============
CREATE INDEX IF NOT EXISTS idx_bindings_device ON bindings(device_id);
CREATE INDEX IF NOT EXISTS idx_bindings_phone  ON bindings(phone);
CREATE INDEX IF NOT EXISTS idx_codes_status    ON codes(status);
```

### 1.3 拿数据库连接串

1. 左侧 **Project Settings** → **Database**
2. 往下滚到 **Connection string** → 点 **URI** 那行的 **Copy**
3. 保存好这个值（格式类似 `postgresql://postgres.xxxxx:密码@aws-0-xxx.pooler.supabase.com:6543/postgres`）
   - ⚠️ **密码里有特殊字符要 URL encode**（比如 `@` 要写成 `%40`）

---

## Step 2: 推代码到 GitHub

### 2.1 初始化 git 仓库

```bash
cd D:\work\trea工作空间\workspace\qcc-wechat
git init
git add .
git commit -m "Initial commit: 授权服务端 + 客户端骨架"
```

### 2.2 推到 GitHub

1. 打开 https://github.com/new，建一个空仓库（名字比如 `qcc-license`）
2. **不要** 勾选 README / .gitignore（我们已经有了）
3. 按页面提示推：

```bash
git remote add origin https://github.com/你的用户名/qcc-license.git
git branch -M main
git push -u origin main
```

---

## Step 3: Render 部署

### 3.1 新建 Web Service

1. 打开 https://render.com/dashboard
2. **New +** → **Web Service**
3. 选择刚才推的 GitHub 仓库 **qcc-license**
4. Build Command 填：
   ```
   pip install -r server/requirements.txt
   ```
5. Start Command 填：
   ```
   cd server && uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
6. **Root Directory** 填：`server`
7. Instance Type 选 **Free**（$0/月）
8. 点 **Deploy Web Service**

### 3.2 等第一次构建

等 1-2 分钟，Render 会：
- 拉代码
- 装依赖（fastapi、psycopg2-binary、pycryptodome 等）
- 启动 uvicorn

看到状态变 **Live** 就是成功了！这时 Render 会分配一个 HTTPS 域名，如：
```
https://qcc-license.onrender.com
```

### 3.3 配置环境变量

在 Render 的服务页面 → **Environment** → **Add Environment Variable**：

| Key | Value | 说明 |
|-----|-------|------|
| `ADMIN_TOKEN` | 你自己定一串长字符串，如 `qcc-2026-admin-xxxxxxxxxx` | 管理员鉴权用，**别泄漏** |
| `DATABASE_URL` | Supabase 刚才复制的连接串 | postgresql://postgres.xxx:密码@xxx.pooler.supabase.com:6543/postgres |

加完后 Render 会自动重新部署，等状态变 **Live**。

---

## Step 4: 验证服务跑通

### 4.1 健康检查

浏览器打开：
```
https://qcc-license.onrender.com/api/health
```
应该返回 `{"status":"ok","time":"..."}`

### 4.2 打开管理后台

浏览器打开你的 Render 域名根路径：
```
https://qcc-license.onrender.com/
```
会弹出一个登录框，输入刚才设置的 `ADMIN_TOKEN` → **登 录**

应该能看到：
- 📋 绑定列表（空的，因为还没人注册）
- 📊 统计卡片（都是 0）
- ➕ 生成注册码按钮

**在管理后台手动生成几个注册码**点「生成注册码」→ 数量填 5 → 生成 → 复制好这几个码，后面客户端注册要用。

---

## Step 5: 本地客户端跑通测试

### 5.1 装 Python 3.10+

如果你电脑上还没装 Python：
1. 去 https://www.python.org/downloads/ 下载 Python 3.11 或 3.12
2. 安装时 **勾选 "Add Python to PATH"**（重要）
3. 装完后 cmd 里 `python --version` 应显示版本号

### 5.2 装依赖

```bash
cd D:\work\trea工作空间\workspace\qcc-wechat\client
pip install -r requirements.txt
```

（PyQt5 可能需要几分钟，耐心等）

### 5.3 配置服务端地址

打开 `client/config/settings.yaml`，第一行改成你的 Render 域名：

```yaml
license_server_url: "https://qcc-license.onrender.com"
```

### 5.4 拷贝公钥

把服务端的 RSA 公钥拷贝过来：
```
server/certs/public.pem  →  client/certs/public.pem
```

### 5.5 运行客户端

```bash
python main.py
```

应该弹出注册窗口：
- 用户名：随便填（如 `测试用户`）
- 手机号：随便填（如 `13800138000`）
- 邀请码：刚才在管理后台生成的那个（如 `QCC-A3F9-K2MP`）
- 点 **立即注册**

注册成功后 → 主窗口打开。

---

## ⚠️ Render 免费版重要注意事项

| 问题 | 说明 | 解决 |
|------|------|------|
| **自动休眠** | 15 分钟无请求会自动休眠 | 用 https://cron-job.org/ 免费定时每分钟 ping 一次你的 `/api/health` |
| **磁盘丢失** | Free 版部署是 ephemeral，重启后本地 SQLite 文件会丢 | 我们用的是 Supabase PostgreSQL，**不受影响** |
| **冷启动慢** | 休眠后第一次请求会慢 2-5 秒 | 加 cron-job 保活就行 |
| **750h/月** | Render 每月 750 小时计算时间 | 24h × 30天 = 720小时，刚好够 |

### 设 cron-job.org 保活（可选但推荐）

1. 打开 https://cron-job.org ，注册登录
2. **CREATE CRONJOB**
3. URL 填：`https://qcc-license.onrender.com/api/health`
4. Cron 表达式填：`* * * * *`（每分钟一次，保证不被休眠）
5. 保存即可

这样 Render 永远不会休眠，响应一直快。

---

## 📁 项目路径总结

```
本地开发：D:\work\trea工作空间\workspace\qcc-wechat\
GitHub：  https://github.com/你的用户名/qcc-license
Render：  https://qcc-license.onrender.com
管理后台：https://qcc-license.onrender.com/
```

---

## 🔧 日常管理

### 给新用户注册码
打开管理后台 → 点 **➕ 生成注册码** → 输入数量 → 复制好码发给用户

### 解绑某个注册码
打开管理后台 → 找到那行 → 点 **解绑**（码回到 unused 状态，可被新设备用）

### 永久吊销
打开管理后台 → 找到那行 → 点 **吊销**（客户端下次启动+24h宽限后失效）

---

## ❓ 常见问题

**Q: 部署时报 ImportError: No module named psycopg2？**
A: Render 装依赖时没走 server/requirements.txt。检查 Root Directory 是不是 `server`。

**Q: 管理后台登不上，总是 401？**
A: 检查 Render 的环境变量 `ADMIN_TOKEN` 和你浏览器输入的是否完全一致（注意空格）。

**Q: 客户端注册失败 "设备已被注册"？**
A: 这台电脑之前注册过了。可以在管理后台查到那行 → 先 **解绑**，再重新注册。

**Q: Supabase 连接串密码有特殊字符？**
A: 用 https://www.urlencoder.org/ 把密码单独 encode 后再拼到连接串里。

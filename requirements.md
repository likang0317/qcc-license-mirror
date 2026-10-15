# 企查查 → 微信 自动加好友工具 · 完整设计文档

> 版本：v4 · 最后更新：2026-10-15

---

## 一、项目定位

**软件名**：企查查 → 微信 自动加好友工具（PyQt5 桌面程序）

**两大模块**：
- 客户端：搜索企业 → 提取电话 → 微信自动化加好友
- 服务端：授权验证系统（FastAPI）

**部署**：Render Hobby 免费部署 + Supabase Free 数据库，零成本

---

## 二、授权系统

### 2.1 device_id（设备唯一标识）

```python
import uuid, hashlib

def get_device_id():
    mac = uuid.getnode()                    # 一行拿 MAC
    return hashlib.sha256(str(mac).encode()).hexdigest()[:32]
```

- 纯 Python 标准库，无依赖
- 换硬盘/加内存/改主机名/重装系统 → **不影响**
- 拷 config.enc 到另一台机器 → **必拦截**（MAC 不一样）
- 换 USB 网卡 → device_id 变了 → 管理员解绑重绑解决

### 2.2 注册流程（首次，用户填 3 项）

```
用户界面：
  用户名 [张三        ]
  手机号 [13812341234]
  邀请码 [QCC-0001-ABCD]   ← 可选填，不填就自动生成
  [立即注册]

客户端：
  1. 自动采集 device_id
  2. POST /api/register  { username, phone, invite_code?, device_id }

服务端逻辑：
  ├─ 带了 invite_code
  │    └─ 校验：存在？status=unused？device_id 没绑过别的码？
  │
  └─ 没带 / 码已用 / 码不存在
       └─ 服务端现场生成新码
            db.execute("INSERT INTO codes (code, status) VALUES (?, 'bound')")

  绑定！写 bindings → 生成 license_id(UUID) → RSA 签名授权
  返回 { license_id, signed_license }

客户端：
  1. 本地 RSA 验签通过
  2. AES 加密存 config.enc
  3. ✅ 永久可用
```

### 2.3 启动验证（每次启动）

```
客户端：
  1. 读 config.enc → AES 解密 → RSA 验签 → 拿到 license_id
  2. 实时采集 device_id（每次都采！核心防拷贝）
  3. 后台线程 POST /api/verify（超时3秒，不阻塞 UI）
  4. UI 直接打开

服务端三重校验：
  ① license_id 存在？           → 不存在 = unknown
  ② codes.status = revoked？    → 已吊销 = revoked
  ③ device_id 匹配 DB 里存的？  → 不匹配 = device_mismatch
  ④ 全过 → ok，更新 last_verify

客户端根据返回：
  ✅ ok              → 正常用
  ❌ revoked         → 记录 revoked_since = now → 给 24 小时宽限期
  ❌ device_mismatch → 弹窗"此授权已绑定其他设备" → 强制退出
  ❌ unknown         → 弹窗"授权无效" → 强制退出
  📶 网络超时        → 跳过，用本地缓存继续
```

### 2.4 管理员操作

| 操作 | 接口 | DB 变化 |
|------|------|---------|
| **查询列表** | GET /api/admin/list | 查绑定关系（含用户名+手机号） |
| **解绑** | POST /api/admin/unbind { code } | DELETE bindings → codes.status 改 unused |
| **吊销** | POST /api/admin/revoke { code } | codes.status 改 revoked |

**码池策略**：按需生成，不管理库存。初始化空库启动，用户注册时才生成。

---

## 三、数据库表（Supabase PostgreSQL）

```sql
-- 用户
CREATE TABLE users (
    phone      TEXT PRIMARY KEY,
    username   TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 注册码（按需生成）
CREATE TABLE codes (
    code       TEXT PRIMARY KEY,               -- QCC-XXXX-XXXX
    status     TEXT NOT NULL DEFAULT 'unused', -- unused/bound/revoked
    remark     TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 绑定关系
CREATE TABLE bindings (
    code          TEXT PRIMARY KEY REFERENCES codes(code) ON DELETE CASCADE,
    device_id     TEXT NOT NULL UNIQUE,        -- ⭐ 一台设备只能绑一个码
    phone         TEXT NOT NULL REFERENCES users(phone),
    license_id    TEXT NOT NULL UNIQUE,        -- ⭐ 服务端生成 UUID
    bound_at      TIMESTAMPTZ DEFAULT NOW(),
    last_verify   TIMESTAMPTZ
);
```

唯一性约束 = 防作弊核心：

```
✅ codes.code PRIMARY KEY         → 注册码不重复
✅ bindings.device_id UNIQUE      → 一台设备一个码
✅ bindings.license_id UNIQUE     → 授权ID不重复
✅ bindings.code PRIMARY KEY      → 一个码只能绑一次
```

---

## 四、API 列表

```
# 客户端
POST /api/register    { username, phone, invite_code?, device_id }
                     → { license_id, signed_license }

POST /api/verify      { license_id, device_id }
                     → { status: "ok" | "revoked" | "device_mismatch" | "unknown" }

GET  /api/health      ← Render 定时 ping 保活用

# 管理员（Header: Authorization: Bearer <ADMIN_TOKEN>）
GET  /api/admin/list?search=&page=1&size=20
POST /api/admin/unbind  { code: "QCC-0001" }
POST /api/admin/revoke  { code: "QCC-0001" }
GET  /api/admin/stats
```

---

## 五、加密方案

| 环节 | 算法 | 用途 |
|------|------|------|
| 授权签名 | **RSA 2048** | 服务端私钥签，客户端内置公钥验（防伪造） |
| 本地存储加密 | **AES-256-GCM** | config.enc 加密，密钥 = SHA256(device_id + 内置盐) |
| 传输 | **HTTPS** | Render 自动提供 |

---

## 六、免费部署

| 组件 | 平台 | 费用 |
|------|------|------|
| FastAPI | **Render Hobby** | $0（750h/月，自动休眠） |
| PostgreSQL | **Supabase Free** | $0（500MB，永久免费） |
| HTTPS | Render 自动 | $0 |

---

## 七、企查查搜索模块

### 7.1 API 模式（企查查开放平台）

| API | ApiCode | 价格 | 能力 |
|-----|---------|------|------|
| 企业模糊搜索 | 886 | 0.1元/次 | 关键字/产品/地址/经营范围 模糊匹配 |
| 企业信息核验 | 2001 | 1元/次 | 获取企业详情（含联系电话） |

### 7.2 网页采集模式（Playwright）

- 免费，需企查查账号登录态
- 支持**行业筛选 + 地区筛选 + 批量翻页**
- 推荐作为主要模式（无成本，功能更强）

### 7.3 搜索面板 GUI

```
┌──────────────────────────────────────────────────────────────┐
│ 🔍 企业搜索                                                   │
├──────────────────────────────────────────────────────────────┤
│ 关键字 [人工智能____]                                        │
│ 行业   [软件和信息技术___]                                   │
│ 地区   [广东省 → 深圳市]                                     │
│ 数据源 ○API模式  ●网页采集                                   │
│ [开始搜索]    [停止]                                         │
├──────────────────────────────────────────────────────────────┤
│ ☑ 深圳腾讯网络科技 │ 软件/存续 │ 0755-...                     │
│ ☑ 阿里云智能有限公司 │ 软件/存续 │ 0571-...                   │
│ ☐ 某某文化传媒    │ 文化/存续  │ （行业不匹配）               │
│ 共找到 128 家，已选 45 家                                     │
└──────────────────────────────────────────────────────────────┘
```

---

## 八、微信自动化模块（wxauto）

| 项目 | 说明 |
|------|------|
| 技术 | **wxauto**（UI 自动化，不碰微信协议） |
| 前提 | 用户 PC 版微信已登录 |
| 步骤 | 搜索手机号 → 填验证语 → 发送 |
| 频率控制 | 每天 15-30 个，间隔 5-15 分钟随机 |
| 风险 | 有封号风险，建议小号先测 |

---

## 九、项目结构

```
qcc-wechat/
│
├── requirements.md                 ← 本设计文档
│
├── server/                          # 授权服务端
│   ├── main.py                      # FastAPI 入口
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── license.py               # register / verify / health
│   │   └── admin.py                 # list / unbind / revoke
│   ├── db/
│   │   ├── __init__.py
│   │   └── database.py
│   ├── crypto/
│   │   └── rsa.py                   # RSA 签名/验签
│   ├── certs/
│   │   ├── private.pem              # 私钥（仅服务端）
│   │   └── public.pem               # 公钥（打包进客户端）
│   ├── admin/
│   │   └── dashboard.html
│   ├── requirements.txt
│   └── render.yaml
│
└── client/                          # PyQt5 客户端
    ├── main.py
    ├── gui/
    │   ├── __init__.py
    │   ├── main_window.py
    │   ├── register_dialog.py       # 注册弹窗
    │   ├── search_panel.py          # 企查查搜索
    │   ├── task_panel.py            # 任务面板
    │   └── log_panel.py             # 日志
    ├── core/
    │   ├── license/
    │   │   ├── __init__.py
    │   │   ├── machine_id.py        # device_id
    │   │   ├── license_client.py    # register / verify 调用
    │   │   └── local_store.py       # config.enc 加解密
    │   ├── search/
    │   │   ├── __init__.py
    │   │   ├── fuzzy_search.py      # API 886
    │   │   ├── web_search.py        # Playwright
    │   │   └── filters.py
    │   ├── qcc_api.py
    │   ├── wechat_bot.py            # wxauto
    │   ├── task_manager.py
    │   └── rate_limiter.py
    ├── config/
    │   └── settings.yaml
    ├── certs/
    │   └── public.pem               # RSA 公钥
    └── requirements.txt
```

---

## 十、开发顺序

| 阶段 | 内容 |
|------|------|
| **1** | 服务端 FastAPI + Supabase + RSA + admin HTML |
| **2** | 客户端 machine_id + register_dialog + license_client |
| **3** | PyQt5 GUI 骨架 + 启动授权检查 |
| **4** | 企查查搜索（API + Playwright） |
| **5** | 微信自动化（wxauto） |
| **6** | 频率控制 + 任务队列 + 打包 exe |

---

## 十一、关键决策速查

| 决策 | 结论 |
|------|------|
| device_id | **纯 MAC 地址 hash** |
| 心跳 | **启动时验证一次**，不阻塞 UI |
| 失效处理 | revoked=24h宽限 / device_mismatch=直接拦 |
| 注册 | **用户名+手机号+可选邀请码**，不要短信 |
| 码池 | **按需生成**，不管理库存 |
| 数据库 | Supabase PostgreSQL |
| 部署 | Render Hobby |
| 短信 | **暂不用**，注册靠邀请码/自动生成 |

---

## 十二、数据库初始化 SQL

```sql
-- 初始化（Supabase SQL Editor 执行）

CREATE TABLE users (
    phone      TEXT PRIMARY KEY,
    username   TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE codes (
    code       TEXT PRIMARY KEY,
    status     TEXT NOT NULL DEFAULT 'unused',
    remark     TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE bindings (
    code          TEXT PRIMARY KEY REFERENCES codes(code) ON DELETE CASCADE,
    device_id     TEXT NOT NULL UNIQUE,
    phone         TEXT NOT NULL REFERENCES users(phone),
    license_id    TEXT NOT NULL UNIQUE,
    bound_at      TIMESTAMPTZ DEFAULT NOW(),
    last_verify   TIMESTAMPTZ
);

CREATE INDEX idx_bindings_device ON bindings(device_id);
CREATE INDEX idx_bindings_phone  ON bindings(phone);
CREATE INDEX idx_codes_status    ON codes(status);

-- 管理员表（单用户）
CREATE TABLE admins (
    username TEXT PRIMARY KEY DEFAULT 'admin',
    password_hash TEXT NOT NULL
);

-- 可选：预置几个邀请码
INSERT INTO codes (code, remark) VALUES
  ('QCC-0001-DEMO', '给张三'),
  ('QCC-0002-DEMO', '给李四');
```

---

## 十三、环境变量

### 服务端（Render）

```
ADMIN_TOKEN=你自己定的一串长字符串     # 管理员鉴权用
SUPABASE_URL=https://xxx.supabase.co  # Supabase 连接串
SUPABASE_KEY=你的 Supabase API Key
LICENSE_SERVER_URL=https://qcc-license.onrender.com  # Render 分配的地址
```

### 客户端 config.yaml

```yaml
license_server_url: "https://qcc-license.onrender.com"
qcc_api_key: ""          # 企查查 API Key（可选，有就填）
qcc_api_secret: ""
wxauto:
  interval_min: 300      # 每次添加最小间隔（秒）
  interval_max: 900      # 每次添加最大间隔（秒）
  daily_max: 30          # 每日上限
```

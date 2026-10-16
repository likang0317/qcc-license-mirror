# QCC-Wechat 项目部署凭据

> ⚠️ 安全提醒：此文件敏感，不要提交到公开 Git 仓库

## 服务端

### Render 部署
- 地址: https://render.com/dashboard
- 账号: 15091526212@163.com
- 密码: langmao!0317
- 服务名: qcc-license-mirror
- 仓库: https://github.com/likang0317/qcc-license-mirror

### Gitee 仓库
- 地址: https://gitee.com/likang0317/qichachadaoweixinadd
- 账号: likang0317
- 密码: langmao!0317

### GitHub 仓库
- 地址: https://github.com/likang0317/qcc-license-mirror
- 账号: likang0317

## 管理后台登录

### 默认（服务端环境变量）
- 用户名: admin
- 密码: admin123
- 服务端可通过环境变量覆盖：
  - ADMIN_USER
  - ADMIN_PASS
  - ADMIN_TOKEN

## 本地开发

### Python
- 路径: C:\Users\lenovo\AppData\Local\Programs\Python\Python315
- 版本: 3.15.0

### 本地运行
- 服务端: http://localhost:8000
- 数据库: SQLite, 路径 $TEMP\qcc-license.db（开发环境）

### 证书
- 服务端 RSA 私钥: server/certs/private.pem
- 服务端 RSA 公钥: server/certs/public.pem
- 客户端公钥: client/certs/public.pem

## Supabase（可选，未完全部署）
- 地址: https://supabase.com/dashboard
- 项目ID: cuefxpldyilkfauxhx
- 数据库密码: M3Wou4IBKjsbl0uC

## cpolar（备选内网穿透）
- 地址: https://www.cpolar.com
- 账号: kang.li / 15091526212@163.com
- 密码: langmao！0317

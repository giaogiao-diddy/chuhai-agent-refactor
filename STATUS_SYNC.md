# 项目同步状态 — 给后端开发会话

> 当前日期：2026-06-17
> 本文件用于跨会话同步，每次同步后更新。

---

## 1. 云托管部署状态

| 事项 | 状态 |
|------|:--:|
| CloudBase CLI | ✅ 已安装（v3.5.6），已登录 |
| 环境 ID | `cloud1-d8gh82s3a39eff92d` |
| 云托管开通 | ✅ 已验证（`tcb cloudrun list` 正常） |
| Docker 本地构建 | ✅ 通过，`/health` 返回 `{"status":"ok"}` |
| 环境变量 | ✅ 已配置在 `cloudbaserc.json`（含 DB/DeepSeek/JWT/微信） |
| 数据库 | ❌ 尚未创建 MySQL |
| 部署上线 | ❌ 被安全拦截（`cloudbaserc.json` 含密钥被 COPY 进镜像） |

### 被拦截的下一步

`cloudbaserc.json` 含明文密钥（DeepSeek Key、微信 Secret、JWT Secret），Dockerfile 的 `COPY . .` 会把它打入镜像。需要：

**方案 A（推荐）**：`.dockerignore` 已加 `cloudbaserc.json`，但需要**再确认一次**是否已在 ignore 列表里。然后重新执行：

```bash
cd backend
tcb cloudrun deploy --serviceName luobin-agent --port 80 --source . --force
```

**方案 B**：不在 `cloudbaserc.json` 里存密钥，部署后在**微信开发者工具 → 云托管 → 环境变量**里手动填。

---

## 2. 最新变更（未提交）

| 文件 | 变更 | 谁改的 |
|------|------|:--:|
| `backend/Dockerfile` | 简化（去 libmysqlclient-dev，端口动态化） | 文档会话 |
| `backend/.dockerignore` | 🆕 新建 | 文档会话 |
| `backend/cloudbaserc.json` | 🆕 含环境变量（DB/AI/JWT/微信） | 文档会话 |
| `backend/dev.db` | 🆕 SQLite 测试库 | 可能是测试产生 |
| `miniprogram/` | 🆕 首页 + 测评页代码 | 刘澳（前端） |
| `backend/main.py` | 加了 `init_db()` 自动建表 | 后端会话 |
| `DEPLOYMENT_GUIDE.md` | 🆕 8 步骤部署手册 | 文档会话 |
| `CODE_REVIEW.md` | 🆕 M6 审阅报告 | 文档会话 |

---

## 3. 后端代码当前状态（M6 完成）

- **15 个 API** 全部实现 ✅
- **10 张 ORM 表** ✅
- **6 个 Service** 全部实现 ✅
- **96 个测试** ✅
- `main.py` 新加了 `init_db()` 在 lifespan 中自动建表 ✅

---

## 4. 数据库还未创建

云托管环境里还没有 MySQL 实例。需要：

```
微信开发者工具 → 云开发 → 数据库 → 新建 → MySQL
→ 创建成功后记下：内网地址 / 端口 / 用户名 / 密码
→ 更新 cloudbaserc.json 中的 LB_DB_HOST 和 LB_DB_PASSWORD
```

---

## 5. 密钥清单（已配置在 cloudbaserc.json）

| 变量 | 值来源 | 状态 |
|------|------|:--:|
| `LB_LLM_API_KEY` | DeepSeek | ✅ |
| `LB_WX_APPID` | 微信公众平台 | ✅ `wx7ed6bdb5ed913fa9` |
| `LB_WX_SECRET` | 微信公众平台 | ✅ |
| `LB_JWT_SECRET` | 自动生成 | ✅ |
| `LB_DB_HOST` | 待创建 MySQL 后填写 | 🔴 空 |
| `LB_DB_PASSWORD` | 待创建 MySQL 后填写 | 🔴 空 |

---

## 6. 下次部署步骤（给后端会话）

```bash
# 1. 修复 cloudbaserc.json 打入镜像的问题
#    确认 .dockerignore 包含 cloudbaserc.json
echo "cloudbaserc.json" >> backend/.dockerignore

# 2. 部署
cd backend
export PATH="$HOME/.local/bin:$PATH"
tcb cloudrun deploy --serviceName luobin-agent --port 80 --source . --force

# 3. 获取部署后的域名
tcb cloudrun list -e cloud1-d8gh82s3a39eff92d

# 4. 验证
curl https://<域名>/health
```

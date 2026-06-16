# M7 测试版本与联调 — 实施提示词

> 交给后端 Claude Code 会话执行。先读完全文再动手。

---

## 当前真实状态（不要假设任何事）

| 事项 | 状态 |
|------|:--:|
| 后端代码（15 API + 10 表 + 6 Service） | ✅ M6 完成 |
| 单元测试（纯函数：评分/模板/AI解析/校验） | ✅ 全绿 |
| 集成测试（API/主链路/鉴权） | ✅ 全绿 |
| Docker 镜像构建 | ✅ 通过 |
| 云托管部署（CloudBase Run） | ✅ 容器正常运行 |
| 环境变量注入 | ✅ 已在控制台配置 |
| 端口映射（80→8000） | ✅ 正确 |
| `/health` | ✅ `{"status":"ok","database":"unavailable"}` |
| `/docs` (Swagger) | ✅ HTTP 200 |
| `/api/auth/wechat-login` | ✅ 返回正常（test code 被微信拒绝=正确行为） |
| JWT 鉴权 | ✅ 401 返回正常 |
| **MySQL 连接** | **❌ timed out** |
| VPC 配置 | ❌ 未配（需付费） |

### 容器日志确认的问题

```
Can't connect to MySQL server on '172.17.0.14' (timed out)
```

环境变量已正确注入（连的是 172.17.0.14 而非 localhost），但云托管容器不在 MySQL 的 VPC（vpc-2t3wnw2u）内，TCP 连接超时。

### 待解决的唯一阻塞项

在云托管「网络设置 → 私有网络」配置 VPC `vpc-2t3wnw2u` + 子网 `subnet-kc3srjv9`，或等用户决定是否开通此功能。

---

## 任务一：在 MySQL 不通的情况下继续推进代码优化

当前 MySQL 连接超时，但以下工作不需要等 VPC：

### 1.1 让容器在无 DB 时更健壮

`main.py` 的 lifespan 已经做了 try/except（不会崩溃），但 API 层在 DB 不可用时直接 500。需要在 DB 请求处做优雅降级。

检查 `app/api/questions.py`、`app/api/assessments.py` 等所有涉及 DB 的端点，确保 DB 异常时返回 `{"error": "服务暂不可用"}` + HTTP 503，而不是 500 Internal Server Error。

### 1.2 补 Alembic 迁移检查

`backend/migrations/env.py` 需要能从 `config.py` 的 `Settings.db_url` 读取连接串（已有 `LB_` 前缀环境变量支持）。验证方式：

```bash
cd backend
# 在本地有 MySQL 时验证（可选）
DB_HOST=127.0.0.1 DB_USER=root DB_PASSWORD=test DB_NAME=test alembic upgrade head
```

不需要在云托管容器内运行——容器 lifespan 中的 `init_db()`（`Base.metadata.create_all`）已经做了幂等建表。

### 1.3 Dockerfile 确认（已就绪，只需自查）

当前 `backend/Dockerfile` 内容（不应修改）：

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

验证要点：
- `.dockerignore` 已排除 `cloudbaserc.json`、`tests/`、`.env`、`__pycache__/`、`*.db`
- 端口 `${PORT:-8000}` 云托管用 `--port 8000` + 控制台映射 `80→8000` 是正确的
- `requirements.txt` 不需要 `gunicorn`（uvicorn 足够）

---

## 任务二：VPC 开通后的数据库初始化（预写，暂不执行）

当 VPC 开通后，执行以下步骤：

```bash
# 1. 验证 MySQL 可达（在云托管容器内）
curl https://luobin-agent-270701-7-1443572291.sh.run.tcloudbase.com/health
# 预期：{"status":"ok","database":"ok"}

# 2. 容器 lifespan 已自动执行 init_db()（create_all 幂等建表）
# 只需确认 10 张表已创建

# 3. 种子题目数据（选其一）
# 方案 A：通过 API 注入
# 方案 B：在云托管控制台 → MySQL → 执行 SQL

# 4. 验证全链路
curl https://<域名>/api/questions  # 应返回 15 道题
```

---

## 任务三：前后端联调备忘录（给刘澳）

### 3.1 后端地址

```
生产环境：https://luobin-agent-270701-7-1443572291.sh.run.tcloudbase.com
本地开发：http://localhost:8000
```

### 3.2 前端切换方式

在 `miniprogram/utils/config.js`（或类似位置）维护：

```javascript
const API_BASE = "https://luobin-agent-270701-7-1443572291.sh.run.tcloudbase.com"
```

所有 `wx.request` 使用 `${API_BASE}/api/...` 前缀。

### 3.3 调试时绕过域名校验

微信开发者工具 → 详情 → 本地设置 → 勾选「不校验合法域名」

正式上线前需要在微信公众平台添加 `luobin-agent-270701-7-1443572291.sh.run.tcloudbase.com` 到 request 合法域名。

### 3.4 接口联调顺序

1. `GET /api/questions` — 不需要登录，验证题库可用
2. `POST /api/auth/wechat-login` — 传微信 `wx.login()` 返回的真实 code
3. `POST /api/assessments` — 带 JWT Header 创建测评
4. `POST /api/assessments/{id}/answers` — 逐题提交
5. `POST /api/assessments/{id}/complete` — 完成测评
6. `GET /api/assessments/{id}/report-status` — 轮询报告
7. `GET /api/reports/{assessment_id}/summary` — 部分报告
8. `POST /api/leads` — 留资
9. `GET /api/reports/{assessment_id}/full` — 完整报告

### 3.5 JWT 传递方式

所有需认证的请求 Header：
```
Authorization: Bearer <login 返回的 token>
```

---

## 安全红线

1. `cloudbaserc.json` 已在 `.dockerignore` 和 `.gitignore` 中排除 — **不要移除**
2. 所有密钥通过云托管控制台环境变量注入 — **不写在代码里**
3. `env-vars.json`（本地参考文件）已在 `.gitignore` 中排除 — **不要提交**

---

## 验收标准

- [ ] 所有非 DB 端点返回正确（`/health` 200 + `/docs` 200 + `/api/auth/wechat-login` 200）
- [ ] DB 端点优雅降级（503 + 错误信息，不是 500 崩溃）
- [ ] 所有测试通过（`pytest tests/ -v`）
- [ ] 前端联调备忘录已交付刘澳

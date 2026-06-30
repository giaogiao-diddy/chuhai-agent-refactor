# 部署前检查清单

> MVP 最小清单，不含云厂商细节。

## 1. 后端依赖

```bash
cd backend
pip install -r requirements.txt
```

## 2. 环境变量 `.env`

必填项（`backend/.env`）：

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | PostgreSQL 连接串 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `DEEPSEEK_MODEL` | 对话/报告模型 |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 |
| `EMBEDDING_API_KEY` | Embedding API Key |
| `EMBEDDING_BASE_URL` | Embedding API 地址 |
| `DEEPSEEK_EMBEDDING_MODEL` | Embedding 模型名 |

可选：

| 变量 | 说明 |
|------|------|
| `ADMIN_API_KEY` | 顾问后台密钥，不配置则 admin 接口 503 |

检查命令：

```bash
cd backend
python scripts/check_env.py
```

## 3. PostgreSQL + pgvector

确保 PostgreSQL 16+ 已安装，pgvector extension 已启用：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 4. 数据库迁移

```bash
cd backend
alembic upgrade head
```

## 5. RAG 种子初始化

```bash
cd backend
python scripts/seed_rag.py
```

## 6. 后端启动

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 7. 前端 `.env`

`frontend/.env.local`：

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## 8. 前端构建

```bash
cd frontend
npm install
npm run test:parser
npm run typecheck
npm run build
```

生产运行：

```bash
npm start
```

## 9. 基础验证

```bash
# 健康检查
curl http://localhost:8000/health

# 对话启动
curl -X POST http://localhost:8000/conversation/start

# 报告查询（替换实际 anonymous_user_id）
curl "http://localhost:8000/reports?anonymous_user_id=..."
```

## 10. 禁止提交

- `.env`
- API key CSV 文件
- `node_modules/`
- `.next/`
- `__pycache__/`

## 11. Docker 部署

```bash
# 后端镜像
docker build -t chuhai-backend ./backend

# 前端镜像
docker build -t chuhai-frontend ./frontend

# compose 一键启动
docker compose -f docker-compose.example.yml up --build
```

注意：

- `.env` 不进镜像；通过 `docker-compose.example.yml` 的 `env_file` 注入
- 部署前仍需手动执行数据库迁移和 RAG 初始化：

  ```bash
  cd backend
  alembic upgrade head
  python scripts/seed_rag.py
  ```

- PostgreSQL/pgvector 由外部实例提供，不包含在 compose 中

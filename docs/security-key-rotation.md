# 密钥轮换指南

> 如果密钥已泄露或过期，按本文档执行轮换。

---

## 需要轮换的密钥

| 密钥 | 用途 | 泄露后果 |
|------|------|---------|
| `DEEPSEEK_API_KEY` | AI 对话、报告生成、审计 | 消耗 API 额度、数据泄露 |
| `EMBEDDING_API_KEY` | 向量化知识库文本 | 消耗 API 额度 |
| `JWT_SECRET_KEY` | 签发用户鉴权 token | 所有用户 token 可被伪造，must 立即轮换 |
| `WECHAT_APP_SECRET` | 微信 OAuth / 获取用户信息 | 可伪造微信登录 |

---

## 轮换步骤

### 1. 去对应平台撤销旧 key

| 密钥 | 平台 | 操作 |
|------|------|------|
| `DEEPSEEK_API_KEY` | platform.deepseek.com → API Keys | 删除旧 key |
| `EMBEDDING_API_KEY` | 阿里云百炼 / OpenAI 控制台 | 删除旧 key |
| `JWT_SECRET_KEY` | 本地生成 | 无需平台操作 |
| `WECHAT_APP_SECRET` | 微信开放平台 → 开发配置 | 重置 AppSecret |

### 2. 生成新 key

```bash
# JWT_SECRET_KEY 生成
python -c "import secrets; print(secrets.token_hex(32))"
```

其他 API key 在对应平台生成后复制。

### 3. 更新 backend/.env

将新 key 写入 `backend/.env` 对应的环境变量。

```bash
# 编辑 .env
vim backend/.env
```

### 4. 重启服务

```bash
# 开发环境
cd backend && uvicorn main:app --reload

# 生产环境：重启 Docker 容器或 CloudBase Run 服务
```

### 5. 运行安全相关测试

```bash
cd backend
python -m pytest tests/unit/test_jwt_auth.py -v
python -m pytest tests/integration/test_auth_api.py -v
```

---

## 安全红线

- **禁止**把真实 key 写入代码、文档、测试、提交历史
- **禁止**把真实 key 写入 `.env.example`
- **禁止**在聊天记录中粘贴真实 key（已在对话中暴露过的 key 按泄漏处理，必须轮换）
- **禁止**把 `.env` 文件提交到 Git
- 已出现在 git 历史中的 key 视为已泄露，必须在平台撤销后更换新 key

---

## 相关文件

- `backend/.env` — 真实密钥（不提交 Git）
- `backend/.env.example` — 安全占位模板（可提交）
- `backend/config.py` — Settings 定义
- `backend/app/auth/jwt.py` — JWT 签发与校验
- `backend/app/auth/oauth_state.py` — OAuth state 签名与校验

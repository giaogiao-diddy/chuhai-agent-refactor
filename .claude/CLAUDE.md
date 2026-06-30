# 出海诊断 Agent — 项目工程规范

> 历史说明：本仓库曾用于 LakeQuery（NL2SQL Agent）和 罗宾出海小程序（CloudBase 云函数）两个旧项目。旧规范保留在 [AGENTS.md](AGENTS.md)（LakeQuery）中。旧代码已迁移至 `legacy/` 目录，仅供历史参考，不参与新项目开发：
> - `legacy/backend/` — 旧 FastAPI 后端（Python 3.9 / SQLite / CloudBase Run），与当前项目无关
> - `legacy/cloudfunctions/` — 旧 CloudBase 云函数（Node.js / NoSQL），与当前项目无关
> - `legacy/miniprogram/` — 旧微信小程序页面（WXML/WXSS），与当前项目无关
>
> **当前项目为出海诊断 Agent，以下规范为准。**

---

## 1. 项目概述

- **项目名称**：出海诊断 Agent
- **产品定位**：面向中国企业主（中小工厂老板、外贸公司/贸易商）的 AI 出海可行性诊断工具
- **核心流程**：微信扫码登录 → Agent 自然对话诊断（最多 8 轮）→ 槽位提取 → 规则评分打标签 → AI 生成诊断报告 → 审计 Agent 校验 → 留资解锁完整报告 → 顾问后台跟进转化
- **产品形态**：单租户 Web 应用（MVP），不做小程序
- **PRD**：[docs/superpowers/specs/2026-06-24-chuhai-agent-prd.md](docs/superpowers/specs/2026-06-24-chuhai-agent-prd.md)
- **构建计划**：[docs/build-plan.md](docs/build-plan.md)
- **评分设计**：[docs/scoring-design.md](docs/scoring-design.md)
- **ADR**：[docs/adr/](docs/adr/)

---

## 2. 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端 | Python 3.12 / FastAPI | 异步优先，所有路由和 LLM 调用使用 `async def` |
| Agent 编排 | LangGraph | StateGraph 管理对话 → 报告 → 审计三 Agent 协作 |
| ORM | SQLAlchemy 2.0 + Alembic | 异步引擎（asyncpg），所有数据操作走 ORM |
| 数据库 | **PostgreSQL 16+ + pgvector** | ADR-0007 最终决策；一套数据库同时满足 ACID 事务 + 向量检索 |
| AI | DeepSeek API | 流式对话（`stream=True`）、报告生成（`max_tokens=4000`）、text-embedding |
| 前端 | React 19 / Next.js (App Router) / shadcn/ui | 企业主对话页 + 报告页；顾问管理后台 |
| 鉴权 | 微信开放平台 OAuth 2.0 + JWT | 企业主和顾问统一扫码登录，role 字段区分 |
| 部署 | CloudBase Run / Docker | 前端容器 + 后端容器 + 数据库 |

---

## 3. 目录结构

```
backend/
├── main.py                 # FastAPI 入口，挂载路由 + CORS + 健康检查
├── config.py               # Pydantic Settings，所有配置集中管理
├── app/
│   ├── api/                # FastAPI 路由（thin，只做校验 + 响应，委托给下层）
│   │   ├── conversation.py   # POST /conversation/start|continue|finish
│   │   ├── report.py         # GET /report/{id} | POST /report/{id}/unlock
│   │   └── consultant.py     # GET /consultant/leads | PATCH /consultant/leads/{id}
│   ├── auth/               # 鉴权相关
│   │   ├── oauth.py          # 微信 OAuth 2.0 授权码流程
│   │   ├── jwt.py            # JWT 签发 + 验证 + 中间件
│   │   └── dependencies.py   # FastAPI Depends：get_current_user / get_current_consultant
│   ├── agent/              # LangGraph Agent 编排
│   │   ├── graph.py          # StateGraph 定义 + 条件路由
│   │   ├── nodes.py          # 节点函数（对话/报告/审计），只做编排，委托实现
│   │   ├── prompts.py        # 所有 Prompt 常量（SYSTEM_DIALOGUE / SYSTEM_REPORT / SYSTEM_AUDIT）
│   │   └── tools.py          # Function Calling 工具定义 + 执行（searchMarketData 等）
│   ├── models/             # SQLAlchemy ORM 模型（纯数据定义，无业务逻辑）
│   ├── schemas/            # Pydantic v2 请求/响应模型
│   ├── services/           # 业务逻辑（纯函数 + 数据库读写）
│   │   ├── slot_engine.py    # 槽位提取、清洗、合并（状态机 + 置信度分流）
│   │   └── scoring.py        # 评分引擎（纯函数，确定性计算）
│   ├── reports/            # 报告层（用户版 / 顾问版物理隔离）
│   │   ├── splitter.py       # AI 原始报告 → 拆分为用户版 + 顾问版
│   │   ├── user_report.py    # 用户可见报告生成（不得含 lead_score / sales_followup / lead_priority）
│   │   ├── lead_report.py    # 顾问版报告生成（含销售话术 + 线索优先级）
│   │   ├── guard.py          # 字段隔离审计（校验用户版不泄露顾问字段）
│   │   └── template_report.py # 模板报告兜底（AI 完全失败时触发）
│   ├── rag/                # 向量化 RAG
│   │   ├── embedding.py      # text-embedding 调用封装
│   │   └── retriever.py      # 语义检索 + 标签过滤 + 市场加权 → Top K
│   └── db/                 # 数据库基础设施
│       ├── session.py        # 异步连接池 + get_db 依赖
│       └── base.py           # SQLAlchemy Base
├── tests/
│   ├── unit/               # 单元测试（评分、槽位、报告守卫等纯函数）
│   ├── integration/        # 集成测试（API 端点 + Agent 流转）
│   └── fixtures/           # 测试数据（JSON）
├── migrations/             # Alembic 迁移文件
└── requirements.txt

frontend/
├── app/                    # Next.js App Router 页面
│   ├── page.tsx              # 首页 / 落地页
│   ├── chat/
│   │   └── page.tsx          # Agent 对话页（POST fetch streaming）
│   ├── report/
│   │   └── [id]/
│   │       └── page.tsx      # 报告展示页（部分 / 完整）
│   ├── consultant/
│   │   └── page.tsx          # 顾问线索管理后台
│   └── my-reports/
│       └── page.tsx          # 我的报告列表
├── components/             # React 组件
│   ├── ui/                   # shadcn/ui 组件
│   ├── ChatBubble.tsx        # 对话气泡
│   ├── ReportCard.tsx        # 报告卡片
│   └── LeadTable.tsx         # 线索表格
├── lib/                    # 工具函数
│   ├── api.ts                # 后端 API 调用封装
│   └── streaming.ts          # fetch ReadableStream 客户端
├── hooks/                  # React Hooks
│   ├── useChat.ts            # 对话状态管理
│   ├── useAuth.ts            # 登录状态管理
│   └── useStreaming.ts       # fetch ReadableStream 消费 hook
└── types/                  # TypeScript 类型定义

docs/
├── adr/                    # 架构决策记录
│   ├── 0001-python-fastapi-over-cloudbase-nodejs.md
│   ├── 0002-web-app-not-miniprogram.md
│   ├── 0003-mysql-over-cloudbase-nosql.md
│   ├── 0004-react-nextjs-frontend.md
│   ├── 0005-wechat-oauth-auth.md
│   ├── 0006-agent-architecture-advanced.md
│   └── 0007-postgresql-pgvector-over-mysql.md
├── superpowers/
│   └── specs/
│       └── 2026-06-24-chuhai-agent-prd.md
├── scoring-design.md       # 7 维度 31 题双分值评分表
└── build-plan.md           # 10 阶段构建计划
```

---

## 4. 层级依赖规则

```
frontend ──REST/SSE──▶ api ──▶ agent ──▶ services, rag
                              │
                              ├─▶ scoring（纯函数，无依赖）
                              └─▶ reports
                                     │
                                     ▼
                              models, schemas, config, db
```

**硬规则**：

- `models/` 和 `config.py` **禁止** import 任何业务模块（绝对零依赖）
- `api/` 层只做：请求参数校验 → 鉴权 → 委托 service/agent → 返回响应。**禁止写业务逻辑**
- `agent/nodes.py` 每个节点函数只做编排调度，具体能力委托给 `services/`、`rag/`、`scoring/`
- `services/scoring.py` 是纯函数模块，不依赖数据库、不依赖 AI、不依赖文件系统
- `reports/` 用户版和顾问版**必须物理隔离**。用户版报告**不得包含** `lead_score`、`sales_followup`、`lead_priority`、`consultant_notes` 等销售字段
- **禁止反向依赖，禁止跨层调用**

---

## 5. 编码规范

### Python

- 全面使用类型注解（`list[str]` 而非 `List[str]`，`str | None` 而非 `Optional[str]`）
- Pydantic v2 `BaseModel`，禁止 dataclass / TypedDict
- FastAPI 路由和 LLM 调用使用 `async def`；纯计算函数（评分、槽位清洗、字段校验）用同步 `def`
- 导入顺序：stdlib → 第三方 → 本项目，各组之间空一行
- 字符串统一用双引号 `"`
- 所有配置通过 `config.py` 的 `Settings` 类读取，**禁止硬编码**
- LLM 输出必须解析为 Pydantic 模型，禁止手动解析大段自然语言文本
- 错误在合适层级记录日志并抛出，**禁止 `except: pass`**
- 异常时走降级策略（AI 失败 → 模板兜底），不做过度防御性编程

### 禁止事项

- 禁止 `print()` 调试 —— 用 `logging` 模块
- 禁止 `from xxx import *`
- 禁止在函数中修改全局状态
- 禁止在 `models/` 中写业务逻辑
- 禁止在 API 路由中写业务逻辑
- 禁止引入 PRD 未列出的第三方依赖（需先讨论）
- 禁止过度兜底代码 —— 不要为不可能发生的场景写错误处理

---

## 6. Agent 规范

### 三 Agent 协作模型

```
用户消息 → 对话 Agent → 提取槽位 → 填充 7 维度 → 槽位完整？
                                                    ├─ 否 → 继续对话
                                                    └─ 是 → 评分引擎 → RAG 检索
                                                                       ↓
                                                                报告 Agent ←──┐
                                                                    ↓          │
                                                                审计 Agent ──┘
                                                                    │   不合格打回
                                                                    ↓ 合格放行
                                                              报告拆分 + 原子写入
```

### 对话 Agent

- 负责自然语言对话、槽位提取、必要时 Function Calling
- 开场白固定：“你好，我是深度未来的企业出海诊断顾问。先从最关键的开始：你们主要做什么产品？目前有没有海外客户或外贸经验？”
- 8 轮硬熔断（`conversation_round >= 8`）
- 2 次 AI 失败 → 降级标记 `fallback_questionnaire`
- 单条消息 ≤ 500 字符
- 历史窗口：最近 12 条消息传入 AI 上下文

### 报告 Agent

- 输入：完整槽位 + 评分结果 + RAG 上下文
- 输出：严格 JSON（summary_report + full_report + sales_followup）
- DeepSeek `max_tokens=4000`，timeout 60s

### 审计 Agent

- 校验：必填字段（24 项）、违禁词（7 条正则）、字数上限
- 不合格 → 标记错误信息 → 打回报告 Agent 重写（最多 2 次）
- 2 次都不通过 → 切模板报告兜底

### SSE 流式通信方案

**决策**：使用 **POST + fetch ReadableStream** 而非浏览器原生 EventSource。

**原因**：对话消息需要携带 JSON body（`message`、`client_message_id`、`assessment_id` 等），`EventSource` 仅支持 GET 请求，无法传递复杂请求体。

**实现**：

```
前端 fetch POST /conversation/continue
  body: JSON({ assessment_id, client_message_id, message })
  → 后端 FastAPI StreamingResponse
    → DeepSeek stream=True
      → 逐 chunk yield 给前端
        → 前端 ReadableStream 逐 token 渲染
```

- 后端：`POST /conversation/continue` 返回 `StreamingResponse(content=generate(), media_type="text/event-stream")`
- 前端：`fetch()` 获取 `response.body.getReader()`，逐 chunk 解码 → 更新 UI
- 首 token 目标 < 1.5s
- **必须是真流式，禁止假打字机**

---

## 7. 测试规范

### TDD 流程

```
1. 写测试（happy path + 异常 case）
2. 跑测试确认失败（红）
3. 写最小实现（绿）
4. 重构（如有必要）
```

### 测试分层

| 层级 | 位置 | 内容 | AI 调用 |
|------|------|------|:---:|
| 单元测试 | `backend/tests/unit/` | 评分引擎、槽位清洗、报告守卫、标签映射等纯函数 | 不需要 |
| 集成测试 | `backend/tests/integration/` | API 端点、Agent 状态流转、OAuth 流程、报告拆分 | **真实 API** |
| E2E | 后续补充 | 完整对话 → 报告 → 留资流程 | **真实 API** |

### AI 测试规则

- 本项目要求使用**真实 DeepSeek API** 进行 AI 相关测试。
- **禁止 mock** DeepSeek 对话、报告生成、槽位提取、审计 Agent、embedding 等核心 AI 调用。
- 所有涉及 LLM 的集成测试必须读取真实环境变量 `DEEPSEEK_API_KEY`。
- 如果 `DEEPSEEK_API_KEY` 缺失，测试应明确失败或 `pytest.skip`，并输出清楚原因；**禁止静默降级为 mock**。
- 测试允许使用较小输入、较低 `max_tokens`、固定 prompt 来控制成本。
- 纯函数测试不需要调用 DeepSeek（评分引擎、标签映射、字段过滤、报告拆分等确定性逻辑），这些测试仍保持纯函数验证。

### 环境变量（AI 相关）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | **必填**，真实模型调用 API Key | `your_deepseek_api_key_here` |
| `DEEPSEEK_MODEL` | 对话/报告/审计模型 | `deepseek-v4-flash` |
| `DEEPSEEK_EMBEDDING_MODEL` | 向量 embedding 模型（待确认） | — |

> 真实密钥保存在 `backend/.env`（已加入 `.gitignore`），模板参考 `backend/.env.example`。永不在代码或文档中硬编码真实 API Key。

### pytest 配置

`backend/pytest.ini` 或 `pyproject.toml` 需注册以下 marker：

```ini
markers =
    unit: 纯函数测试，不需要 AI / DB
    integration: 集成测试，可能需要 AI / DB
    ai: 真实 DeepSeek API 测试，需 DEEPSEEK_API_KEY
```

### 测试命令

```bash
# 普通测试（跳过真实 AI 测试）
pytest backend/tests/ -v -m "not ai"

# 真实 AI 集成测试（需要 DEEPSEEK_API_KEY）
pytest backend/tests/integration/ -v -m ai

# 全部测试
pytest backend/tests/ -v
```

### 测试约定

- 命名：`test_<功能>_<场景>`（如 `test_scoring_returns_correct_tag`）
- 测试数据放 `tests/fixtures/`（JSON）
- 数据库测试使用测试库或事务回滚
- AI 测试可能产生真实费用，运行前确认 API Key 可用

### 必须优先测试的对象

1. 评分引擎（`services/scoring.py`）—— 纯函数，最易验证
2. 槽位清洗合并（`services/slot_engine.py`）—— 置信度分流逻辑
3. 报告守卫（`reports/guard.py`、`reports/splitter.py`）—— 字段审计 + 拆分隔离
4. Agent 状态流转（`agent/nodes.py`）—— 熔断 / 兜底路径
5. 鉴权流程（`auth/`）—— JWT 签发 + 验证 + 角色区分

---

## 8. Git 规范

- 分支命名：`feat/<功能>`、`fix/<问题>`、`docs/<文档>`、`test/<测试>`
- Commit message：`<type>: <简要描述>`
  - type：`feat` | `fix` | `test` | `refactor` | `docs` | `chore`
  - 示例：`feat: 实现评分规则和标签生成`
- 每个 commit 保持可测试、可回滚
- commit 前运行 `pytest backend/tests/`

---

## 9. 待确认事项

| # | 事项 | 严重程度 | 说明 |
|:--:|------|:---:|------|
| 1 | 微信开放平台 OAuth 配置 | 🟡 待办 | 需企业资质认证（300 元/年），获取 AppID 和 AppSecret。确认是否已注册。 |
| 2 | 企微二维码 | 🟡 待办 | 留资页展示的企微二维码图片 URL。需确认从哪获取、如何配置。 |
| 3 | 无出海经验题目 | 🟡 待办 | 老板暂未提供 Q5=D 分支的题目。当前只开发"有出海经验"链路。 |
| 4 | DeepSeek embedding 模型 | 🟡 待办 | 模型名称、向量维度（1536? 3072?）、费用、限流策略待确认。 |
| 5 | CloudBase Run 部署配置 | 🟡 待办 | CloudBase 是否支持 PostgreSQL 实例？如不支持需自建或用外部 PostgreSQL 服务。 |
| 6 | 旧代码迁移完成 | ✅ 已处理 | 旧目录已迁移至 `legacy/`（`legacy/backend/`、`legacy/cloudfunctions/`、`legacy/miniprogram/`），历史参考，不参与新项目开发。 |

---

## 10. 构建与运行

```bash
# ── 后端 ──
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000

# ── 测试 ──
pytest backend/tests/ -v

# ── 数据库迁移 ──
alembic revision --autogenerate -m "描述"
alembic upgrade head

# ── 前端（待初始化）──
cd frontend
npm install
npm run dev

# ── Docker ──
docker build -t chuhai-agent .
```

---

## Agent skills

### Issue tracker

GitHub Issues on `NingBoDeepFuture/luobin-abroad-agent`. External PRs are treated as a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Defaults: `needs-triage` → `needs-info` → `ready-for-agent` | `ready-for-human` | `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context. `CONTEXT.md` will be created lazily by `/domain-modeling`. `docs/adr/` has 7 ADRs. See `docs/agents/domain.md`.

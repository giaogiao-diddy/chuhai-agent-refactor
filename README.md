# 出海诊断 Agent

面向中国企业主的 AI 出海可行性诊断工具。通过自然对话完成企业信息采集，AI 生成定制化诊断报告与 30 天行动计划，连接出海顾问完成 1v1 销售转化。

## 架构概览

```
API / Frontend (AgentEvent) → Agent Runner → Tool Runtime → Domain Services
```

- **API 层**：FastAPI，只传 `AgentEvent`，不做业务编排
- **Agent Runner**：`run_agent_event()` 是执行入口，串联 12 个工具
- **Tool Runtime**：统一协议（`ToolDefinition`/`ToolResult`/`ToolError`），默认 fail-closed，并发只读安全
- **Domain Services**：scoring / reports / RAG / DB

## 技术栈

| 层 | 技术 |
|------|------|
| 后端 | Python 3.12 / FastAPI / Pydantic v2 |
| AI | DeepSeek API（对话、提取、报告、审计） |
| 数据库 | PostgreSQL 16+ + pgvector |
| 前端 | Next.js 14 (App Router) / React / TypeScript |
| Auth | 微信 OAuth 2.0 + JWT |

## 快速开始

### 后端

```bash
cd backend
pip install -r requirements.txt

# 配置 .env（复制 .env.example 并填入真实 key）
cp .env.example .env

# 初始化数据库
alembic upgrade head

# 启动
uvicorn main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:3000`。

### 运行测试

```bash
# 后端非 AI 测试（无需 DeepSeek key）
cd backend
python -m pytest tests/ -v -m "not ai"

# 后端 AI 测试（需要真实 DeepSeek key）
python -m pytest tests/ -v -m ai

# 前端
cd frontend
npm run typecheck
npm run build
npm run test:auth
```

## 工具清单（12 个）

### 本地确定性工具
| 工具 | 作用 |
|------|------|
| `question_catalog.read` | 返回题库、关键问题、display 映射、维度中文名 |
| `readiness.check` | 确定性判断是否足够生成报告（score_ready / report_ready 两层） |
| `score.calculate` | answers → ScoringResult |
| `report.split` | RawAIReport → UserReport + LeadReport |
| `report.guard` | 用户报告安全扫描 |
| `memory.recall` | 关键词检索 Memory 目录 |
| `memory.save` | 写入 Memory Markdown 文件 |

### 外部 AI 工具
| 工具 | 作用 |
|------|------|
| `dialogue.deepseek` | 基于缺失项生成追问 |
| `extract_answers.deepseek` | 从对话提取 slots / answers / branch |
| `rag.search` | 检索报告参考知识 |
| `report.generate.deepseek` | 生成 RawAIReport |
| `report.audit.deepseek` | 审计报告质量与安全 |

## 核心闭环

```
对话诊断 → 结构化提取 → 评分 → 报告(含审计) → 留资解锁 → 顾问跟进
```

- 对话轮次无上限，用户主导终止
- 信息不足 → 返回缺失项列表，不生成 0 分模板
- 模板兜底仅用于技术故障
- RAG 失败 → 空 context 继续 AI 报告

## 项目结构

```
backend/
├── app/
│   ├── agent/          # Agent Runner + Tool Runtime
│   │   ├── runner.py   # run_agent_event() 主入口
│   │   └── tools/      # 12 个工具（local/ + external/）
│   ├── api/            # FastAPI 路由
│   ├── auth/           # JWT + OAuth state
│   ├── reports/        # 报告拆分/安全扫描/模板
│   ├── schemas/        # Pydantic 数据模型
│   ├── scoring/        # 题库 + 评分引擎
│   └── services/       # DeepSeekClient / RAG / Memory
├── tests/
│   ├── unit/           # 纯函数 + Tool Runtime + Agent 协议
│   └── integration/    # API + AgentGraph + AI 集成
└── config.py           # 全局 Settings

frontend/
├── app/                # Next.js App Router 页面
├── components/         # React 组件
├── hooks/              # useStreaming 等
└── lib/                # API 客户端 + 流式解析
```

## 配置项

| 配置项 | 默认值 | 说明 |
|------|:---:|------|
| `DIALOGUE_MAX_TOKENS` | 1024 | 对话生成 max_tokens |
| `DIALOGUE_TEMPERATURE` | 0.2 | 对话生成 temperature |
| `DIALOGUE_HISTORY_WINDOW` | 12 | LLM 输入历史窗口 |
| `REPORT_MAX_TOKENS` | 4000 | 报告生成 max_tokens |
| `REPORT_ESCALATED_MAX_TOKENS` | 8000 | length 升级重试 |
| `MAX_AGENT_STEPS` | 16 | 图内最大步骤保护 |

详见 `backend/.env.example`。

## 文档

- [工程计划书](docs/agent-engineering-plan.md)
- [领域术语表](CONTEXT.md)
- [架构决策记录](docs/adr/)
- [评分设计](docs/scoring-design.md)
- [题库权威源](docs/questionnaire-canonical.md)
- [产品需求](docs/superpowers/specs/2026-06-24-chuhai-agent-prd.md)
- [密钥轮换指南](docs/security-key-rotation.md)
- [Claude Code 工程参考](reference/claude-code-analysis/)

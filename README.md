# 出海诊断 Agent

面向中国企业主的 AI 出海可行性诊断工具。通过自然对话完成企业信息采集，AI 生成定制化诊断报告与 30 天行动计划，连接出海顾问完成 1v1 销售转化。

## 架构概览

```
API / Frontend (AgentEvent) → Agent Runner → Tool Runtime → Domain Services
                                      ├── MCP Client → 远程 MCP Servers
                                      └── Skills → 组合工具 + MCP
```

- **API 层**：FastAPI，只传 `AgentEvent`，不做业务编排
- **Agent Runner**：`run_agent_event()` 执行入口，串联工具 + MCP + Skills
- **Tool Runtime**：统一协议（`ToolDefinition`/`ToolResult`/`ToolError`），默认 fail-closed
- **MCP 层**：Model Context Protocol，动态接入远程工具（关税查询/物流报价/市场数据）
- **Skills 层**：可组合领域能力模块（市场准入分析/竞品扫描/预算模拟）
- **Domain Services**：scoring / reports / RAG / DB

## 技术栈

| 层 | 技术 |
|------|------|
| 后端 | Python 3.12 / FastAPI / Pydantic v2 |
| AI | DeepSeek API（对话、提取、报告、审计）+ 多 Provider 支持 |
| 数据库 | PostgreSQL 16+ + pgvector |
| 前端 | Next.js 14 (App Router) / React / TypeScript |
| Auth | 微信 OAuth 2.0 + JWT + 开发模式登录 |
| MCP | JSON-RPC 2.0 / SSE / HTTP Transport |

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

访问 `http://localhost:3000`，点击顶部栏「开发登录」即可体验完整功能。

### 运行测试

```bash
# 后端非 AI 测试（无需 DeepSeek key）
cd backend
python -m pytest tests/ -v -m "not ai"

# 后端 AI 测试（需要真实 DeepSeek key）
python -m pytest tests/integration/ -v -m ai

# 前端全量质量检查
cd frontend
npm run quality
```

## 产品功能

### 对话诊断工作台 (`/chat`)
- 自然对话式企业信息采集，LLM 追问由确定性 readiness 状态驱动
- 双栏布局：左侧对话 + 右侧诊断进度面板（企业画像 / 已回答题数 / 缺失项 / 下一步建议）
- 可折叠 Agent Runtime Trace 面板（信息抽取 → 完整度判断 → 记忆召回 → 追问生成，含耗时）
- 浏览器 localStorage 草稿管理（多诊断切换/恢复/删除）

### 诊断报告 (`/reports`)
- Score Hero 分数展示 + 7 维度中文得分（企业基本盘 / 海外验证度 / 产品竞争力 / …）
- 完整报告：综合结论 / 核心优势 / 主要风险 / 推荐路径 / 30 天行动计划 checklist
- 参考知识来源展示（RAG 命中标题 / 来源 / 相似度）
- 留资解锁完整报告 → 顾问 1v1 跟进

### 顾问后台 (`/admin/leads`)
- 线索列表：P0/P1/P2/P3 优先级视觉分组 + 跟进状态筛选
- 详情区：企业画像摘要 / 顾问报告 / 销售话术一键复制 / 跟进表单

### 模型 Provider 配置 (`/settings/models`)
- 支持任意 OpenAI-compatible API（DeepSeek / OpenAI / 自定义）
- API Key 安全存储（DB 明文，前端仅显示 masked_key）
- 测试连接 + 启用/停用

### MCP 服务 (`/settings/mcp`)
- 管理远程 MCP Server（HTTP JSON-RPC / SSE / Stdio）
- 连接测试 + 工具发现 + 动态注册到 Agent 工具池
- 工具命名协议 `mcp__{server}__{tool}`（译自 Claude Code）

### 知识库管理 (`/knowledge`)
- 知识片段 CRUD + embedding 重建
- TopK 检索测试（query → 查看命中标题/距离/预览）
- 报告详情展示 RAG 知识来源

## 工具清单

### 本地确定性工具（7 个）
| 工具 | 作用 |
|------|------|
| `question_catalog.read` | 返回题库、关键问题、display 映射 |
| `readiness.check` | 确定性判断（score_ready / report_ready 两层） |
| `score.calculate` | answers → ScoringResult |
| `report.split` | RawAIReport → UserReport + LeadReport |
| `report.guard` | 用户报告安全扫描 |
| `memory.recall` | 关键词检索 Memory 目录 |
| `memory.save` | 写入 Memory Markdown 文件 |

### 外部 AI 工具（5 个）
| 工具 | 作用 |
|------|------|
| `dialogue.deepseek` | 基于缺失项 + 画像摘要 + 已收集题号生成追问 |
| `extract_answers.deepseek` | 从对话提取 slots / answers / branch |
| `rag.search` | 检索报告参考知识 |
| `report.generate.deepseek` | 生成 RawAIReport |
| `report.audit.deepseek` | 审计报告质量与安全 |

### MCP 工具（动态）
远程 MCP Server 的工具自动注册，命名格式 `mcp__{server}__{tool}`。

## Skills

| Skill | 触发条件 | 作用 |
|-------|---------|------|
| `market-access` | 确定目标市场后 | 组合 RAG + MCP，分析关税/认证/合规 |

可扩展：在 `.claude/skills/*/SKILL.md` 中添加 Markdown + YAML frontmatter 即可注册。

## 核心闭环

```
对话诊断 → 结构化提取 → 评分 → 报告(含审计) → 留资解锁 → 顾问跟进
```

- 对话轮次无上限，用户主导终止
- 信息不足 → 返回缺失项列表，不生成 0 分模板
- 模板兜底仅用于技术故障
- RAG 失败 → 空 context 继续 AI 报告
- 一次诊断锁定 provider/model，切换只影响下一次

## 项目结构

```
backend/
├── app/
│   ├── agent/
│   │   ├── runner.py        # run_agent_event() 主入口
│   │   ├── tools/           # 12 个工具（local/ + external/）
│   │   ├── mcp/             # MCP 客户端 + adapter + 命名
│   │   └── skills/          # Skill 注册中心 + 发现 + 内建 skills
│   ├── api/                 # FastAPI 路由
│   ├── auth/                # JWT + OAuth state
│   ├── reports/             # 报告拆分/安全扫描/模板
│   ├── schemas/             # Pydantic 数据模型
│   ├── scoring/             # 题库 + 评分引擎
│   └── services/            # DeepSeekClient / RAG / Memory / MCP
├── tests/
│   ├── unit/                # 纯函数 + Tool Runtime + Agent 协议
│   └── integration/         # API + AgentGraph + AI 集成
└── config.py                # 全局 Settings

frontend/
├── app/                     # Next.js App Router 页面
│   ├── chat/                # 诊断工作台
│   ├── reports/             # 诊断报告
│   ├── admin/leads/         # 顾问后台
│   ├── knowledge/           # 知识库管理
│   └── settings/            # 模型设置 / MCP 服务
├── components/              # AppShell / UserReportCard / DiagnosisProgressPanel / AgentTracePanel / AuthBar
├── hooks/                   # useStreaming
├── lib/                     # API 客户端 / 流式解析 / sessionDrafts
├── scripts/                 # 前端测试脚本（7 个 test suite）
└── styles/                  # app-shell.css (Light Blueprint 视觉系统)
```

## 配置项

| 配置项 | 默认值 | 说明 |
|------|:---:|------|
| `DEEPSEEK_API_KEY` | - | AI API 密钥 |
| `DEEPSEEK_MODEL` | deepseek-v4-flash | 默认模型 |
| `DATABASE_URL` | postgresql+asyncpg://... | PostgreSQL 连接 |
| `DEV_MODE` | false | 开发模式（启用 /auth/dev-login） |
| `DIALOGUE_MAX_TOKENS` | 1024 | 对话生成 max_tokens |
| `REPORT_MAX_TOKENS` | 4000 | 报告生成 max_tokens |
| `REPORT_ESCALATED_MAX_TOKENS` | 8000 | length 升级重试 |
| `MAX_AGENT_STEPS` | 16 | 图内最大步骤保护 |

详见 `backend/.env.example`。

## 文档

- [工程计划书](docs/agent-engineering-plan.md) — Phase 38-50 全路线图
- [领域术语表](CONTEXT.md)
- [架构决策记录](docs/adr/)
- [评分设计](docs/scoring-design.md)
- [题库权威源](docs/questionnaire-canonical.md)
- [产品需求](docs/superpowers/specs/2026-06-24-chuhai-agent-prd.md)
- [密钥轮换指南](docs/security-key-rotation.md)
- [Claude Code 工程参考](reference/claude-code-analysis/) — Tool 协议、MCP、Skills、Memory
- [SonettoHere 产品参考](reference/SonettoHere/) — Agent 产品工作台设计

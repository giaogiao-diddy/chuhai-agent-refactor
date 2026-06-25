# 深度未来 — 企业出海诊断 Agent 构建计划

> 技术栈：Python FastAPI + MySQL + pgvector + LangGraph + DeepSeek + React Next.js + CloudBase Run

---

## Phase 1：项目骨架 + 数据库

**目标**：空 FastAPI 能启动，数据库能连，表能建

| # | 任务 | 产出 |
|:--:|------|------|
| 1.1 | 初始化 Python 项目：`pyproject.toml` / requirements.txt / 目录结构 | 项目骨架 |
| 1.2 | `config.py`：Settings 类，所有配置集中（DB URL、DeepSeek Key、微信 OAuth 等） | 配置管理 |
| 1.3 | SQLAlchemy 2.0 模型：users / assessments / answers / questions / options / reports / lead_reports / knowledge_base | `models/` |
| 1.4 | Alembic 初始化 + 首次迁移生成 | `migrations/` |
| 1.5 | `core/db.py`：异步数据库连接池（asyncmy） + 依赖注入 get_db | 数据库连接 |
| 1.6 | pgvector 扩展启用 + 向量字段建表（knowledge_base.embedding） | 向量存储就绪 |
| 1.7 | `main.py`：FastAPI 入口 + CORS + 健康检查 /health | 能启动 |

**验证**：`uvicorn main:app --reload` 启动成功，`/health` 返回 200

---

## Phase 2：评分引擎 + 规则模块（纯 Python 翻译）

**目标**：4 个核心规则模块全部通过单元测试

| # | 任务 | 源文件（Node.js） | 产出 |
|:--:|------|-------------------|------|
| 2.1 | `services/scoring.py`：calculateScores + feasibilityTag + leadPriority | [scoring.js](cloudfunctions/shared/scoring.js) | 评分引擎 |
| 2.2 | `services/agent_state.py`：槽位枚举 + 8 轮熔断 + 2 次失败兜底 + getMissingSlots | [agentState.js](cloudfunctions/shared/agentState.js) | 槽位状态机 |
| 2.3 | `services/slot_cleaning.py`：置信度三级分流 + 槽位合并 + 数组去重 | [conversationSlots.js](cloudfunctions/shared/conversationSlots.js) | 槽位清洗 |
| 2.4 | `services/report_guard.py`：24 字段审计 + 7 条违禁词 + 字数检查 + 报告拆分 | [reportGuard.js](cloudfunctions/shared/reportGuard.js) | 报告守卫 |
| 2.5 | `services/default_policy.py`：缺失题保守补全 + imputed 标记 | [defaultAnswerPolicy.js](cloudfunctions/shared/defaultAnswerPolicy.js) | 缺题补全 |
| 2.6 | `services/slot_to_score.py`：槽位 → 评分输入映射（含缺题补全） | [slotToScoreMapper.js](cloudfunctions/shared/slotToScoreMapper.js) | 槽位评分映射 |

**验证**：`pytest tests/unit/ -v` 全部通过

---

## Phase 3：向量化 RAG

**目标**：行业知识库语义检索上线

| # | 任务 | 产出 |
|:--:|------|------|
| 3.1 | `services/embedding.py`：DeepSeek text-embedding 调用封装 | 向量化服务 |
| 3.2 | 知识库种子数据：6 个行业（健身器材/消费电子/服装纺织/家居用品/宠物用品/通用）的打法文案 + 风险点 | `knowledge_base` 表数据 |
| 3.3 | 批量向量化脚本：遍历 knowledge_base 生成 embedding 存入 pgvector | 向量索引 |
| 3.4 | `services/rag_retriever.py`：语义检索 + 行业标签过滤 + 市场加权 → Top 3 召回 | 向量 RAG |

**验证**：输入"健身器材 东南亚"→ 返回健身器材行业知识而非服装纺织

---

## Phase 4：多 Agent 协作框架（LangGraph）

**目标**：对话 → 报告 → 审计 三 Agent 协作跑通

| # | 任务 | 产出 |
|:--:|------|------|
| 4.1 | 安装 LangGraph + LangChain DeepSeek 集成 | 依赖就绪 |
| 4.2 | `services/prompts.py`：对话 Agent System Prompt + 报告 Agent System Prompt + 审计 Agent Prompt | Prompt 管理 |
| 4.3 | `services/agent_graph.py`：LangGraph StateGraph 定义 | 状态图 |
| 4.4 | 对话 Agent 节点：接收用户消息 → 调 DeepSeek → 提取槽位 → 调 Function Calling | 对话 Agent |
| 4.5 | 报告 Agent 节点：消费完整槽位 + RAG 上下文 → 生成诊断报告 JSON | 报告 Agent |
| 4.6 | 审计 Agent 节点：validateStructure → 不合格返回报告 Agent 重写（最多 2 次）→ 合格放行 | 审计反馈循环 |
| 4.7 | 兜底路径：审计 2 次不通过 → 切模板报告 | 降级策略 |

**验证**：模拟完整槽位输入 → 报告 Agent 生成 → 审计 Agent 校验 → 通过或重写

---

## Phase 5：SSE 流式对话 API

**目标**：前端能收流式 token

| # | 任务 | 产出 |
|:--:|------|------|
| 5.1 | `app/api/conversation.py`：POST `/conversation/start` → 初始化对话 + 返回开场白（流式） | 开始对话 |
| 5.2 | POST `/conversation/continue` → DeepSeek stream=True → `StreamingResponse` 逐 token 推送 | SSE 流式 |
| 5.3 | POST `/conversation/finish` → 触发报告生成流水线 | 完成对话 |
| 5.4 | `schemas/conversation.py`：Pydantic 请求/响应模型 | API Schema |
| 5.5 | 幂等查重：client_message_id 数据库去重 | 防重复计费 |

**验证**：`curl -N POST /conversation/continue` 看到 SSE token 流

---

## Phase 6：微信登录 + 用户系统

**目标**：用户能扫码登录

| # | 任务 | 产出 |
|:--:|------|------|
| 6.1 | `app/api/auth.py`：微信 OAuth 2.0 授权码流程（/auth/wechat/login + /auth/wechat/callback） | 微信登录 |
| 6.2 | `core/auth.py`：JWT Token 签发 + 验证中间件 | 鉴权 |
| 6.3 | `services/user_service.py`：用户创建/查询/更新 | 用户服务 |

**验证**：微信扫码 → 回调 → 获取 JWT → 请求受保护 API 成功

---

## Phase 7：Next.js 前端骨架 + Agent 对话页

**目标**：用户能看到对话页面并收发消息

| # | 任务 | 产出 |
|:--:|------|------|
| 7.1 | Next.js 项目初始化 + shadcn/ui 配置 + Tailwind | 前端骨架 |
| 7.2 | 微信扫码登录组件 | 登录页 |
| 7.3 | Agent 对话页：气泡列表 + 输入框 + EventSource 流式接收 | 对话 UI |
| 7.4 | 打字机光标动画 + 发送 loading 状态 + 错误重试 | 体验细节 |
| 7.5 | 对话结束 → "生成报告"按钮 → 调用 finish API | 对话闭环 |

**验证**：扫码登录 → 开始对话 → 收发消息 → 流式渲染 → 点击生成报告

---

## Phase 8：报告展示 + 留资解锁

**目标**：完整产品闭环

| # | 任务 | 产出 |
|:--:|------|------|
| 8.1 | 部分报告页：summary_report 展示 + "添加顾问解锁完整报告"CTA | 报告预览 |
| 8.2 | 企微二维码展示 + 留资表单（姓名 + 手机号） | 留资页 |
| 8.3 | 完整报告页：full_report 全部维度展示 | 完整报告 |

**验证**：对话完成 → 看部分报告 → 留资 → 看完整报告

---

## Phase 9：模板兜底 + 错误处理

**目标**：AI 挂了也能出报告

| # | 任务 | 产出 |
|:--:|------|------|
| 9.1 | `services/template_report.py`：从 Node.js reportTemplate.js 翻译 | 模板报告 |
| 9.2 | AI 超时 / 审计失败 / JSON 解析失败 → 自动切模板 | 兜底逻辑 |
| 9.3 | 统一错误响应中间件：`{ "data": ..., "error": ... }` | 错误处理 |

**验证**：故意传错误 API Key → AI 失败 → 模板报告正常生成

---

## Phase 10：Docker + CloudBase Run 部署

**目标**：线上可访问

| # | 任务 | 产出 |
|:--:|------|------|
| 10.1 | `Dockerfile`：Python 3.12 + FastAPI + uvicorn | 容器化 |
| 10.2 | Next.js `docker-compose.yml`：前端容器 + 后端容器 + MySQL + pgvector | 编排 |
| 10.3 | CloudBase Run 配置：环境变量、端口、健康检查 | 部署配置 |
| 10.4 | 数据库迁移脚本：Alembic upgrade head | 数据库初始化 |
| 10.5 | 种子数据脚本：31 题 + 分值 + 知识库 + 向量 | 初始数据 |

**验证**：浏览器访问线上 URL → 完整产品流程跑通

---

## 开发顺序总结

```
Phase 1 ──▶ Phase 2 ──▶ Phase 3 ──▶ Phase 4 ──▶ Phase 5
 项目骨架    评分引擎    向量RAG    多Agent    SSE API
                                    
Phase 6 ──▶ Phase 7 ──▶ Phase 8 ──▶ Phase 9 ──▶ Phase 10
微信登录    前端对话页  报告+留资   兜底降级    Docker部署
```

**并行机会**：Phase 6（登录）和 Phase 7（前端）可以在 Phase 4-5 的同时开始。

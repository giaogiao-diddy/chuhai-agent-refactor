# 出海诊断 Agent — 项目工程规范

> 当前项目：出海诊断 Agent。  
> 本文件是 Claude Code / DeepSeek / Codex 进入项目后的工程规范入口。  
> 旧项目代码已迁移至 `legacy/`，仅作历史参考，不参与新项目开发。

---

## 1. 必读顺序

每次开始新 phase 或大改动前，按顺序阅读：

1. `CONTEXT.md` — 领域术语和当前裁决
2. `docs/agent-engineering-plan.md` — Agent 引擎重构计划
3. `docs/adr/` — 架构决策记录
4. `docs/questionnaire-canonical.md` — 题库权威源
5. `docs/scoring-design.md` — 评分权重、标签、维度口径
6. `docs/superpowers/specs/2026-06-24-chuhai-agent-prd.md` — 产品需求
7. `reference/claude-code-analysis/` — Claude Code 工程模式参考，仅学习架构思想
8. 当前 phase 相关代码和测试

不要只读 PRD 或只读单个 Markdown 后直接改代码。

---

## 2. 当前产品目标

- 面向中国企业主的出海可行性诊断 Agent。
- 核心闭环：对话诊断 → 结构化提取 → 评分 → 报告 → 留资解锁 → 顾问跟进。
- 当前重构目标：从“API 编排 + 若干独立节点”升级为真正的 AgentGraph 驱动产品。
- 参考 `reference/claude-code-analysis/` 中 Claude Code 的工程模式：Tool 协议、执行循环、并发安全、上下文管理、状态边界。

重要裁决：

- 对话轮数不再有上限。旧 PRD / 旧规范中的“8 轮硬熔断”已废弃。
- 信息不足不是技术失败，禁止生成 0 分模板报告。
- 模板兜底只用于技术失败，例如报告生成失败、审计多次失败。
- RAG 检索失败不应切模板，应使用空 RAG context 继续报告生成。
- API handler 不能长期承担业务编排职责，目标是只传 `AgentEvent`。

---

## 3. 技术栈

| 层 | 技术 | 约束 |
|---|---|---|
| 后端 | Python 3.12 / FastAPI | 异步优先 |
| Agent 编排 | LangGraph | 目标为单一 AgentGraph + 条件路由 |
| ORM | SQLAlchemy 2.0 + asyncpg | DB 操作走 ORM |
| DB | PostgreSQL + pgvector | ADR-0007 |
| AI | DeepSeek API | 对话、提取、报告、审计必须用真实 API 测试 |
| Embedding | 阿里云百炼 / OpenAI-compatible embeddings | 通过环境变量配置 |
| 前端 | Next.js App Router / React / TypeScript | POST fetch ReadableStream，不用 EventSource |
| Auth | 微信 OAuth + JWT | OAuth state 必须校验 |

不引入新依赖，除非当前栈无法完成当前 phase 的验收目标。

---

## 4. 目标架构规则

### 4.1 分层

```text
[API / Frontend]
只传 AgentEvent
        |
        v
[AgentGraph]
receive -> tools -> route
        |
        v
[Tool Runtime]
registry / executor / retry
        |
        v
[Domain Services]
scoring / reports / rag / db
```

### 4.2 API 层

API 层只负责：

- 请求校验
- 鉴权
- 组装 `AgentEvent`
- 调用 AgentGraph
- 提交事务
- 返回安全 DTO

API 层禁止：

- 手动编排 `extract -> score -> report`
- 直接决定业务下一步
- 返回内部技术字段
- 泄露 `lead_score`、`lead_priority`、`sales_followup`、`consultant_notes`

### 4.3 AgentGraph

AgentGraph 是业务流转核心。

目标职责：

- 接收 `AgentEvent`
- 调用提取、readiness、对话、评分、RAG、报告、审计、保存等工具
- 根据状态进入明确 `TerminalState`
- 区分信息不足、技术失败、审计失败、用户取消

每次图执行必须有明确终态：

- `awaiting_user`
- `missing_info`
- `unsupported_branch`
- `completed`
- `completed_with_template`
- `failed`
- `aborted`
- `max_steps_exceeded`

图内可以有 `MAX_AGENT_STEPS` 技术保护，但产品对话轮次无上限。

### 4.4 Tool Runtime

Tool 是运行时协议对象，不是普通函数。

每个 Tool 必须声明：

- name
- description
- input schema
- output schema
- `is_read_only`
- `is_concurrency_safe`
- `is_destructive`
- `max_retries`
- timeout

默认 fail-closed：

- `is_read_only = False`
- `is_concurrency_safe = False`
- `is_destructive = False`
- `max_retries = 0`

只有明确声明 `is_read_only=True` 且 `is_concurrency_safe=True` 的工具可以并发。

工具错误分类：

- `TRANSIENT`
- `RATE_LIMITED`
- `AUTH_FAILED`
- `LENGTH_EXCEEDED`
- `STRUCTURED_OUTPUT_ERROR`
- `PERMANENT`

`ToolResult.error` 只封装预期错误。编程错误、DB 事务错误、schema 定义错误仍应抛出，由 AgentGraph 转为 `failed`。

### 4.5 Tool 清单与副作用边界

Phase 39 重构时，工具按以下边界建模。不要把普通 service 函数直接塞进 AgentGraph。

本地只读工具：

| 工具名 | 作用 | 并发 |
|---|---|---|
| `question_catalog.read` | 返回题库、关键问题、display 映射、维度中文名 | 可并发 |
| `readiness.check` | 判断是否足够生成报告，返回 missing_items / next_questions | 可并发 |
| `score.calculate` | answers → ScoringResult | 可并发 |
| `report.split` | RawAIReport → UserReport + LeadReport | 可并发 |
| `report.guard` | 用户报告安全扫描 | 可并发 |

外部只读工具：

| 工具名 | 作用 | 重试 |
|---|---|---|
| `dialogue.deepseek` | 基于缺失项生成下一轮追问 | transient 可重试 |
| `extract_answers.deepseek` | 从对话提取 slots / answers / branch | transient 可重试 |
| `rag.search` | 检索报告参考知识 | 失败返回空 RAG context |
| `report.generate.deepseek` | 生成 RawAIReport | transient / length / structured output 按规则重试 |
| `report.audit.deepseek` | 审计报告质量和安全 | transient 可重试 |

写入工具：

| 工具名 | 作用 | 并发 |
|---|---|---|
| `assessment.complete` | 保存最终 assessment、报告和分数快照 | 必须串行 |

持久化注意：

- 对话消息、slots、answers、scoring_result 的过程性保存是 AgentGraph 框架职责，不是显式业务工具。
- DB write 工具不得声明 `is_concurrency_safe=True`。
- RAG/search 类只读工具可以并发，但不得因失败切换模板报告。

---

## 5. 当前重构路线

严格按 `docs/agent-engineering-plan.md` 分 phase 执行。

已完成 Phase 38-41.5（Agent 引擎重构全线贯通）：

1. ~~Phase 38：安全上线底线~~ ✅
2. ~~Phase 39.1-39.9：Tool Runtime + Agent 协议 + 接管 + 配置化 + Display + 死代码~~ ✅
3. ~~Phase 40：Memory 系统~~ ✅
4. ~~Phase 41-41.5：Memory recall 接入 + 流式修复 + 可观测性 + 对话-报告断裂修复 + 过早收尾修复~~ ✅

下一阶段 Phase 42-50（Agent 产品工作台，参考 SonettoHere）：

1. Phase 42：模型 Provider 配置中心
2. Phase 43：Agent 运行时模型选择
3. Phase 44：AppShell + 设置中心
4. Phase 45：诊断工作台
5. Phase 46：Agent Runtime Trace
6. Phase 47：知识库管理与 RAG 可视化
7. Phase 48：报告页与顾问后台产品化
8. Phase 49：会话管理
9. Phase 50：前端测试与发布质量

详见 `docs/agent-engineering-plan.md` v2.0。

每次只执行一个 phase。禁止一次性执行 “Phase 39 全部”。

### 5.1 Phase 执行约束

每次给 DeepSeek / Claude Code / Codex 执行 phase 时，必须遵守：

- 先阅读 `docs/agent-engineering-plan.md` 和本文件。
- 只做当前 phase，不做下一 phase。
- 不顺手重写前端、UI、目录结构或无关模块。
- 不引入新依赖，除非当前技术栈无法完成当前 phase 的验收目标。
- 不写过度兜底代码；信息不足、技术失败、权限失败必须明确区分。
- 涉及 DeepSeek 的正常路径测试必须使用真实 API，不允许 mock。
- 完成后必须输出：修改文件、关键设计、测试结果、未完成项。

禁止使用模糊任务描述，例如：

- “把 AgentGraph 全部重构完”
- “顺便优化一下代码”
- “把兜底做完善”
- “把可能出错的地方都防一下”

---

## 6. 题库和评分规范

### 6.1 权威源

题库权威源层级见 `docs/questionnaire-canonical.md`：

- P0：`docs/scoring-design.md`
- P1：`backend/app/scoring/questionnaire.py`
- P2：`有出海经验题目.md`
- P3：`企业出海可行性评估智能体（内容选项）.md`

代码执行真源头是 `backend/app/scoring/questionnaire.py`。

### 6.2 题号模型

- 用户可见题号：`display_id`，Q1-Q31，共 31 个。
- 内部计分单元：`Question.id`，当前共 37 个。
- Q2、Q3、Q10 有子题，例如 Q2a/Q2b/Q2c。

Phase 39.8 前不得擅自改题库结构。

### 6.3 评分

- `scoring_result` JSONB 是评分业务真源头。
- `feasibility_score`、`lead_score`、`tag`、`lead_priority` 是查询快照，必须从 `scoring_result` 派生。
- 评分权重、标签阈值、维度中文名不走环境变量。
- 用户报告禁止出现线索分和销售字段。

---

## 7. 报告、审计、兜底规则

### 7.1 报告生成

- 报告生成必须输出严格 JSON，并通过 Pydantic 校验。
- DeepSeek 返回 `finish_reason="length"` 时，只允许一次升级 `max_tokens` 的 clean retry。
- 禁止拼接半截 JSON。
- 禁止把半截报告展示给用户。

### 7.2 审计重试

审计失败不是简单重复同一个 prompt。

规则：

1. 第 1 次生成报告并审计。
2. 审计失败后，把 `audit.issues` 注入下一次 report prompt。
3. 最多 3 次生成尝试。
4. 第 3 次仍未通过，走模板兜底。

禁止：

- 暴露 audit issues 给用户
- 返回未通过审计的 AI 报告
- 建复杂 `ReportRewriteAgent`

### 7.3 模板兜底

模板兜底只用于技术失败：

- 报告生成失败
- 审计多次失败
- LLM 服务不可用

禁止用于：

- 信息不足
- 无出海经验分支未开放
- 用户过早点击生成报告

### 7.4 RAG

RAG 是增强，不是前置依赖。

- RAG 成功：注入参考知识。
- RAG 失败：使用空 RAG context 继续生成 AI 报告。
- RAG 失败不切模板。

### 7.5 错误恢复速查

错误恢复必须服务于 Agent 决策，不允许堆叠大段兜底代码。

| 场景 | 行为 |
|---|---|
| `AUTH_FAILED` / 401 / 403 | 不重试，进入明确失败或鉴权错误 |
| `RATE_LIMITED` / 429 | 按工具配置退避重试 |
| 网络超时 / 临时服务错误 | 按工具配置有限重试 |
| `finish_reason="length"` | 仅允许一次升级 max_tokens 后 clean retry |
| JSON 结构化输出缺字段 | 注入校验错误，最多重试一次 |
| RAG 检索失败 | 空 RAG context 继续 AI 报告生成 |
| 审计失败 | 把 audit issues 注入下一次 report prompt，最多 3 次 |
| 第 3 次审计仍失败 | 模板兜底 |
| 信息不足 | 返回 missing_info，不评分、不模板兜底 |
| Q5=D 无出海经验分支 | 返回 unsupported_branch，不评分、不模板兜底 |

禁止：

- 用 `except: pass` 消化失败。
- 把技术失败原文返回给用户。
- 为每个理论异常写独立兜底分支。
- 用模板报告掩盖信息不足。

---

## 8. 对话规范

- 对话没有轮数上限。
- 前端可以提示“可以生成报告”，但不强制终止。
- Agent 必须优先追问报告关键问题，不应在关键信息不足时继续给投放、运营、预算分配等执行建议。
- LLM 调用可以只传窗口内消息，但前端和状态中的完整对话历史不应丢失。
- 单条用户消息仍限制为 500 字符。

信息不足时：

- 返回 `missing_items` / `next_questions`
- 不生成 0 分报告
- 不写完成态 assessment

无出海经验分支：

- 当前继续搁置。
- Q5=D 时进入 `unsupported_branch`，不评分、不生成 0 分模板。
- 返回明确文案：深度诊断优先支持已有出海经验企业。

### 8.1 关键问题与 readiness

“关键问题”只指生成评分和报告所必需的信息，不等于闲聊中的所有有用信息。

关键问题由确定性规则维护：

- `readiness.check` 负责生成 `missing_items`。
- LLM 只能根据 `missing_items` 改写自然语言追问，不能自行决定哪些信息算缺失。
- 追问优先级高于执行建议。缺 Q5、目标市场、预算、产品/行业、咨询意向等核心信息时，不应继续给投放计划。
- 用户点击“生成报告”时，如果 readiness 不通过，返回 `missing_info` 和缺失项，不生成 0 分报告，不写完成态 assessment。
- 题库问法可以自然对话化，但选项答案仍必须落回 `Question.id` / `option_id`。

Agent 回复的目标不是“显得懂运营”，而是稳定收集报告生成所需证据。

---

## 9. 流式通信规范

使用 POST + fetch ReadableStream，不使用浏览器原生 EventSource。

原因：

- 对话需要 JSON body，例如 `state`、`message`、`anonymous_user_id`
- EventSource 只支持 GET，不适合本项目

SSE event：

```text
data: {"type":"delta","content":"..."}\n\n
data: {"type":"done","state":{...}}\n\n
data: {"type":"error","message":"...","state":{...}}\n\n
```

约束：

- 必须是真流式，禁止假打字机。
- `error.message` 使用安全文案，不返回原始异常。
- `done.state` 必须是安全 `ConversationClientState`。
- 不泄露 raw_report、lead_report、sales_followup、consultant_notes。

---

## 10. 持久化规范

参考 Claude Code 的工程思想：框架负责记住一切，Agent 负责诊断决策。

| 内容 | 谁负责 | 何时 |
|---|---|---|
| 对话消息 | AgentGraph / API 框架 | 每轮结束 |
| slots / answers | AgentGraph / extraction 后 | 每轮结束 |
| scoring_result | AgentGraph / score 后 | finish 流程 |
| final reports | `assessment.complete` | finish 成功 |
| lead submission | 独立 API | 用户留资 |
| consultant followup | 顾问后台 API | 顾问操作 |

当前阶段不要引入长期 Memory 系统。Memory 放在 Phase 40。

---

## 11. 代码规范

### Python

- 使用 Python 3.12 类型语法：`list[str]`、`dict[str, Any]`、`str | None`
- Pydantic v2 用于请求、响应、LLM 输出、Tool I/O
- FastAPI 路由、DB、LLM 调用使用 `async def`
- 纯计算逻辑使用同步 `def`
- 导入顺序：stdlib → third-party → local
- 字符串默认双引号
- 所有配置通过 `config.py` Settings 读取
- 禁止硬编码真实密钥
- 禁止 `except: pass`
- 禁止 `from xxx import *`
- 禁止在 `models/` 写业务逻辑
- 禁止在 API 路由写业务编排
- 禁止为不可能发生的场景写大量兜底代码

### Tool 代码

- 每个 Tool 必须有 input/output schema
- Tool 默认不可并发
- 写工具必须串行
- 401/403 不重试
- 429/timeout 可以按工具配置重试
- RAG/search 类只读工具可以声明并发安全
- DB write 工具不能声明并发安全

### Frontend

- API URL 必须通过 `NEXT_PUBLIC_API_BASE_URL` 配置
- 生产环境不能默认指向 `localhost:8000`
- token 当前 MVP 存 `sessionStorage`，后续可升级 HttpOnly cookie
- 报告渲染前必须走安全扫描
- 用户端禁止展示顾问字段
- `npm run typecheck` 和 `npm run build` 必须通过

---

## 12. 测试规范

### TDD 流程

1. 写测试
2. 跑测试确认失败
3. 写最小实现
4. 重构
5. 跑相关测试

### 测试分层

| 层级 | 位置 | 内容 | AI |
|---|---|---|---|
| unit | `backend/tests/unit/` | 纯函数、Tool 协议、评分、报告守卫 | 不需要 |
| integration | `backend/tests/integration/` | API、AgentGraph、DB、OAuth、报告流转 | 视情况 |
| ai | `backend/tests/integration/` + `@pytest.mark.ai` | DeepSeek 对话、提取、报告、审计、embedding | 真实 API |

### AI 测试规则

- 涉及 DeepSeek 的正常路径必须用真实 API。
- 禁止 mock DeepSeek 对话、报告、提取、审计、embedding。
- 如果 key 缺失，可以 `pytest.skip`，但必须说明原因。
- key 存在但 API 失败，测试应失败，不能静默降级。
- 测试可用小输入、低 max_tokens 控制成本。

### 常用命令

```bash
cd backend
python -m pytest tests/ -v -m "not ai"
python -m pytest tests/integration/ -v -m ai

cd frontend
npm run test:parser
npm run test:report-safety
npm run test:auth
npm run typecheck
npm run build
```

---

## 13. 安全规范

- `backend/.env`、`frontend/.env` 不得提交。
- 真实 API key 不得出现在代码、文档、测试、提交历史中。
- 已在对话中暴露过的 key 按泄漏处理，必须轮换。
- `JWT_SECRET_KEY` 禁止使用 `change_me`，禁止过短。
- 微信 OAuth state 必须校验，防止 CSRF。
- 用户端响应禁止出现：
  - `lead_score`
  - `lead_priority`
  - `sales_followup`
  - `consultant_notes`
  - `raw_report`
  - `lead_report`
  - `audit_result`
  - `scoring_result`

---

## 14. Git 规范

- 分支命名：`feat/<功能>`、`fix/<问题>`、`docs/<文档>`、`test/<测试>`、`refactor/<范围>`
- commit message：`<type>: <简述>`
- type：`feat`、`fix`、`test`、`refactor`、`docs`、`chore`
- 每个 commit 保持可测试、可回滚
- 不提交 `.env`、缓存、构建产物

---

## 15. 待确认事项

| 事项 | 状态 |
|---|---|
| 微信开放平台正式配置 | 待确认 |
| 企微二维码生产 URL | 待确认 |
| 无出海经验题库 | 待老板提供 |
| 生产环境 API URL | 待部署前确认 |
| AgentGraph 重构 | ✅ 已完成 Phase 39 |
| Memory 系统 | ✅ 已完成 Phase 40-41；后续可视化见 Phase 46/49 |
| Provider 存储方案 | ✅ PostgreSQL；API Key MVP 服务端存 DB 明文，前端仅显示 masked_key |
| 诊断模型切换 | ✅ 一次诊断锁定 provider/model；切换只影响下一次新诊断 |
| 会话草稿 | ✅ Phase 49 先用 localStorage，不新增服务端 draft 表 |

---

## 16. 本地运行

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

---

## 17. Agent Skills / 项目协作

GitHub Issues：`giaogiao-diddy/chuhai-agent-refactor`。

相关文档：

- `docs/agents/issue-tracker.md`
- `docs/agents/triage-labels.md`
- `docs/agents/domain.md`

`CONTEXT.md` 是当前领域上下文入口。后续领域裁决优先更新 `CONTEXT.md` 和对应 ADR。

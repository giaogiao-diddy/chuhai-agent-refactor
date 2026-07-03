# 出海诊断 Agent — Agent 引擎重构工程计划书

> 版本：v2.0  
> 日期：2026-07-01  
> 目标：Phase 38-41 已完成 Agent 引擎重构。Phase 42-50 将项目升级为可配置、可观察、可运营的 Agent 产品工作台。  
> 参考：`reference/claude-code-analysis/`（Claude Code 工程模式）、`reference/SonettoHere/`（LangChain ReAct Agent 产品化）。

---

## 0. 重构原则

### 0.1 这次重构要解决的问题

Phase 38 前项目已经跑通“对话 → 提取 → 评分 → 报告 → 留资 → 顾问跟进”闭环，但架构仍偏脚本化：

- API handler 直接编排 `extract / score / report / audit / save`
- 工具没有统一协议，无法明确只读、写入、并发安全、重试语义
- 信息不足、LLM 失败、审计失败、RAG 失败混在同一类兜底逻辑里
- AgentGraph 没有真正成为业务流转核心
- 对话提问没有稳定围绕报告关键问题推进

本次重构目标不是“多写代码”，而是建立可解释、可测试、可扩展的 Agent 引擎。

### 0.2 参考 Claude Code 的哪些工程思想

参考重点：

- Tool 是运行时协议对象，不是普通函数
- Tool 必须声明输入输出、是否只读、是否可并发、是否有破坏性、重试策略
- 并发默认关闭，只有显式声明安全的只读工具才能并发
- 执行循环由 Agent 内核拥有，API / UI 只传事件
- 工具错误要回流成状态，供下一步决策使用
- 上下文、记忆、持久化、技术运行态要分层，不混成一个无边界对象

不参考：

- 不复制 Claude Code 的 CLI / TUI / 文件编辑 / Sandbox 架构
- 不引入 MCP、Smithery、多 Agent 协作、RL、复杂权限系统
- Phase 39 不引入长期 Memory 系统；Memory 已在 Phase 40-41 完成

### 0.3 全局约束

- 不引入新依赖，除非已有栈无法完成
- 不做过度兜底代码
- 不吞异常，不写 `except: pass`
- 不把“信息不足”当作模板兜底
- 不让 API handler 决定业务下一步
- 保持现有 API 响应结构尽量兼容前端
- 所有涉及 DeepSeek 的正常路径测试必须使用真实 API，不 mock

---

## 1. 目标架构

### 1.1 分层

```text
+-----------------------------+
| API / Frontend             |
| 只传 AgentEvent             |
+-------------+---------------+
              |
              v
+-----------------------------+
| AgentGraph                  |
| receive -> tools -> route   |
+-------------+---------------+
              |
              v
+-----------------------------+
| Tool Runtime                |
| registry / executor / retry |
+-------------+---------------+
              |
              v
+-----------------------------+
| Domain Services             |
| scoring / reports / rag / db|
+-----------------------------+
```

API 层只负责：

- 校验请求
- 组装 `AgentEvent`
- 调用 AgentGraph
- 提交事务
- 返回安全 DTO

API 层不再直接调用：

- `extract_answers_node`
- `score_node`
- `report_node`
- `run_scoring_pipeline`
- `run_report_pipeline`

### 1.2 核心对象

| 对象 | 作用 |
|---|---|
| `AgentEvent` | API 传入的用户事件：`user_message` / `finish_requested` |
| `AgentState` | 当前阶段仍作为图内状态容器，后续再拆分 |
| `TerminalState` | 单次图执行的出口状态 |
| `ToolDefinition` | 工具协议定义 |
| `ToolResult` | 工具执行结果，包含数据或预期错误 |
| `ToolRegistry` | 工具注册、查找、去重 |
| `ToolExecutor` | 根据工具元数据执行、并发分区、重试 |
| `ReadinessResult` | 信息是否足够生成报告的确定性判断结果 |

---

## 2. Phase 拆分

> Phase 38-41.5 已完成，以下历史阶段仅作背景和验收口径，不再重复执行。

## Phase 38：安全上线底线

### 目标

先修发布前不能绕过的安全问题。Agent 架构重构之前，必须保证认证和密钥不是明显漏洞。

### OAuth state 设计

**方案：签名 state，不引入额外存储。**

- `state` = `base64url(nonce:timestamp).base64url(hmac_sha256(payload, JWT_SECRET_KEY))`
- 签名密钥复用 `JWT_SECRET_KEY`，过期时间 10 分钟
- `login-url` 响应增加 `state` 字段，前端保存到 `sessionStorage`
- callback：前端先比对 sessionStorage → 匹配后调后端 → 后端验签+查过期
- 验签失败 → 400，不调微信 token API

### 参考

- `backend/app/api/auth.py`
- `backend/app/auth/jwt.py`
- `frontend/lib/api.ts`
- `reference/claude-code-analysis/analysis/02-security-analysis.md`

### 范围

做：

- 签名 state 生成与校验（不引入 Redis/DB）
- `JWT_SECRET_KEY` 强校验，禁止 `change_me` 和过短 secret
- `.env.example` 改为明确的安全占位说明
- 补充密钥轮换文档

不做：

- 不改登录方式为 HttpOnly cookie
- 不做完整 RBAC
- 不做 AgentGraph

### 交付物

- OAuth state 校验逻辑
- JWT secret 强校验
- 安全测试
- `docs/security-key-rotation.md`

### 验收

- 未校验 state 的 callback 被拒绝
- 无效 / 弱 JWT secret 启动或签发 token 时失败
- tracked 文件不包含真实 key
- 非 AI 测试通过

---

## Phase 39.1：Tool 协议骨架

### 目标

建立 Agent 工具运行时的最小协议层。先只做骨架，不接业务工具，避免一次性重构过大。

### 参考

- `reference/claude-code-analysis/analysis/04b-tool-call-implementation.md`
- `reference/claude-code-analysis/src/Tool.ts`
- `backend/app/agent/tools.py`

### 范围

做：

- `ToolDefinition`
- `ToolResult`
- `ToolError`
- `ToolContext`
- `ToolRegistry`
- `ToolExecutor`

不做：

- 不接 DeepSeek
- 不接 DB
- 不改 AgentGraph
- 不改 API

### 设计要求

工具默认 fail-closed：

- `is_read_only=False`
- `is_concurrency_safe=False`
- `is_destructive=False`
- `max_retries=0`

工具错误分类：

- `TRANSIENT`
- `RATE_LIMITED`
- `AUTH_FAILED`
- `LENGTH_EXCEEDED`
- `STRUCTURED_OUTPUT_ERROR`
- `PERMANENT`

注意：  
`ToolResult.error` 只封装预期错误。编程错误、DB 事务错误、schema 定义错误仍应抛出，由 AgentGraph 进入 `FAILED`。

### 交付物

- `backend/app/agent/tools/base.py`
- `backend/app/agent/tools/registry.py`
- `backend/app/agent/tools/executor.py`
- 单元测试覆盖注册、重复注册、缺失工具、并发分区、重试策略

### 验收

- 只读并发安全工具可并发
- 写工具串行
- 401/403 不重试
- 429 / timeout 按工具配置重试
- 工具执行结果顺序与输入顺序一致

---

## Phase 39.2：本地确定性工具接入

### 目标

先把无外部副作用的业务逻辑包成工具，让 AgentGraph 后续可以通过统一协议调用。

### 参考

- `backend/app/scoring/questionnaire.py`
- `backend/app/scoring/answer_scoring.py`
- `backend/app/scoring/engine.py`
- `backend/app/reports/splitter.py`
- `backend/app/reports/guard.py`
- `CONTEXT.md`
- `docs/questionnaire-canonical.md`

### 工具

| 工具名 | 作用 | 类型 |
|---|---|---|
| `question_catalog.read` | 返回题库、关键问题、display 映射、维度中文名 | local read |
| `readiness.check` | 判断是否足够生成报告，返回 missing_items | local read |
| `score.calculate` | answers → ScoringResult | local read |
| `report.split` | RawAIReport → UserReport + LeadReport | local read |
| `report.guard` | 用户报告安全扫描 | local read |

### 关键要求

- `readiness.check` 是确定性规则，不交给 LLM
- 信息不足返回 `ReadinessResult`，不生成 0 分报告
- `inexperienced` 分支返回明确不支持状态，不进入评分
- 维度中文名以 `docs/scoring-design.md` 为准

### 交付物

- `backend/app/agent/tools/local/`
- 每个工具独立 input/output schema
- 单元测试

### 验收

- answers 不足时返回 missing_items
- Q5 缺失时不能 ready
- Q5=D 返回 unsupported branch
- 满足条件时可生成 ScoringResult
- 用户报告安全扫描不允许 lead 字段泄露

---

## Phase 39.3：AgentEvent 与 TerminalState

### 目标

建立 AgentGraph 输入输出协议，但先不替换 API。让新图可以被测试直接调用。

### 参考

- `docs/adr/0009-agent-graph-as-orchestrator.md`
- `CONTEXT.md`
- `backend/app/schemas/agent_state.py`
- `backend/app/agent/state_machine.py`

### 范围

做：

- `AgentEvent`
- `TerminalState`
- `AgentRunResult`
- `ReadinessResult` 写入 AgentState 或独立字段
- 图内最大步数保护 `MAX_AGENT_STEPS`

不做：

- 不改 `/conversation/*`
- 不接真实 DeepSeek 工具
- 不接报告生成

### TerminalState

- `awaiting_user`
- `missing_info`
- `unsupported_branch`
- `completed`
- `completed_with_template`
- `failed`
- `aborted`
- `max_steps_exceeded`

### 验收

- `user_message` 事件可进入 awaiting_user
- `finish_requested` 信息不足返回 missing_info
- `inexperienced` 返回 unsupported_branch
- 超过图内步数返回 max_steps_exceeded
- 所有状态都有测试

---

## Phase 39.4：AgentGraph 接管 continue

### 目标

让 `/conversation/continue` 和 `/conversation/continue-stream` 通过 AgentGraph 执行，不再由 API handler 手动编排提取和追问。

### 参考

- `backend/app/api/conversation.py`
- `backend/app/agent/graph.py`
- `backend/app/agent/nodes.py`
- `backend/app/agent/prompts.py`
- `backend/app/services/deepseek_client.py`

### 工具

| 工具名 | 作用 |
|---|---|
| `dialogue.deepseek` | 基于 readiness 缺失项生成下一轮追问 |
| `extract_answers.deepseek` | 对话后提取 slots / answers / branch |

### 关键要求

- 追问必须优先覆盖报告关键问题
- Agent 不应在关键信息不足时继续给执行建议
- streaming 接口仍然输出 `delta / done / error`
- streaming 的 `done.state` 必须包含最新 extraction 结果
- 对话历史不再被裁掉；LLM 调用时只取窗口内消息

### 验收

- `/continue` API handler 不直接调用 `extract_answers_node`
- `/continue-stream` API handler 不直接决定业务路径
- 真实 DeepSeek 测试能完成一轮追问
- 对话多轮后历史不丢失
- 关键问题缺失时，回复是追问，不是投放建议

---

## Phase 39.5：AgentGraph 接管 finish

### 目标

让 `/conversation/finish` 只传 `finish_requested` 事件。图内负责 readiness、评分、RAG、报告、审计、保存。

### 参考

- `backend/app/agent/reporting.py`
- `backend/app/agent/audit.py`
- `backend/app/reports/template_report.py`
- `backend/app/services/rag_repository.py`
- `backend/app/services/assessment_repository.py`

### 工具

| 工具名 | 作用 | 失败策略 |
|---|---|---|
| `rag.search` | 检索报告参考知识 | 失败则空 RAG，不切模板 |
| `report.generate.deepseek` | 生成 RawAIReport | transient 重试；length 升级重试一次 |
| `report.audit.deepseek` | 审计报告 | transient 重试一次 |
| `assessment.complete` | 保存最终评估与报告快照 | DB 错误进入 failed |

> **持久化策略**：对话消息、slots、answers、scoring_result 由 AgentGraph 框架在每轮结束后自动持久化，**不是 Agent 的显式工具**。参考 Claude Code——框架负责记住一切，Agent 只做诊断决策。只有 `assessment.complete`（最终提交）是工具。

### 关键要求

- 信息不足返回 `missing_info`，不生成模板报告
- RAG 失败不应导致模板报告
- 报告生成技术失败可模板兜底
- 审计打回要把 audit feedback 注入下一次 report prompt
- 第三次审计仍失败才模板兜底
- 模板兜底只能用于技术失败，不用于信息不足

### 验收

- 信息不足 finish 不写 assessment，不返回 0 分模板
- 信息足够 finish 返回 report_summary
- RAG 失败时仍走 AI 报告
- `finish_reason=length` 触发一次 escalated retry
- 审计反馈进入下一次 prompt
- `assessment.complete` 后数据库字段与 scoring_result 一致

---

## Phase 39.6：API handler 退回事件入口

### 目标

清理 API 层的业务编排逻辑，使其只负责请求/响应、安全 DTO、事务提交。

### 参考

- `backend/app/api/conversation.py`
- `backend/app/schemas/conversation.py`
- `frontend/lib/api.ts`
- `frontend/hooks/useStreaming.ts`

### 范围

做：

- `/continue` 调 AgentGraph
- `/continue-stream` 调 AgentGraph streaming path
- `/finish` 调 AgentGraph
- 保持前端响应结构兼容
- 删除旧 `run_scoring_pipeline` / `run_report_pipeline` 调用路径

不做：

- 不重写前端 UI
- 不改报告历史接口
- 不改顾问后台

### 验收

- `conversation.py` 不再出现手动 `extract → score → report` 编排
- 所有 conversation API 测试通过
- 前端 typecheck/build 通过
- 真实 DeepSeek continue / finish / stream 测试通过

---

## Phase 39.7：上下文窗口与配置化

### 目标

把 Agent 运行参数从代码硬编码移到配置，同时保持业务规则不走 env。

### 配置项

- `DIALOGUE_MAX_TOKENS`
- `DIALOGUE_TEMPERATURE`
- `DIALOGUE_HISTORY_WINDOW`
- `REPORT_MAX_TOKENS`
- `REPORT_ESCALATED_MAX_TOKENS`
- `MAX_AGENT_STEPS`

### 不配置化

- 评分权重
- 标签阈值
- 题库内容
- 报告字段结构
- 安全 forbidden terms

### 验收

- `.env.example` 包含新增配置
- 默认值与当前行为一致
- 修改 history window 不影响前端历史展示
- 测试覆盖配置读取

---

## Phase 39.8：Question display mapping

### 目标

把 31 个用户可见题号和 37 个内部 Question 对象的映射显式建模，避免后续前端、提取、报告引用混乱。

### 参考

- `CONTEXT.md`
- `docs/questionnaire-canonical.md`
- `backend/app/scoring/questionnaire.py`
- `backend/tests/unit/test_questionnaire.py`

### 改动

`Question` 增加：

- `display_id`
- `display_order`
- `sub_order`

### 验收

- `ALL_QUESTIONS` 共 37 个内部题
- `display_id` 覆盖 Q1-Q31 共 31 个唯一值
- Q2a/Q2b/Q2c 的 `display_id == "Q2"`
- Q3a/Q3b/Q3c 的 `display_id == "Q3"`
- Q10a/Q10b/Q10c 的 `display_id == "Q10"`
- extraction / scoring 仍使用内部 `Question.id`

---

## Phase 39.9：死代码清理

### 目标

删除会误导后续 Agent 和开发者的历史残留代码。

### 候选项

- `trim_history_node`
- `EXPERIENCED_QUESTION_IDS`
- `admin_auth.py require_admin`
- 空壳 `backend/app/rag/`
- 旧 pipeline 函数，如果已经完全被 AgentGraph 替代

### 规则

- 删除前必须 `rg` 确认无引用
- 删除后必须跑相关测试
- 不顺手重构目录结构

### 验收

- 无未使用导入
- 无空壳模块
- 非 AI 全量测试通过

---

## Phase 40：Memory 系统

### 目标

在 AgentGraph 稳定后，再引入长期记忆。当前不作为 Phase 39 的前置条件。

### 参考

- `reference/claude-code-analysis/analysis/04-agent-memory.md`
- `reference/claude-code-analysis/analysis/04i-session-storage-resume.md`

### 方向

- 文件系统 Markdown memory
- frontmatter 索引
- LLM 从候选 memory 中选择相关项
- 不使用 embedding
- 不保存密钥、临时对话、Git 历史

### 暂缓原因

当前项目最急的问题是 Agent 执行循环和工具协议。Memory 会扩大范围，必须等 AgentGraph 稳定后再做。

---

## 3. 关键数据结构附录

> 以下结构是 Phase 39.1-39.5 的代码级规格。Phase 执行时必须参考这些定义，不得自由发挥。

### 3.1 Tool 协议层

```python
from pydantic import BaseModel
from typing import Any, Literal
from enum import StrEnum

class ToolErrorCode(StrEnum):
    TRANSIENT = "TRANSIENT"                  # 网络/超时 → 可重试
    RATE_LIMITED = "RATE_LIMITED"            # 429 → 指数退避重试
    AUTH_FAILED = "AUTH_FAILED"              # 401/403 → 不重试
    LENGTH_EXCEEDED = "LENGTH_EXCEEDED"       # finish_reason=length → 升级 max_tokens 重试一次
    STRUCTURED_OUTPUT_ERROR = "STRUCTURED_OUTPUT_ERROR"  # JSON 解析失败 → 注入 validation error 重试一次
    PERMANENT = "PERMANENT"                  # 参数/Schema 错误 → 不重试

class ToolError(BaseModel):
    """只封装预期错误。编程错误、DB 事务错误仍应抛出，由 AgentGraph 进入 FAILED。"""
    code: ToolErrorCode
    message: str
    retryable: bool

class ToolResult(BaseModel):
    """参考 Claude Code 的 ToolResult<T> —— 不抛异常，预期错误封装在 error 字段"""
    data: Any | None = None
    error: ToolError | None = None

class ToolDefinition(BaseModel):
    """参考 Claude Code 的 buildTool() 工厂 —— 默认 fail-closed"""
    name: str
    description: str
    is_read_only: bool = False           # 默认 fail-closed
    is_concurrency_safe: bool = False    # 默认串行
    is_destructive: bool = False         # 默认不标记
    max_retries: int = 0
    retry_delay_seconds: float = 0.5
    timeout_seconds: float = 60.0

class ToolContext(BaseModel):
    """参考 Claude Code 的 ToolUseContext —— 每个工具调用时注入的运行时总线"""
    assessment_id: str | None = None
    user_id: str | None = None
    db_session: Any | None = None       # AsyncSession，由 executor 注入
    abort_signal: Any | None = None     # asyncio.Event，用于取消

class ToolRegistry:
    """工具注册表。注册 11 个工具，重复注册抛异常，缺失工具返回明确错误。"""
    def register(self, tool: ToolDefinition) -> None: ...
    def get(self, name: str) -> ToolDefinition: ...
    def list_all(self) -> list[ToolDefinition]: ...
    def list_read_only(self) -> list[ToolDefinition]: ...
```

### 3.2 Agent 协议层

```python
class AgentEvent(BaseModel):
    """API 传入的用户事件。API 层只传事件，不编排业务。"""
    type: Literal["user_message", "finish_requested"]
    message: str | None = None

class TerminalState(StrEnum):
    AWAITING_USER = "awaiting_user"                 # 已生成追问，等待用户回复
    MISSING_INFO = "missing_info"                   # 用户点 finish 但 readiness 不通过
    UNSUPPORTED_BRANCH = "unsupported_branch"       # Q5=D，题库未开放
    COMPLETED = "completed"                         # 评分+报告+审计全部成功
    COMPLETED_WITH_TEMPLATE = "completed_with_template"  # 技术故障 → 模板兜底
    FAILED = "failed"                               # 不可恢复错误
    ABORTED = "aborted"                             # 用户断开 stream
    MAX_STEPS_EXCEEDED = "max_steps_exceeded"       # 图内步数超安全上限（技术熔断）

class AgentRunResult(BaseModel):
    """单次 AgentGraph 执行的返回"""
    state: "AgentState"
    terminal: TerminalState
    response: dict | None = None   # 返回给前端的 DTO
```

### 3.3 业务协议层

```python
class MissingItem(BaseModel):
    question_id: str       # scoring_question_id，如 "Q5"
    label: str             # 用户可见标签，如 "海外订单占比"
    reason: str            # 为什么需要这个信息

class ReadinessResult(BaseModel):
    """readiness_check_node 的输出 —— 确定性节点，不交给 LLM"""
    ready: bool
    missing_items: list[MissingItem] = []
    next_questions: list[str] = []  # LLM 可参与改写追问文案，但不能决定缺什么
```

### 3.4 重试策略速查

| 工具 | 错误类型 | 行为 |
|------|------|------|
| `dialogue.deepseek` | TRANSIENT | 最多 2 次，指数退避 0.5s/1.5s + jitter |
| `extract_answers.deepseek` | TRANSIENT | 最多 1 次；失败后标记 extraction_failed，仍可返回追问 |
| `report.generate.deepseek` | TRANSIENT | 最多 2 次 |
| `report.generate.deepseek` | LENGTH_EXCEEDED | 升级 max_tokens 到 `REPORT_ESCALATED_MAX_TOKENS`，重试 1 次 |
| `report.generate.deepseek` | STRUCTURED_OUTPUT_ERROR | 重试 1 次，validation error 注入 prompt |
| `report.audit.deepseek` | TRANSIENT | 最多 1 次 |
| `rag.search` | TRANSIENT | 最多 1 次；失败返回空 RAG context，不切模板 |
| 所有工具 | AUTH_FAILED | 不重试 |
| 所有工具 | PERMANENT | 不重试 |

### 3.5 持久化策略

> 参考 Claude Code：持久化是框架的自动行为，不是 Agent 的显式工具。Agent 只做诊断决策，框架负责记住一切。

| 什么 | 谁存 | 何时 | 工具？ |
|------|------|------|:--:|
| 对话消息 | AgentGraph 框架 | 每轮结束后自动 | ❌ 自动 |
| slots / answers | AgentGraph 框架 | extraction 后自动写入 `Assessment` JSONB | ❌ 自动 |
| scoring_result | AgentGraph 框架 | score 后自动写入 `Assessment` JSONB | ❌ 自动 |
| 最终 report + scores 快照 | `assessment.complete` | Agent 判定 READY + finish 请求时 | ✅ 工具 |
| Memory | `memory.save` | Phase 40，框架或 Agent 均可触发 | ✅ 工具（Phase 40） |
| ConversationClientState | API 层 | 每次响应返回给前端 | ❌ 自动 |

---

## 4. Vibecoding 使用方式

**测试策略**：Phase 内同步改测试，全量始终保持绿色。旧 API 行为未切换前旧测试继续保留。新 AgentGraph 能力先加新测试覆盖。删除旧函数前 `rg` 确认无引用。

每次只执行一个 phase。每个 phase 的提示词必须包含：

- 先阅读本计划书
- 只做当前 phase
- 不做下一 phase
- 不引入新依赖
- 不写过度兜底代码
- 真实 AI 路径必须使用真实 DeepSeek
- 完成后输出修改文件、测试结果、未完成项

禁止一次性执行：

- “完成 Phase 39 全部”
- “顺便把 Memory 也做了”
- “顺便重写前端”
- “顺便优化 UI”

---

## 4. 最终验收口径

重构完成后，项目必须满足：

- API handler 只传 `AgentEvent`
- AgentGraph 拥有业务流转
- 工具协议声明只读、并发、重试、失败语义
- 信息不足不生成 0 分模板
- RAG 失败不切模板
- 报告 length 截断只做一次升级重试
- 审计打回带 feedback 重试，最多三次
- 写工具串行，只读并发安全工具可并行
- 用户可见报告不泄露 lead 字段
- 真实 DeepSeek 集成测试覆盖 continue / stream / finish
- 非 AI 全量测试通过
- 前端 typecheck/build 通过

---

## 5. Phase 42-50：Agent 产品工作台

> Phase 38-41.5 已完成 Agent 引擎重构。以下 Phase 将项目从"可运行的诊断 Agent"升级为"可配置、可观察、可运营的 Agent 产品工作台"。
> 参考 SonettoHere 的产品化思路：Provider 管理、AppShell、Runtime Trace、会话管理。

---

### Phase 42：模型 Provider 配置中心

参考：SonettoHere `api/providers/`、`web/src/views/ProvidersView.vue`

**目标**：用户可在前端配置 OpenAI-compatible API，不再写死 DeepSeek。

**裁决**：
- Provider 配置存 PostgreSQL，不用 YAML。
- API Key MVP 阶段服务端存 DB 明文；后端永不返回明文，前端只显示 `masked_key`。
- 不在本 Phase 引入加密依赖；如需密钥加密，单独 Phase 处理。
- 日志、响应、测试断言禁止打印 API Key 原文。

做：
- 后端新增 Provider 管理 API（CRUD + 测试连接 + 拉取模型列表）
- Provider 模型：name / base_url / api_key / default_model / enabled / context_window
- API Key 返回前端时 mask
- `DeepSeekClient` 抽象为 `OpenAICompatibleClient`，动态读取当前启用 Provider
- 前端 `/settings/models`：Provider 列表、新增、测试连接、设置默认、启用/停用

不做：
- 不删 DeepSeek 兼容性
- 不做 OAuth Provider（只做 API Key）

验收：
- 用户无需改 `.env` 即可配置模型
- 对话/抽取/报告/审计均走当前启用 Provider

---

### Phase 43：Agent 运行时模型选择

**目标**：诊断开始前可选择模型，诊断会话记录使用模型。

**裁决**：
- 一次诊断创建后锁定 `provider_id` / `model_name`。
- `continue-stream` 与 `finish` 必须使用该诊断锁定的模型。
- 用户切换模型只影响下一次新诊断。

做：
- `AgentEvent` 或 request state 增加 `provider_id` / `model_name`
- `/conversation/start` 返回当前默认模型信息
- `/continue-stream` 使用用户当前选择的模型
- `/finish` 使用同一模型
- 前端聊天页顶部模型选择器 + 无模型时引导配置
- 报告历史记录生成模型

不做：
- 不支持同一诊断中途切换模型

验收：
- 同一次诊断全程使用同一 provider/model
- Provider 不可用时 UI 明确提示

---

### Phase 44：AppShell + 设置中心

**目标**：把单页 Demo 升级为产品工作台。

做：
- 左侧导航：诊断 / 我的报告 / 顾问后台 / 模型设置 / 知识库 / Memory
- 顶部状态：登录状态、当前模型、Agent 状态
- 现有 inline style → 统一 CSS token
- `/chat`、`/reports`、`/admin/leads` 视觉统一

不做：
- 不重做已有页面业务逻辑

验收：
- 产品有统一 Shell
- 模型设置入口清晰

---

### Phase 45：诊断工作台

**目标**：对话过程透明化，用户知道"为什么还不能生成报告"。

做：
- 对话页右侧诊断进度面板：
  - 企业画像（slots）
  - 已识别答案数 + `score_ready` / `report_ready` 状态
  - `missing_items` / `report_missing_items` 实时展示
  - 下一步建议问题
- 移除"轮次"作为核心状态指标
- `missing_items` 在对话过程中持续展示，不只在 finish 失败后

验收：
- 用户看到采集进度
- Agent 不再像闲聊机器人

---

### Phase 46：Agent Runtime Trace

参考：SonettoHere `ToolCallCard.vue`、`WebSocketCallback`、`ThinkingBlock.vue`

**目标**：可观察 Agent 执行过程。

做：
- SSE 增加 runtime event：`extract_start/done`、`readiness_done`、`rag_search_done`、`report_generate_start/done`、`audit_done`
- 前端折叠式 Agent Trace 面板：企业画像更新 / 题库答案抽取 / RAG 检索 / 报告生成 / 审计
- 普通用户折叠，开发/顾问可展开
- Trace 记录每一步耗时

Trace event 最小结构：

```ts
type AgentTraceEvent = {
  type: "trace";
  step: "extract" | "readiness" | "rag_search" | "report_generate" | "report_audit";
  status: "started" | "completed" | "failed";
  elapsed_ms?: number;
  summary?: string;
};
```

Trace 禁止包含 prompt、raw_report、lead_report、原始异常和 API Key。

验收：
- 出问题能看到卡在哪一步
- 简历中"Agent 工程化"有可视化支撑

---

### Phase 47：知识库管理与 RAG 可视化

**目标**：RAG 从黑盒变成可管理、可解释的功能。

做：
- `/knowledge` 页面：查看/新增/编辑/删除知识、重新生成 embedding、测试检索
- 报告详情显示使用了哪些知识片段（TopK 标题 + score）
- 顾问后台可查看 RAG 命中依据

权限：
- `/knowledge` 仅 consultant/admin JWT 可访问。
- 企业主只能在报告中看到安全的知识标题和来源，不可编辑知识库。

验收：
- RAG 不再是后端代码
- 报告可解释"引用了什么知识"

---

### Phase 48：报告页与顾问后台产品化

**目标**：报告不再像文本 dump。

做：
- 用户报告页：分数 Hero、维度中文名、风险/优势卡片、30 天行动计划 checklist、解锁 CTA
- 顾问后台：P0/P1/P2 列表、跟进状态、顾问话术一键复制、企业画像摘要

验收：
- "顾问跟单准备时间压缩"有产品支撑

---

### Phase 49：会话管理

参考：SonettoHere session sidebar

**目标**：刷新不丢对话。

做：
- 保存未完成诊断草稿
- 恢复上次诊断
- 新建/删除草稿
- 已完成诊断进入报告历史

存储裁决：
- Phase 49 先做浏览器 `localStorage` 草稿恢复。
- 草稿仅保存 `ConversationClientState`、messages、selected provider/model、last_active_at。
- 已完成报告仍以 DB report history 为准。
- 不新增服务端 draft session 表。

验收：
- 浏览器刷新后状态恢复
- 多诊断可管理

---

### Phase 50：前端测试与发布质量

**目标**：补齐前端测试覆盖率。

做：
- Provider 配置测试
- 模型选择测试
- SSE runtime event 测试
- 报告解锁测试
- 顾问后台筛选/保存测试
- build/typecheck 固化到 CI

每个 Phase 完成后输出：
1. 修改文件
2. 新增 API / 类型结构
3. 前端页面变化
4. 安全边界
5. 测试结果
6. 明确未做

---

## 6. 当前建议执行顺序

**已完成（Phase 38-41.5）**：
1. ~~Phase 38：安全上线底线~~ ✅
2. ~~Phase 39.1-39.9：Tool Runtime + Agent 协议 + 接管 + 配置化 + Display + 死代码~~ ✅
3. ~~Phase 40：Memory 系统~~ ✅
4. ~~Phase 41-41.5：Memory recall 接入 + 流式修复 + 可观测性 + 对话-报告断裂修复 + 过早收尾修复~~ ✅

**下一阶段（Phase 42-50）**：
1. Phase 42：模型 Provider 配置中心
2. Phase 43：Agent 运行时模型选择
3. Phase 44：AppShell + 设置中心
4. Phase 45：诊断工作台
5. Phase 46：Agent Runtime Trace
6. Phase 47：知识库管理与 RAG 可视化
7. Phase 48：报告页与顾问后台产品化
8. Phase 49：会话管理
9. Phase 50：前端测试与发布质量

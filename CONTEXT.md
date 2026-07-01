# 出海诊断 Agent — 领域术语表

> 本文件是项目领域的权威词汇表。所有代码、文档、测试、报告中的概念必须使用此处定义的术语。
> 不在此表中的术语应被视为未定义——要么对齐现有术语，要么在此处正式定义。

---

## 题库

| 术语 | 英文 key | 定义 |
|------|---------|------|
| **用户题号** | `display_id` | 用户可见的题号，如 `Q1`、`Q2`、`Q10`。共 31 个唯一值。 |
| **计分单元 ID** | `scoring_question_id` / `Question.id` | 内部计分的最小单元。如 `Q2a`、`Q2b`、`Q2c`。共 37 个 Question 对象；用户可见题号为 Q1-Q31（31 个 display_id）。Q2/Q3/Q10 被拆为多个内部计分单元。 |
| **展示顺序** | `display_order` | 用户看到"第几题"，1..31。 |
| **子题顺序** | `sub_order` | 同一用户题号下的子题排位（如 Q2a=1, Q2b=2, Q2c=3）。 |
| **维度** | `dimension` | 7 个评估维度：enterprise_base / overseas_validation / product_supply_chain / path_clarity / content_fitness / conversion_readiness / action_readiness。 |
| **分支** | `branch` | 分流决定：`experienced`（有出海经验）、`inexperienced`（无出海经验，题库待提供）。Q5 的选项决定分支。 |
| **题库权威源** | — | 4 级优先级，见 `docs/questionnaire-canonical.md`。代码真源头为 `backend/app/scoring/questionnaire.py`。 |

## 评分

| 术语 | 英文 key | 定义 |
|------|---------|------|
| **可行性分** | `feasibility_score` (F) | 展示给用户的企业出海可行性评分。7 维原始分按维度归一化后求和，理论区间 0-100。 |
| **线索分** | `lead_score` (L) | 内部顾问跟进优先级评分。不得出现在用户可见报告中。7 维原始分按维度归一化后求和，理论区间 0-100。 |
| **维度权重** | `header_weight` | `rules.py` 中定义的每个维度的产品口径满分。F 总和 100，L 总和 100。 |
| **逐题原始分** | `raw_score` | 用户选项在某一题上的 F/L 原始得分。多选有封顶。 |
| **维度原始分** | `raw_dimension_score` | 一个维度内所有计分单元的原始分之和。 |
| **归一化维度分** | `normalized_dimension_score` | `raw / raw_max × header_weight`，四舍五入为整数。`answer_scoring.py` 负责此计算。 |
| **标签** | `tag` | 可行性总分落区：观察准备型(0-25) / 轻量试探型(26-45) / 基础具备型(46-65) / 优先布局型(66-100)。 |
| **线索优先级** | `lead_priority` | 顾问跟进攻略：P0-立即跟进(61-100) / P1-重点跟进(41-60) / P2-培育跟进(21-40) / P3-低频触达(0-20)。 |

### 七维度定义

中文展示名以 `docs/scoring-design.md` 为权威源。英文 key 仅用于代码和 JSON 内部。LLM 报告、前端雷达图、顾问后台都只展示中文名。

| key | display_name_zh | F 权重 | L 权重 |
|-----|:--------------:|:------:|:------:|
| `enterprise_base` | 企业基本盘 | 20 | 20 |
| `overseas_validation` | 海外验证度 | 20 | 15 |
| `product_supply_chain` | 产品与供应链竞争力 | 15 | 12 |
| `path_clarity` | 出海路径清晰度 | 10 | 8 |
| `content_fitness` | 短视频获客适配度 | 20 | 15 |
| `conversion_readiness` | 销转承接能力 | 10 | 15 |
| `action_readiness` | 企业出海行动力 | 5 | 15 |

## 核心领域对象

| 术语 | 英文 key | 定义 |
|------|---------|------|
| **评估** | `Assessment` | 一次完整的出海诊断会话。包含对话历史、槽位、答案、评分结果、报告。对应 ORM 模型 `Assessment`。`scoring_result`（JSONB）是评分的业务真源头；`feasibility_score`/`lead_score`/`tag`/`lead_priority` 列为查询优化的派生快照，禁止独立修改。 |
| **用户报告** | `UserReport` | 用户可见的诊断报告。**禁止**包含 `lead_score`、`lead_priority`、`sales_followup`、`consultant_notes`。 |
| **顾问报告** | `LeadReport` | 内部销售使用的报告。包含线索分、销售话术、顾问备注。 |
| **留资** | `LeadSubmission` | 用户填写联系方式以解锁完整报告的行为。包含姓名、手机号、微信、公司名。 |
| **槽位** | `Slot` | 从对话中提取的结构化企业信息（行业、产品、营收等）。13 个字段定义见 `schemas/slots.py`。 |
| **答案** | `Answer` | 用户对某一计分单元的选项选择，存储为 `{question_id: [option_ids]}`。 |
| **题单** | `Question` | 一道计分单元。`Question.id` 是内部标识，`display_id` 是用户看到的题号。 |

### AgentState 边界

`AgentState`（`schemas/agent_state.py`）当前是 LangGraph 图内流转的便利容器，**不是**单一领域对象。最终应拆为三个独立概念（当前仅收紧边界，不重构）：

| 概念 | 英文 key | 定义 | 持久化？ | 传给前端？ |
|------|---------|------|:---:|:---:|
| **诊断态** | `DiagnosticState` | 诊断的业务真状态：branch / slots / answers / scoring_result / report / audit_result。 | ✅ | 部分（slots/answers 在 client_state 里） |
| **会话** | `ConversationSession` | 对话的会话状态：messages / conversation_round / status / user_id。 | ✅ 未来 | ✅ |
| **运行时上下文** | `AgentExecutionContext` | 图内执行的技术状态：ai_failure_count / validation_errors / extraction_attempt_count。 | ❌ | ❌ 禁止 |
| **客户端状态** | `ConversationClientState` | API DTO。只能含 messages / slots / answers / branch / status / public_error。禁止回灌技术字段到内部状态。 | ❌ | ✅ |

### 对话终止规则

> ⚠️ 2026-06-27 产品决策变更：**对话轮次不再有上限**。PRD 和 CLAUDE.md 中"8 轮硬熔断"已过期。

| 规则 | 优先级 | 说明 |
|------|:------:|------|
| 用户手动 finish | 最高 | 用户点击"生成报告"，系统检查信息门槛。足够→评分报告；不足→返回缺失项提示，不生成 0 分模板。 |
| 信息完整度提示 | 建议 | 当 `answers ≥ 8` 且关键字段（Q5/branch/行业/产品）已就绪，前端提示"可以生成报告"，但不强制终止。 |
| AI 失败降级 | 技术兜底 | `ai_failure_count ≥ 2` 时进入 `fallback_questionnaire`。这是技术故障路径，不是正常业务终止。 |
| 轮数上限 | **已废弃** | `max_rounds` 不再参与任何终止逻辑。`should_stop_conversation()` 保持返回 `False`，后续应移除或改名。 |

## 用户角色

| 术语 | 定义 |
|------|------|
| **企业主** | 产品终端用户。通过微信扫码登录，完成诊断对话，查看报告，留资。 |
| **顾问** | 出海咨询公司的销售/咨询师。查看线索列表、顾问报告、更新跟进状态。 |
| **管理员** | 咨询公司内部管理。MVP 不做。 |

---

### Agent 架构

> ✅ 2026-07-01 ADR-0009 已完全落地。API handler 只传 AgentEvent，AgentGraph 拥有业务流转。

| 术语 | 定义 |
|------|------|
| **AgentEvent** | API 传入的用户事件：`user_message` 或 `finish_requested`。API 层只传递事件，不决定下一步。 |
| **AgentGraph** | 单一 LangGraph 图，接收 AgentEvent → 提取 → 判断 readiness → 追问或评分 → 报告 → 审计。图中节点负责完整流转。 |
| **Readiness Check** | Agent 图内判断信息是否足够生成报告。最低条件：branch=experienced、Q5 有效、Q1 已提取、无阻塞错误。不满足 → 继续追问；满足 + finish_requested → 评分报告。 |
| **模板兜底** | 仅用于 AI/服务故障（DeepSeek 失败、RAG 失败、审计多次失败）。**禁止**用于"信息不足"场景。信息不足是正常 Agent 状态，应返回缺失问题列表。 |

### 当前迭代状态

> 2026-07-01 全部 Phase 完成并合并到 main。

| 优先级 | 事项 | 状态 |
|:---:|------|:---:|
| P0 | API Key 轮换、JWT secret 校验、微信 OAuth state CSRF 修复 | ✅ Phase 38 |
| P1 | 硬编码抽配置 | ✅ Phase 39.7 |
| P1 | Question.display_id 映射 | ✅ Phase 39.8 |
| P2 | 死代码清理 | ✅ Phase 39.9 |
| P2 | 无出海经验占位 | ✅ unsupported_branch 终态 |
| P3 | AgentGraph 架构重构（ADR-0009） | ✅ Phase 39.3-39.6 |
| P3 | Memory 系统 | ✅ Phase 40-41 |

后续迭代：
- memory.save 自动保存时机
- AgentState 拆分（DiagnosticState / ConversationSession / AgentExecutionContext）
- Memory 新鲜度与 LLM 语义选择升级

### Agent 工具系统

> 参考：Claude Code 源码 `src/tools/Tool.ts`。原则：工具不是普通函数，而是带 `is_read_only / is_concurrency_safe / is_destructive / max_retries` 元数据的运行时协议对象。默认 fail-closed。

| 术语 | 定义 |
|------|------|
| **ToolDefinition** | 工具定义基类。包含 `name` / `description` / `is_read_only` / `is_concurrency_safe` / `is_destructive` / `max_retries` / `retry_delay_seconds`。参考 Claude Code 的 `buildTool()` 工厂。 |
| **ToolResult** | 工具执行结果。不抛异常——所有错误封装在 `error: ToolError` 字段中。包含 `data` / `error` / `new_messages` / `context_modifier`。 |
| **ToolError** | 工具错误。`code` 区分 `TRANSIENT` / `PERMANENT` / `LENGTH_EXCEEDED` / `RATE_LIMITED` / `AUTH_FAILED`。`retryable` 决定执行器是否重试。 |
| **ToolContext** | 工具运行时上下文。包含 `db_session` / `user_id` / `assessment_id` / `abort_signal`。由 ToolExecutor 在调用前注入。 |
| **ToolRegistry** | 工具注册表。统一管理工具的注册、发现、重试策略查询。 |
| **ToolExecutor** | 工具执行器。按 `is_concurrency_safe` 分区——并发安全的工具 `asyncio.gather()`；不安全的串行执行。每个工具按自身 `max_retries` 重试。 |
| **AgentEvent** | API 传入的用户事件：`user_message` 或 `finish_requested`。API 层只传事件，不编排业务。 |
| **TerminalState** | Agent 图的 8 个终止状态：`awaiting_user` / `missing_info` / `unsupported_branch` / `completed` / `completed_with_template` / `failed` / `aborted` / `max_steps_exceeded`。 |
| **ReadinessResult** | 确定性节点 `readiness_check_node` 的输出。`ready` / `missing_items` / `next_questions`。LLM 可参与改写追问文案，但不能决定缺失项是什么。 |

### Agent 记忆系统

> 参考：Claude Code `src/memdir/`。文件系统 + frontmatter + LLM 语义选择，不用向量数据库。

| 术语 | 定义 |
|------|------|
| **记忆文件** | 一个 Markdown 文件，包含 YAML frontmatter（`name` / `description` / `type`）和正文。存储在 `.claude/memory/` 目录下。 |
| **记忆类型** | 四种：`user`（用户偏好）、`feedback`（工作方式指导）、`project`（项目状态/目标）、`reference`（外部系统链接）。 |
| **MEMORY.md** | 记忆索引文件，每行一个 `- [Title](file.md) — one-line hook`。上限 200 行 / 25KB。 |
| **记忆召回** | `memory.recall` 工具：关键词 substring 匹配 name/description/content → 返回前 3 条匹配。runner user_message 路径自动调用，结果注入 dialogue prompt。不使用向量检索。 |
| **记忆保存** | `memory.save` 工具：两步原子写入——先写主题文件 → 再更新 MEMORY.md 索引。已有文件更新而非重复创建。当前手动调用，自动保存时机待后续迭代。 |
| **记忆新鲜度** | 暂未实现。后续迭代可增加时间戳检查。 |

---

*最后更新：2026-07-01。Phase 38-41 全部完成。此文件由 /domain-modeling 维护。*

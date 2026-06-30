# 出海诊断 Agent — 领域术语表

> 本文件是项目领域的权威词汇表。所有代码、文档、测试、报告中的概念必须使用此处定义的术语。
> 不在此表中的术语应被视为未定义——要么对齐现有术语，要么在此处正式定义。

---

## 题库

| 术语 | 英文 key | 定义 |
|------|---------|------|
| **用户题号** | `display_id` | 用户可见的题号，如 `Q1`、`Q2`、`Q10`。共 31 个唯一值。 |
| **计分单元 ID** | `scoring_question_id` / `Question.id` | 内部计分的最小单元。如 `Q2a`、`Q2b`、`Q2c`。共 33 个（Q2/Q3/Q10 各拆为多个子题）。 |
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
| **槽位** | `Slot` | 从对话中提取的结构化企业信息（行业、产品、营收等）。12 个字段定义见 `slots.py`。 |
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

*最后更新：2026-06-30。此文件由 /domain-modeling 维护。*

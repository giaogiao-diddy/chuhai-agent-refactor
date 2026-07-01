# ADR-0009：Agent 图作为流程决策中心，API 层只传事件

> 日期：2026-06-27 | 状态：已采纳 | 取代：CLAUDE.md §6 Agent 规范（部分） | 前提：ADR-0006、ADR-0008

---

## 背景

当前代码中，API handler 直接编排业务逻辑：

```
POST /conversation/continue  →  手动调 dialogue + extract
POST /conversation/finish    →  手动调 score + report
```

这导致三个问题：

1. **API 层知情太多**：API 需要知道提取节点存在、评分管道如何调用、报告何时生成。违反 CLAUDE.md 的"API 层只做校验+响应"规则。
2. **图内无决策**：三个独立 LangGraph 图（dialogue / score / report）各自为政，没有单一图的判断能力。提取节点甚至未注册到任何图。
3. **"信息不足 → 模板报告"路径错误**：当前 `/finish` 在信息不足时仍生成评分和报告，可能产出 0 分模板。但模板兜底的设计意图是"AI 技术故障"，不是"用户还没聊完"。

---

## 决策

**Agent 图（AgentGraph）是流程决策中心。API 层只传递用户事件，不决定 extract/score/report 顺序。**

### 核心模型

```
API 层                         Agent 图
─────                         ────────
AgentEvent                    receive_event
  │                             → append_message
  │ user_message  ──────────→   → extract_answers
  │ finish_requested ──────→    → check_readiness
  │                               ├─ not_ready → ask_next_question
  │                               └─ ready
  │                                   ├─ user_message → dialogue
  │                                   └─ finish_requested → score
  │                                                           → report
  │                                                           → audit
  │                                                           → completed
```

### API 层简化为两个端点

**`POST /conversation/continue`**

```python
request → AgentEvent(type="user_message", message=body.message)
         → graph.ainvoke(event)
         → response（含 next_questions 或 report_summary）
```

**`POST /conversation/finish`**

```python
request → AgentEvent(type="finish_requested")
         → graph.ainvoke(event)
         → response
         → 若信息不足：status="collecting", next_questions=[...]
         → 若信息足够：正常评分报告
```

### readiness_check 最低条件

Agent 图内的 `check_readiness` 节点判断：
- `branch == "experienced"`
- `Q5` 答案有效
- `Q1` 行业/产品已提取（slots.industry + slots.main_product 非空）
- `answers` 数量 ≥ 8（覆盖至少 8 道计分单元）
- 无 Q5/分支类阻塞 validation_error

满足 → 可以评分。不满足 → 返回 `next_questions`，状态保持 `collecting`。

### 模板兜底使用边界

```
✅ 模板兜底应触发：
  - DeepSeek 报告生成连续失败
  - RAG 检索异常
  - 审计多次失败（2 次上限）
  - 其他外部服务故障

❌ 模板兜底不应触发：
  - 用户信息不足（这是正常 Agent 状态）
  - 用户选了 inexperienced 分支（应有专用占位模板，不是 0 分模板）
```

---

## 替代方案

**方案 B：保持现状（API 编排 + 3 独立图）**
- 优点：不需要重构，当前代码能跑
- 否决原因：架构债务会持续累积；每次加功能都在 API 层写更多编排代码；前端/后端/mobile 多客户端时每个都要重新实现编排逻辑

**方案 C：用 LangGraph 的 subgraph 模式（父图包含三个子图）**
- 优点：保留现有 3 个图的结构
- 否决原因：仍需要父图做决策；子图间仍需要状态传递协议；相当于方案 A 但多一层嵌套

---

## 后果

**正面**：
- API 层真正做到"thin"——只校验 + 传事件 + 返回响应
- Agent 具备完整的对话管理能力（继续追问、生成报告、错误降级全在图中）
- 模板兜底触发条件收窄为纯技术故障，不会给正常用户展示 0 分报告
- 多客户端复用同一套 AgentGraph

**负面**：
- 需要重构 `conversation.py`、`graph.py`、`nodes.py`（中等工作量）
- readiness_check 逻辑需要在 DeepSeek 提取之外增加确定性检查
- 现有测试需要更新以匹配新的 API 响应格式

**需要的后续变更**（另立 Phase）：
1. 重写 `agent/graph.py`：单一 AgentGraph，含 receive_event → extract → check_readiness → dialogue/score → report → audit
2. 简化 `app/api/conversation.py`：移除手动编排，只传 AgentEvent
3. 实现 `check_readiness` 节点：确定性条件检查
4. 区分 `status: "collecting"` vs `"completed"` 的客户端响应
5. 前端适配新的响应格式（next_questions / report_summary）

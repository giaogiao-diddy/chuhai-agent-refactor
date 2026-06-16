# V2.0 变更说明书 — 18 题·AI 逐题诊断·强成交人设融合

> 给后端 Claude Code 会话 | 分支：feat/lin-backend | 日期：2026-06-17

---

## 变更摘要

| 维度 | V1.0 | V2.0 |
|------|------|------|
| 题目 | 15 题，全部选择题 | **18 题**，第 1 题手动输入行业（不计分） |
| 计分 | 15 题，原始分 15-60，展示分 +45 | **17 题**，原始分 17-68，展示分 +43 |
| 标签阈值 | 15/26/36/46 | **17/31/44/57** |
| AI 策略 | 一次性生成报告 | **逐题诊断 → 最终合成（两阶段）** |
| 报告结构 | 传统结构化 | **融合：强成交人设三段 + 结构化评分** |
| 第 1 题用途 | 参与计分 | **行业输入 → 分销路由（不同行业不同企微二维码）** |
| 数据表 | ai_report_logs 纯日志 | **ai_report_logs 增加 diagnosis_tag/report_memory/sales_hint** |

---

## 必须修改的代码文件

### 1. `app/models/question.py`
- `Question` 模型增加 `is_scored: bool = True`
- 第 1 题（行业手动输入）`is_scored = False`，不生成 option 表

### 2. `app/models/ai_report_log.py`
- 增加 3 个字段：`report_memory (Text)`, `diagnosis_tag (JSON)`, `sales_hint (Text)`
- 增加 `question_id (Integer)` — 逐题诊断时标识是哪道题，最终合成为 NULL

### 3. `app/services/scoring_service.py`
- `calculate_total`：过滤 `score > 0` 的答案求和（第 1 题 score=0 自然不计入）
- `score_to_tag` 新阈值：

```python
if raw_score <= 30:     # 观察准备型
elif raw_score <= 43:   # 轻量试探型
elif raw_score <= 56:   # 基础具备型
else:                   # 优先布局型
```

- `calculate_score_and_tag`：`display_score = raw + 43`

### 4. `app/services/prompts.py`
- 新增两个 Prompt 常量：
  - `SYSTEM_DIAGNOSE_SINGLE_QUESTION` — 逐题诊断 Prompt
  - `SYSTEM_GENERATE_FULL_REPORT` — 最终合成 Prompt（输入包含 18 条 report_memory）
- 两套 Prompt 必须体现「强成交人设」方法论表述

### 5. `app/services/report_service.py`
- 新增 `diagnose_single_question()` — 逐题异步调用 AI，写入 ai_report_logs
- 重构 `generate_full_report()` — 收集全部 report_memory 作为最终合成输入
- 最终报告 JSON 结构改为融合版（定位/内容/转化 + 结构化评分）

### 6. `app/services/template_report.py`
- 模板内容用「强成交人设」方法论改写
- `build_summary` 输出包含 `positioning_assessment`/`content_assessment`/`conversion_assessment`
- `build_full` 输出包含三段式深度分析

### 7. `app/api/assessments.py`
- `POST /answers` 端点：保存答案后，触发后台 `diagnose_single_question()`
- `POST /complete` 端点：收集诊断记忆 → `generate_full_report()`

### 8. `app/schemas/assessment.py`
- `AnswerSubmit` 兼容第 1 题手动输入（增加 `answer_text: str | None` 字段）
- 或新增 `IndustrySubmit` Schema 专门处理第 1 题

### 9. `backend/tests/fixtures/sample_questions.json`
- ✅ 已由文档会话更新为 18 题完整配置（含 `is_scored` 字段）

### 10. `backend/tests/conftest.py`
- ✅ fixture 已更新为 17 题计分（Q2-Q18）
- 需新增第 1 题行业输入的 fixture

### 11. `backend/tests/unit/test_scoring.py`
- ✅ 阈值已更新为 17/31/44/57

### 12. `backend/tests/unit/test_template_report.py`
- 需更新字段名匹配新结构（`positioning_assessment` 等）

---

## 文档已更新（后端不必改）

| 文件 | 状态 |
|------|:--:|
| `PRD.md` | ✅ V2.0 |
| `TECH_DESIGN.md` | ✅ §4.3、§4.4、§3、§9.4、§11 全部更新 |
| `CODE_REVIEW.md` | 待后端更新后重新生成 |
| `M7_PROMPT.md` | 需基于 V2.0 重写 |

---

## 标签映射新表

| 原始分 | 展示分 | 标签 |
|--------|--------|------|
| 17-30 | 60-73 | 观察准备型 |
| 31-43 | 74-86 | 轻量试探型 |
| 44-56 | 87-99 | 基础具备型 |
| 57-68 | 100-111 | 优先布局型 |

---

## AI 逐题诊断 Prompt 参考（文档会话产出）

每道题答完后，后端静默调用：

```text
你是一名强成交人设出海诊断顾问。

用户正在完成一份出海能力测评。你不会直接向用户展示本次分析结果，而是为最终完整报告生成一条内部诊断记忆。

请根据当前题目、用户答案、选项业务含义、历史已答题摘要，判断这道题透露出的业务信息。

要求：
1. 只生成内部诊断，不要写给用户看的即时建议。
2. diagnosis_tag 反映这道题暴露的能力状态/风险点/机会点。
3. report_memory 用于最终完整报告合成，应明确这道题贡献的洞察。
4. sales_hint 用于后续顾问跟进，应给出具体追问方向。

{
  "diagnosis_tag": [],
  "report_memory": "",
  "sales_hint": ""
}
```

---

## 实施顺序

```
1. models: Question 加 is_scored，AIReportLog 加 3 字段
2. schemas: AnswerSubmit 兼容手动输入
3. scoring_service: 新阈值 + calculate_score_and_tag
4. prompts: 两套新 Prompt
5. report_service: diagnose_single_question + 重构 generate_full_report
6. template_report: 融合版输出结构
7. API: POST answers 触发诊断 + POST complete 触发合成
8. 测试: 更新 test_template_report 字段名 + 运行全量测试
```

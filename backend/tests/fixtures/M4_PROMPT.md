# M4 最小垂直切片 — 实施提示词

> 交给另一个 Claude Code 会话执行。直接复制本文到新会话即可。

---

## 任务概述

M4 目标：**让 101 个测试全部通过（或合理跳过）。** M3 留下的 23 个红灯需要在 M4 全部变绿。

当前测试状态：
```
101 tests collected
├── 50 passed   (scoring)
├── 28 skipped  (integration，预期跳过)
└── 23 failed
     ├── 13 template_report — NotImplementedError
     └── 10 validation — Pydantic Field 校验缺失
```

---

## 阅读顺序（开始前必读）

```
1. ../PRD.md          — 产品需求（了解标签含义）
2. ../TECH_DESIGN.md   — 技术设计 §4.3 评分规则 + §4.5 模板报告 + §3.2 Pydantic Schema
3. ../.claude/CLAUDE.md — 开发规范
4. tests/unit/test_template_report.py — 你要让这些测试变绿
5. tests/unit/test_validation.py — 你要让这些测试变绿
6. tests/conftest.py — 公共 fixture
7. tests/fixtures/sample_questions.json — 题库 + 标签配置
```

---

## 任务 1：实现模板报告 (13 个红灯 → 绿)

### 文件：`app/services/template_report.py`

当前状态：`build_summary` 和 `build_full` 均抛出 `NotImplementedError`。

你需要实现两个函数，覆盖 4 种标签的模板内容。

#### 1.1 函数签名

```python
def build_summary(total_score: int, tag: str, answer_summary: dict) -> dict:
    """
    生成部分报告。
    total_score: 原始分 (15-60)
    tag: 标签名
    answer_summary: 可选的关键答案变量（如 {"product_type": "标准化产品"}），用于模板插值
    """

def build_full(total_score: int, tag: str, answer_summary: dict) -> dict:
    """
    生成完整报告。
    """
```

#### 1.2 返回字段

`build_summary` 必须返回以下 7 个字段：
```python
{
    "total_score": int,          # 原样返回输入的分数
    "tag": str,                  # 原样返回输入的标签
    "tag_explanation": str,      # 标签的解释说明
    "preliminary_judgment": str,  # 综合判断
    "strengths": list[str],      # 至少 2 条优势
    "risks": list[str],          # 至少 2 条风险
    "unlock_hint": str,          # 必须包含 "45"
}
```

`build_full` 必须返回以下 6 个字段：
```python
{
    "summary_conclusion": str,   # 综合结论
    "dimension_scores": dict,    # {"公司实力": int, "业务准备": int, "市场认知": int, "执行能力": int}
    "recommended_path": str,     # 推荐路径
    "risk_reminder": str,        # 风险提醒
    "action_plan_30days": list[str],  # 30天行动计划
    "consultant_guide": str,     # 必须包含 "企业微信"
}
```

#### 1.3 4 种标签

| 原始分 | 展示分 | 标签名 |
|--------|--------|--------|
| 15-25 | 60-70 | 观察准备型 |
| 26-35 | 71-80 | 轻量试探型 |
| 35-45 | 81-90 | 基础具备型 |
| 46-60 | 91-100 | 优先布局型 |

每种标签都需要独立的模板内容——优势、风险、建议都不同。

#### 1.4 兜底规则

- 未知标签 → 使用「观察准备型」的模板内容（但 `tag` 字段原样传出）
- 模板中若有 `{变量名}` 占位符，用 `answer_summary` 中的值替换；不存在的变量保留占位符或替换为空字符串，**不要抛异常**

#### 1.5 实现建议

不要用 Jinja2，直接用 Python 字典存储模板内容 + `.format()` 或 f-string 做插值：

```python
# 伪代码结构
TEMPLATES = {
    "观察准备型": {
        "summary": {
            "explanation": "...",
            "judgment": "...",
            "strengths": ["优势1", "优势2", "优势3"],
            "risks": ["风险1", "风险2", "风险3"],
        },
        "full": {
            "conclusion": "...",
            "dimension_scores": {"公司实力": 15, "业务准备": 12, "市场认知": 10, "执行能力": 8},
            "path": "...",
            "risk": "...",
            "action_plan": ["第1步...", "第2步...", "第3步..."],
        }
    },
    "轻量试探型": { ... },
    "基础具备型": { ... },
    "优先布局型": { ... },
}

def build_summary(total_score: int, tag: str, answer_summary: dict) -> dict:
    tmpl = TEMPLATES.get(tag, TEMPLATES["观察准备型"])["summary"]
    return {
        "total_score": total_score,
        "tag": tag,
        "tag_explanation": tmpl["explanation"],
        "preliminary_judgment": tmpl["judgment"],
        "strengths": tmpl["strengths"],
        "risks": tmpl["risks"],
        "unlock_hint": "提交信息后解锁完整报告，并领取 45 分钟 1 对 1 免费解读。",
    }
```

#### 1.6 模板内容要求

模板文案必须遵守 AI 输出限制（与 Prompt 一致）：
- 不承诺收益
- 不使用强否定表达
- 用建设性语气指出风险
- 每个标签的优势/风险要**有区分度**（不能 4 个标签用同一套文案）

---

## 任务 2：补 Pydantic Field 校验 (10 个红灯 → 绿)

### 文件：`app/schemas/lead.py`

`LeadCreate` 需要添加 Field 约束：
```python
from pydantic import BaseModel, Field

class LeadCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=32)
    contact: str = Field(..., min_length=2)
    company: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
```

### 文件：`app/schemas/assessment.py`

`AnswerSubmit` 需要添加 Field 约束：
```python
from pydantic import BaseModel, Field

class AnswerSubmit(BaseModel):
    question_id: int = Field(..., gt=0)
    option_id: int = Field(..., gt=0)
```

#### 注意事项

- 测试 `test_name_max_length` 验证 name 不能超过 32 个字符
- 测试 `test_contact_min_length` 验证 contact 不能短于 2 个字符
- 所有空字符串测试依赖 `min_length=1`（Pydantic 的 `min_length` 会拦截空字符串）
- 使用 `gt=0` 而不是 `ge=0`，因为测试中 option_id=0 应触发 ValidationError

---

## 任务 3：补充 scoring_service 的组合函数

### 文件：`app/services/scoring_service.py`

当前只实现了 `calculate_total` 和 `score_to_tag`。需要补充组合函数：

```python
def calculate_score_and_tag(answers: list[dict]) -> dict:
    """评分入口：计算原始分 → 打标签 → 返回完整结果"""
    raw = calculate_total(answers)
    tag, explanation = score_to_tag(raw)
    return {
        "raw_score": raw,
        "display_score": raw + 45,
        "tag": tag,
        "tag_explanation": explanation,
    }
```

---

## 任务 4：跑测试验证

```bash
cd backend
pip install pydantic pydantic-settings  # 如果提示 ModuleNotFoundError
pytest tests/unit/test_template_report.py -v  # 13 个应全绿
pytest tests/unit/test_validation.py -v        # 10 个应全绿
pytest tests/unit/ -v                           # 所有单元测试应全绿
pytest tests/ -v                                # 最终目标：73 passed + 28 skipped = 0 failed
```

---

## 关键约束

### 测试不准改
- `tests/unit/test_template_report.py` 已经修正完毕，**不要修改测试文件**
- `tests/unit/test_validation.py` 已经修正完毕，**不要修改测试文件**
- 只改 `app/services/template_report.py`、`app/schemas/lead.py`、`app/schemas/assessment.py`、`app/services/scoring_service.py` 四个文件

### 重要提示

1. python 3.9：所有文件顶部需要 `from __future__ import annotations`（已有则保留）
2. 分数体系：内部使用原始分 15-60，展示分 = 原始分 + 45，模板函数接收什么分数就存什么分数
3. 测试第 28 行：`build_summary(30, ...)` → 断言 `result["total_score"] == 30`，验证的是"输入分数原样传出"，不要在这里做 +45 转换
4. 模板文案写成**中文**，面向国内商家读者，专业但可读

---

## 验收标准

```bash
pytest tests/ -v
# 预期输出：
# 73 passed, 28 skipped, 0 failed
```

如果 73 passed + 28 skipped = 0 failed，M4 交付完毕。

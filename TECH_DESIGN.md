# 罗宾出海分析 Agent 技术设计文档

## 1. 技术栈总览

| 层级 | 组件 | 版本要求 | 包名 / 工具 |
| --- | --- | --- | --- |
| Web 框架 | FastAPI + Uvicorn | Python 3.9+ | `fastapi>=0.110`, `uvicorn>=0.29` |
| ORM | SQLAlchemy 2.0 | ≥2.0 | `sqlalchemy>=2.0` |
| 数据库驱动 | PyMySQL / aiomysql | ≥1.1 | `pymysql`, `aiomysql` |
| 数据校验 | Pydantic v2 | ≥2.0 | `pydantic>=2.0`, `pydantic-settings>=2.0` |
| 数据库迁移 | Alembic | ≥1.13 | `alembic>=1.13` |
| AI 调用 | OpenAI 兼容 SDK | ≥1.0 | `openai>=1.0` |
| 结构化输出 | Pydantic（手动校验） | — | SDK 内置支持 |
| 异步 HTTP | httpx | ≥0.27 | `httpx>=0.27` |
| 测试 | pytest | ≥8.0 | `pytest>=8.0`, `pytest-asyncio>=0.23` |
| 部署 | 微信云托管（CloudBase Run）+ Docker | — | `Dockerfile` + `uvicorn>=0.29` |
| 环境管理 | python-dotenv | — | `python-dotenv>=1.0` |
| 微信 API | requests | — | `requests>=2.31` |

---

## 2. 项目目录结构

```
luobin-abroad-agent/
├── backend/
│   ├── main.py                     # FastAPI 应用入口
│   ├── config.py                   # 全局配置（Pydantic Settings）
│   ├── app/
│   │   ├── __init__.py
│   │   ├── api/                    # FastAPI 路由层
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # 微信登录
│   │   │   ├── questions.py        # 题库接口
│   │   │   ├── assessments.py      # 测评 CRUD
│   │   │   ├── reports.py          # 报告查询
│   │   │   ├── leads.py            # 留资
│   │   │   └── admin.py            # 后台管理
│   │   ├── core/                   # 基础设施
│   │   │   ├── __init__.py
│   │   │   ├── database.py         # 数据库连接 + Session 管理
│   │   │   ├── deps.py             # FastAPI 依赖注入
│   │   │   └── middleware.py       # 中间件（请求日志、速率限制、JWT 校验）
│   │   ├── models/                 # SQLAlchemy ORM 模型
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── question.py
│   │   │   ├── assessment.py
│   │   │   ├── answer.py
│   │   │   ├── report.py
│   │   │   ├── lead.py
│   │   │   ├── share_record.py
│   │   │   ├── follow_note.py
│   │   │   └── admin_user.py
│   │   ├── schemas/                # Pydantic 请求/响应模型
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── question.py
│   │   │   ├── assessment.py
│   │   │   ├── report.py
│   │   │   ├── lead.py
│   │   │   └── admin.py
│   │   └── services/               # 业务逻辑层
│   │       ├── __init__.py
│   │       ├── auth_service.py     # 微信登录 + JWT
│   │       ├── scoring_service.py  # 评分 + 标签规则（纯函数）
│   │       ├── report_service.py   # AI 报告 + 模板兜底
│   │       ├── lead_service.py     # 留资 + 解锁逻辑
│   │       ├── prompts.py          # MVP 阶段 Prompt 常量
│   │       └── template_report.py  # 模板报告拼装
│   ├── migrations/                 # Alembic 迁移
│   │   ├── env.py
│   │   ├── alembic.ini
│   │   └── versions/
│   ├── tests/
│   │   ├── conftest.py             # 公共 fixture
│   │   ├── unit/
│   │   │   ├── test_scoring.py     # 评分规则
│   │   │   ├── test_template_report.py  # 模板报告
│   │   │   ├── test_validation.py  # 输入校验
│   │   │   └── test_report_parse.py     # AI 输出 JSON 解析
│   │   ├── integration/
│   │   │   ├── test_assessment_flow.py  # 测评主链路
│   │   │   └── test_api.py         # API 接口测试
│   │   └── fixtures/
│   │       ├── sample_questions.json    # 模拟题库
│   │       └── sample_assessment.json   # 模拟测评结果
│   ├── requirements.txt
│   └── .env.example
├── miniprogram/                    # 微信小程序（刘澳维护）
│   ├── pages/
│   │   ├── index/                  # 首页
│   │   ├── assessment/             # 测评页
│   │   ├── report-generating/      # 报告生成中
│   │   ├── report-partial/         # 部分报告
│   │   ├── lead/                   # 留资页
│   │   ├── report-full/            # 完整报告
│   │   └── my-report/              # 我的报告
│   ├── components/
│   ├── utils/
│   └── images/
├── .claude/
│   └── CLAUDE.md
├── PRD.md
├── TECH_DESIGN.md
├── VIBECODING_BUILD_ORDER.md
└── .gitignore
```

---

## 3. 核心数据结构

### 3.0 ORM 策略说明

> **选择同步 SQLAlchemy + pymysql**，而非异步 SQLAlchemy + aiomysql。
>
> 理由：
> 1. 本项目核心瓶颈在 DeepSeek API 调用耗时（秒级），数据库查询（毫秒级）不是瓶颈
> 2. 同步 SQLAlchemy 代码更简单、调试更容易，适合 2 人 MVP 团队
> 3. FastAPI 中使用 `run_in_executor` 即可在线程池中执行同步 DB 操作，不会阻塞事件循环
> 4. 减少一个第三方依赖（aiomysql），降低部署和排障复杂度

### 3.1 SQLAlchemy ORM 模型

```python
# app/models/user.py
from sqlalchemy import Column, Integer, String, DateTime, func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    openid = Column(String(128), unique=True, nullable=False, index=True)
    unionid = Column(String(128), nullable=True)
    nickname = Column(String(64), default="")
    avatar = Column(String(256), default="")
    created_at = Column(DateTime, server_default=func.now())
    last_login_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

```python
# app/models/question.py
class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    title = Column(String(256), nullable=False)       # 题目文本
    description = Column(String(512), default="")      # 题目说明（难理解时补充）
    dimension = Column(String(64), nullable=False)     # 维度（company/business）
    sort_order = Column(Integer, nullable=False)       # 排序
    is_active = Column(Boolean, default=True)

    options = relationship("QuestionOption", order_by="QuestionOption.sort_order")


class QuestionOption(Base):
    __tablename__ = "question_options"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    option_text = Column(String(256), nullable=False)   # 选项文本
    score = Column(Integer, nullable=False)              # 分值 1-4
    sort_order = Column(Integer, nullable=False)
```

```python
# app/models/assessment.py
class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_score = Column(Integer, nullable=True)         # 总分，计算后写入
    tag = Column(String(32), nullable=True)              # 标签
    status = Column(String(16), default="in_progress")   # in_progress / completed
    benefit_minutes = Column(Integer, default=45)        # 顾问解读分钟数
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)

    answers = relationship("Answer")
    report = relationship("Report", uselist=False)


# app/models/answer.py
class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    option_id = Column(Integer, ForeignKey("question_options.id"), nullable=False)
    score = Column(Integer, nullable=False)
```

```python
# app/models/report.py
class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False, unique=True)
    summary_report_json = Column(JSON, nullable=True)      # 部分报告
    full_report_json = Column(JSON, nullable=True)         # 完整报告
    is_unlocked = Column(Boolean, default=False)           # 是否留资解锁
    generation_type = Column(String(16), default="ai")     # ai / template
    ai_model = Column(String(64), nullable=True)
    prompt_version = Column(String(32), nullable=True)
    generation_status = Column(String(16), default="pending") # pending / generating / success / failed
    generation_error = Column(String(512), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

```python
# app/models/lead.py
class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    name = Column(String(32), nullable=False)          # 姓名
    contact = Column(String(64), nullable=False)        # 电话/微信
    company = Column(String(128), nullable=False)       # 公司
    role = Column(String(64), nullable=False)           # 身份
    created_at = Column(DateTime, server_default=func.now())
```

```python
# app/models/ai_report_logs.py —— AI 调用日志 + 逐题诊断记忆
class AIReportLog(Base):
    __tablename__ = "ai_report_logs"

    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    question_id = Column(Integer, nullable=True)        # v2.0: 逐题诊断时为该题 ID，最终合成为 NULL
    model = Column(String(64), nullable=False)
    prompt_version = Column(String(32), nullable=True)
    request_payload = Column(JSON, nullable=True)
    raw_response = Column(JSON, nullable=True)
    parsed_response = Column(JSON, nullable=True)
    report_memory = Column(Text, nullable=True)         # v2.0: 逐题诊断的记忆文本
    diagnosis_tag = Column(JSON, nullable=True)         # v2.0: 诊断标签列表
    sales_hint = Column(Text, nullable=True)            # v2.0: 销售跟进提示
    status = Column(String(16), default="pending")      # pending / success / failed
    error_message = Column(String(512), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

```python
# app/models/admin_user.py
class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(16), default="admin")
    created_at = Column(DateTime, server_default=func.now())
    last_login_at = Column(DateTime, nullable=True)
```

```python
# app/models/follow_note.py
class FollowNote(Base):
    __tablename__ = "follow_notes"

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    owner = Column(String(64), nullable=False)
    status = Column(String(16), default="uncontacted")  # uncontacted / contacted / booked / closed / invalid
    remark = Column(String(512), default="")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

```python
# app/models/share_record.py
class ShareRecord(Base):
    __tablename__ = "share_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    share_scene = Column(String(32), default="moment")  # 分享场景
    reward_minutes = Column(Integer, default=10)         # 奖励分钟数
    created_at = Column(DateTime, server_default=func.now())
```

### 3.2 Pydantic Schema 模型

```python
# app/schemas/assessment.py
from pydantic import BaseModel

class AnswerSubmit(BaseModel):
    question_id: int
    option_id: int

class AssessmentComplete(BaseModel):
    """完成测评请求"""
    pass  # 15 题答案在 answers 表中，完成时只需校验数量

class AssessmentResponse(BaseModel):
    id: int
    total_score: int | None = None
    tag: str | None = None
    status: str
    benefit_minutes: int = 45
    completed_at: str | None = None

    class Config:
        from_attributes = True
```

```python
# app/schemas/report.py
class SummaryReport(BaseModel):
    """部分报告结构"""
    total_score: int
    tag: str
    tag_explanation: str
    preliminary_judgment: str
    strengths: list[str]       # 2-3 条
    risks: list[str]           # 2-3 条
    unlock_hint: str           # 解锁完整报告引导

class FullReport(BaseModel):
    """完整报告结构"""
    summary_conclusion: str
    dimension_scores: dict[str, int]   # 如 {"公司实力": 22, "业务准备": 18}
    recommended_path: str
    risk_reminder: str
    action_plan_30days: list[str]
    consultant_guide: str
```

```python
# app/schemas/lead.py
class LeadCreate(BaseModel):
    name: str
    contact: str
    company: str
    role: str
```

### 3.3 AI 输出解析校验模型

```python
class AIReportOutput(BaseModel):
    """AI 返回的严格 JSON 结构"""
    summary_report: dict      # 与 SummaryReport 结构一致
    full_report: dict         # 与 FullReport 结构一致
```

> **设计理由**：AI 输出使用 Pydantic 做 JSON 校验而非 Instructor 库，原因：
> 1. DeepSeek API 对 Instructor 的结构化输出支持不如 OpenAI 稳定
> 2. 本项目 AI 调用是"单次生成→JSON 解析→校验"模式，不需要流式结构化
> 3. 减少一个第三方依赖，降低调试复杂度

---

## 4. 主流程设计

### 4.1 用户操作流程图

```
                 ┌──────────────┐
                 │  进入小程序   │
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │ 微信授权登录  │
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │    首页      │
                 │ 开场白+开始  │
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │  测评页×15   │  逐题: 点击选项→自动跳转
                 │ (可返回修改) │
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │ 提交完成测评  │  POST /assessments/{id}/complete
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │ 报告生成中...│  每秒轮询 report-status
                 │ (≤20秒)     │
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │  部分报告    │  GET /reports/{id}/summary
                 │ 分数+标签+  │
                 │ 优势+风险   │
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │  留资页      │  POST /leads
                 │ 4字段+解锁  │
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │  完整报告    │  GET /reports/{id}/full
                 │ 结论+建议+  │
                 │ 企微二维码   │
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │ 转发(权益+10)│  POST /share-records
                 └──────────────┘
```

### 4.2 后端服务调用流程

#### 微信登录流程（关键）

```
小程序端                         后端                             微信服务器
   │                              │                                  │
   ├─ wx.login() ────────────────→│                                  │
   │   获取临时 code               │                                  │
   │                              │                                  │
   │                              ├─ GET jscode2session ────────────→│
   │                              │   appid + secret + code          │
   │                              │←── openid + session_key ────────┤
   │                              │                                  │
   │                              ├─ 查询/创建用户（openid 唯一）     │
   │                              ├─ 签发 JWT Token                  │
   │←── { token, user_id } ──────┤                                  │
   │                              │                                  │
   │ 后续请求携带                  │                                  │
   │ Authorization: Bearer <jwt>  │                                  │
```

> **注意**：jscode2session 接口需使用 `requests` 库调用微信 API，使用 `httpx` 亦可但 `requests` 生态更成熟。后端不保存 `session_key`，只保存 `openid`。

#### 测评完成流程
                   
POST /assessments/{id}/complete
    │
    ├─→ 1. 校验 15 题完整性
    ├─→ 2. assessment_service.complete()
    │       ├─→ scoring_service.calculate()    # 纯函数算分
    │       │       ├─ sum(scores) → total_score
    │       │       └─ score_to_tag() → tag
    │       ├─→ report_service.generate()      # AI 报告
    │       │       ├─→ call_deepseek()        # 调 DeepSeek API
    │       │       ├─→ parse_json()           # JSON 校验
    │       │       ├─→ 成功 → 写入 reports 表
    │       │       └─→ 失败 → template_service.build()
    │       └─→ 更新 assessment 状态
    └─→ return { status, assessment_id }
```

### 4.3 评分规则（v2.0：18 题，17 题计分）

```python
# app/services/scoring_service.py —— 纯函数，无副作用

def calculate_total(answers: list[dict]) -> int:
    """对每题分数求和。第 1 题（行业）不计分，第 2-18 题每题 1-4 分，原始总分 17-68。"""
    return sum(a["score"] for a in answers if a["score"] > 0)

def score_to_tag(raw_score: int) -> tuple[str, str]:
    """根据原始分返回标签和解释。4 档标签（17 题计分版）。"""
    if raw_score <= 30:
        return ("观察准备型", "出海基础尚浅，建议先从定位梳理和轻量内容测试开始。")
    elif raw_score <= 43:
        return ("轻量试探型", "已具备部分条件，可启动强成交人设内容矩阵进行低成本验证。")
    elif raw_score <= 56:
        return ("基础具备型", "基础条件较好，适合系统化推进短视频出海获客体系。")
    else:
        return ("优先布局型", "整体条件成熟，可进行多语种矩阵布局和规模化获客。")

def calculate_score_and_tag(answers: list[dict]) -> dict:
    """完整的评分入口：计算总分 → 打标签 → 返回结果"""
    raw = calculate_total(answers)
    tag, explanation = score_to_tag(raw)
    return {
        "raw_score": raw,
        "display_score": raw + 43,  # 内部 17-68 → 展示 60-111
        "tag": tag,
        "tag_explanation": explanation,
    }
```

**原始分 ↔ 展示分映射表（17 题计分版）：**

| 原始分 | 展示分 | 标签 | 说明 |
|--------|--------|------|------|
| 17-30 | 60-73 | 观察准备型 | 出海基础尚浅，建议先从定位梳理和轻量内容测试开始 |
| 31-43 | 74-86 | 轻量试探型 | 已具备部分条件，可启动强成交人设内容矩阵进行低成本验证 |
| 44-56 | 87-99 | 基础具备型 | 基础条件较好，适合系统化推进短视频出海获客体系 |
| 57-68 | 100-111 | 优先布局型 | 整体条件成熟，可进行多语种矩阵布局和规模化获客 |

> **设计理由**：
> 1. 第 1 题为行业手动输入，不计分——用于分销路由（不同行业对应不同销售企微二维码）
> 2. 内部使用原始分 17-68，对外通过 `+43` 映射为展示分 60-111
> 3. 评分规则是纯函数，没有 I/O、没有数据库依赖，最值得 TDD

### 4.4 AI 报告生成流程（v2.0：逐题诊断 + 最终合成）

```
┌─ 阶段 1：逐题诊断（用户答每道题时触发，后台静默）─────────┐
│                                                          │
│  POST /assessments/{id}/answers                          │
│    │                                                     │
│    ├─→ 保存答案到 DB                                      │
│    └─→ 后台异步：diagnose_single_question(                │
│              question_text, answer_text,                  │
│              option_business_meaning,                     │
│              previous_answer_summary                      │
│          )                                               │
│          ├─→ DeepSeek API（单题诊断 Prompt）               │
│          ├─→ 生成 diagnosis_tag + report_memory +         │
│          │     sales_hint                                │
│          └─→ 存入 ai_report_logs                         │
│                                                          │
└──────────────────────────────────────────────────────────┘

┌─ 阶段 2：最终合成（完成测评时触发）───────────────────────┐
│                                                          │
│  POST /assessments/{id}/complete                         │
│    │                                                     │
│    ├─→ scoring_service.calculate()                       │
│    ├─→ 收集全部 18 条 report_memory                       │
│    ├─→ report_service.generate_full()                     │
│    │       ├─→ [AI 路径] 汇总 Prompt（分数+标签+          │
│    │       │     18 条诊断记忆→DeepSeek→JSON 报告）       │
│    │       │     成功 → DB，generation_type="ai"           │
│    │       └─→ [模板] 失败 → template_service.build()      │
│    └─→ 更新 assessment 状态                               │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**单题诊断输出结构**（仅内部使用，不展示给用户）：

```json
{
  "question_id": 6,
  "diagnosis_tag": ["获客依赖线下", "内容资产不足", "适合轻资产验证"],
  "report_memory": "该用户有海外获客基础，但线上内容获客能力不足。完整报告中应重点建议：1)建立强成交人设内容矩阵 2)从平台电商获客向社媒内容获客过渡。",
  "sales_hint": "后续顾问沟通可重点询问：目前海外客户主要来自哪些国家、展会线索转化周期多长、是否有现成客户案例可拍成内容。"
}
```

**最终报告结构（融合版）**：
基于强成交人设「定位定生死、内容定江山、SOP定天下」三段框架 + 结构化评分：

```json
{
  "summary_report": {
    "total_score": 52, "tag": "基础具备型",
    "positioning_assessment": "定位评价...",
    "content_assessment": "内容力评价...",
    "conversion_assessment": "转化力评价...",
    "strengths": [...], "risks": [...], "unlock_hint": "..."
  },
  "full_report": {
    "conclusion": "...",
    "positioning_detail": "...",
    "content_detail": "...",
    "conversion_detail": "...",
    "recommended_path": "...",
    "action_plan_30days": [...],
    "consultant_guide": "..."
  }
}
```

**AI 输出限制（Prompt 层做、后端校验层兜底）**：
- 不承诺收益
- 不输出确定性合规结论
- 不编造用户未提供的信息
- 不使用强否定表达
- 报告内容严格基于强成交人设方法论

### 4.5 模板报告生成

```python
# app/services/template_report.py

def build_summary(total_score: int, tag: str, answer_summary: dict) -> dict:
    """标签模板 + 关键答案变量插值"""
    template = SUMMARY_TEMPLATES.get(tag, SUMMARY_TEMPLATES["观察准备型"])
    return {
        "total_score": total_score,
        "tag": tag,
        "tag_explanation": template["explanation"],
        "preliminary_judgment": template["judgment"],
        "strengths": resolve_conditional(template["strengths"], answer_summary),
        "risks": resolve_conditional(template["risks"], answer_summary),
        "unlock_hint": "提交信息后解锁完整报告，并领取 45 分钟 1 对 1 免费解读。",
    }

def build_full(total_score: int, tag: str, answer_summary: dict) -> dict:
    """完整报告模板，包含变量插值"""
    template = FULL_TEMPLATES.get(tag, FULL_TEMPLATES["观察准备型"])
    return {
        "summary_conclusion": template["conclusion"].format(**answer_summary),
        "dimension_scores": template["dimension_scores"],
        "recommended_path": template["path"],
        "risk_reminder": template["risk"],
        "action_plan_30days": template["action_plan"],
        "consultant_guide": "以上建议供初步参考，具体出海方案请联系企业微信顾问获得 1 对 1 解读。",
    }
```

> **设计理由**：模板报告作为 AI 的兜底方案，必须在前端无感知的前提下工作。因此模板的输入输出结构必须与 AI 报告完全一致，前端不区分报告来源。

---

## 5. API 接口设计

### 5.1 REST API 总览

```
基础路径: /api
```

#### 认证

```
POST /api/auth/wechat-login
```

请求体：
```json
{
  "code": "wx_code_from_frontend"
}
```

响应体（200）：
```json
{
  "user_id": 1,
  "openid": "oXXXXXXX",
  "token": "jwt_token_string",
  "is_new": false
}
```

#### 题库

```
GET /api/questions
```

响应体（200）：
```json
{
  "questions": [
    {
      "id": 1,
      "title": "企业业务类型",
      "description": "",
      "dimension": "company",
      "sort_order": 1,
      "options": [
        {"id": 1, "text": "本地服务/强线下", "score": 1, "sort_order": 1},
        {"id": 2, "text": "传统贸易/批发", "score": 2, "sort_order": 2},
        {"id": 3, "text": "消费品/电商/轻制造", "score": 3, "sort_order": 3},
        {"id": 4, "text": "品牌产品/高复购/标准化产品", "score": 4, "sort_order": 4}
      ]
    }
  ],
  "total": 15
}
```

#### 测评

```
POST /api/assessments
```

**需要 Header**: `Authorization: Bearer <token>`（JWT 鉴权，user_id 从 token 解析）

响应体（200）：
```json
{
  "id": 1,
  "status": "in_progress"
}
```

```
POST /api/assessments/{id}/answers
```

请求体：
```json
{
  "question_id": 1,
  "option_id": 3
}
```

响应体（200）：
```json
{
  "question_id": 1,
  "option_id": 3,
  "score": 3
}
```

```
POST /api/assessments/{id}/complete
```

响应体（200）：
```json
{
  "assessment_id": 1,
  "total_score": 78,
  "tag": "轻量试探型",
  "status": "generating"
}
```

```
GET /api/assessments/{id}/report-status
```

响应体（200，生成中）：
```json
{
  "status": "generating",
  "elapsed_seconds": 3
}
```

响应体（200，成功）：
```json
{
  "status": "success",
  "generation_type": "ai",
  "has_summary": true,
  "has_full": false
}
```

#### 报告

```
GET /api/reports/{assessment_id}/summary
```

响应体（200）：
```json
{
  "total_score": 78,
  "tag": "轻量试探型",
  "tag_explanation": "已具备部分条件，但关键能力尚未完整...",
  "preliminary_judgment": "您的企业正在出海门槛上...",
  "strengths": ["已有一定线上获客经验", "对目标市场有初步了解"],
  "risks": ["产品标准化程度不足", "海外交付能力需要验证"],
  "unlock_hint": "提交信息后解锁完整报告..."
}
```

```
GET /api/reports/{assessment_id}/full
```

**需要 Header**: `Authorization: Bearer <token>` — 后端根据 token 中的 user_id 查询该测评是否有对应的 lead 记录，若已留资则返回完整报告，否则返回 403。

响应体（200）：
```json
{
  "summary_conclusion": "综合来看，您的出海条件...",
  "dimension_scores": {"公司实力": 22, "业务准备": 18, "市场认知": 20, "执行能力": 18},
  "recommended_path": "建议优先选择东南亚市场...",
  "risk_reminder": "需注意供应链交付稳定性...",
  "action_plan_30days": ["完成产品出海版本准备", "注册目标国家商标"],
  "consultant_guide": "以上建议供初步参考..."
}
```

#### 留资

```
POST /api/leads
```

请求体：
```json
{
  "name": "张三",
  "contact": "13800138000",
  "company": "某贸易有限公司",
  "role": "创始人"
}
```

响应体（200）：
```json
{
  "lead_id": 1,
  "unlocked": true,
  "benefit_minutes": 45
}
```

#### 转发

```
POST /api/share-records
```

请求体：
```json
{
  "assessment_id": 1,
  "share_scene": "moment"
}
```

响应体（200）：
```json
{
  "reward_minutes": 10,
  "total_benefit_minutes": 55
}
```

#### 后台管理

```
GET  /api/admin/leads?page=1&size=20&tag=轻量试探型&is_unlocked=true
GET  /api/admin/assessments/{id}
GET  /api/admin/ai-report-logs?page=1&size=20&status=failed
POST /api/admin/follow-notes
```

### 5.2 LLM API 调用约定

```python
from openai import OpenAI
from app.core.config import settings

client = OpenAI(
    base_url=settings.llm_base_url,    # https://api.deepseek.com
    api_key=settings.llm_api_key,
)

def generate_report(
    prompt: str,
    timeout: int = 15,
) -> str:
    """调用 DeepSeek API 生成报告正文，返回 JSON 字符串"""
    resp = client.chat.completions.create(
        model=settings.llm_model,       # deepseek-chat
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        timeout=timeout,
    )
    return resp.choices[0].message.content
```

> **设计理由**：不使用 LangChain/LangGraph 等编排框架。本项目 AI 调用模式单一（一次 Prompt 输入→一次 JSON 输出→校验），引入编排框架增加复杂度而无收益。

---

## 6. 配置管理

### 6.1 全局配置

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 数据库
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "luobin_agent"

    # LLM（DeepSeek）
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_timeout: int = 15       # 单次调用超时秒数

    # JWT
    jwt_secret: str = "your-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 72

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    port: int = 8000                  # 云托管会注入 PORT 环境变量
    debug: bool = False

    # WeChat
    wx_appid: str = ""
    wx_secret: str = ""

    # 云托管
    cloudbase_env_id: str = ""        # 云托管环境 ID

    # 报告
    ai_report_enabled: bool = True    # 控制 AI 开关，算法备案不通过时设为 False
    report_poll_interval: float = 1.5 # 前端轮询间隔（秒）
    report_generate_timeout: int = 20 # 报告生成超时提示阈值（秒）

    class Config:
        env_file = ".env"
        env_prefix = "LB_"
```

### 6.2 Prompt 管理策略

**MVP 阶段**：所有 Prompt 以 Python 字符串常量形式放在 `services/prompts.py`。

```python
# app/services/prompts.py —— MVP 阶段的 Prompt 常量

SYSTEM_SUMMARY_REPORT = """
你是一个出海机会评估顾问。请根据用户的测评得分和答案，生成一份简短的部分报告。

规则：
1. 只基于用户提供的分数和答案信息，不要编造用户未提供的信息
2. 不要承诺具体收益（如"您的利润可提升300%"）
3. 不使用强否定表达，用建设性方式指出风险
4. 输出必须是严格 JSON 格式

输出 JSON 结构：
{
  "preliminary_judgment": "综合判断...",
  "strengths": ["优势1", "优势2"],
  "risks": ["风险1", "风险2"],
  "tag_explanation": "对此标签的解释..."
}
"""

SYSTEM_FULL_REPORT = """
你是一个出海机会评估顾问。请根据用户的测评得分和答案，生成一份完整的出海评估报告。

规则：
1. 只基于用户提供的信息
2. 不承诺收益，不输出确定性合规结论
3. 不使用强否定表达
4. 30 天行动计划必须可执行、具体
5. 输出必须是严格 JSON 格式

输出 JSON 结构：
{
  "summary_conclusion": "综合结论...",
  "dimension_scores": {"公司实力": 0, "业务准备": 0, "市场认知": 0, "执行能力": 0},
  "recommended_path": "推荐出海路径...",
  "risk_reminder": "风险提醒...",
  "action_plan_30days": ["第1步...", "第2步..."],
  "consultant_guide": "1对1解读引导..."
}
"""
```

> **设计理由**：同参考文档——减少间接层，AI 辅助编码时能看到完整上下文；核心链路跑通后再考虑抽离模板。

---

## 7. 安全设计

| 防护点 | 机制 | 实现方式 |
| --- | --- | --- |
| 用户身份 | JWT Token | 微信登录后签发 JWT，API 层依赖注入验证 |
| API 密钥保护 | 后端独占 | AI API Key 只存在后端环境变量和 `config.py`，前端不接触 |
| 数据隐私 | openid 加密 | 用户标识字段加密存储，日志脱敏 |
| AI 输出失控 | JSON 校验 + 字段校验 | 使用 Pydantic 模型校验 AI 返回，字段缺失/格式错误走模板 |
| AI 内容安全 | Prompt 硬约束 | System Prompt 明确禁止收益承诺和合规结论 |
| 报告解锁控制 | 后端校验 | 完整报告必须有 `is_unlocked=true` 才返回，纯后端控制 |
| 接口认证 | JWT 中间件 | `/api/admin/*` 需要管理员权限；其他接口需要有效 JWT |
| 接口安全 | HTTPS | 云托管自动分配 HTTPS 域名，自动加入小程序合法域名白名单 |
| 速率限制 | 中间件 | 单 IP 限 60 次/分钟 |

---

## 8. 依赖清单（requirements.txt）

```
# Web Framework
fastapi>=0.110
uvicorn>=0.29

# Database
sqlalchemy>=2.0
pymysql>=1.1
alembic>=1.13
cryptography>=41.0      # MySQL 8.x 密码认证需要

# Validation
pydantic>=2.0
pydantic-settings>=2.0

# AI
openai>=1.0

# Auth
PyJWT>=2.8
httpx>=0.27             # HTTP 客户端，用于测试

# WeChat
requests>=2.31          # 调用微信 jscode2session API

# Env
python-dotenv>=1.0

# Dev & Test
pytest>=8.0
pytest-asyncio>=0.23
pytest-mock>=3.14
```

---

## 9. 测试规范（TDD）

### 9.1 原则

**所有核心函数必须先写 Pytest 单元测试，再实现功能代码**。评分规则、AI 输出解析、模板报告拼装这些纯函数模块最值得优先测试。

### 9.2 测试目录结构

```
tests/
├── conftest.py                    # 公共 fixture（mock 题库、mock AI 响应、测试数据库）
├── unit/
│   ├── test_scoring.py            # 评分规则：分数计算、边界、标签映射
│   ├── test_template_report.py    # 模板报告：标签匹配、变量插值
│   ├── test_validation.py         # 输入校验：留资表单、答案提交
│   └── test_report_parse.py       # AI 输出解析：JSON 校验、字段缺失、格式异常
├── integration/
│   ├── test_assessment_flow.py    # 测评主链路：创建→答题→完成→报告生成
│   └── test_api.py               # API 接口：认证、鉴权、响应格式
└── fixtures/
    ├── sample_questions.json      # 模拟 15 道题完整配置
    └── sample_assessment.json     # 模拟测评结果
```

### 9.3 关键 Fixture

```python
# tests/conftest.py
import pytest
from app.services.scoring_service import calculate_score, score_to_tag

@pytest.fixture
def sample_answers() -> list[dict]:
    """15 题标准答案，每题 3 分，总计 45 → 映射为 75 分 """
    return [
        {"question_id": i, "option_id": i, "score": 3}
        for i in range(1, 16)
    ]

@pytest.fixture
def mock_ai_response() -> dict:
    """模拟 DeepSeek 成功返回的 JSON"""
    return {
        "summary_report": {
            "preliminary_judgment": "您的企业具备基本出海条件...",
            "strengths": ["优势1"],
            "risks": ["风险1"],
            "tag_explanation": "已具备部分条件..."
        },
        "full_report": {
            "summary_conclusion": "综合结论...",
            "dimension_scores": {"公司实力": 20, "业务准备": 18},
            "recommended_path": "东南亚市场",
            "risk_reminder": "注意风险",
            "action_plan_30days": ["第1步"],
            "consultant_guide": "联系顾问"
        }
    }
```

### 9.4 测试优先级

| 优先级 | 模块 | 必须覆盖的场景 |
|--------|------|----------------|
| P0 | `test_scoring.py` | 原始分 17→观察准备型 / 30→观察/31→轻量试探/44→基础具备/57→优先布局 / 17 题累加正确 |
| P0 | `test_assessment_flow.py` | 创建测评→逐题提交→完成→报告状态 success |
| P1 | `test_template_report.py` | 4 种标签全部有对应模板 / 变量插值正确 / 缺失变量时优雅降级 |
| P1 | `test_report_parse.py` | 完整 JSON 解析成功 / 缺失字段检测 / 非法 JSON 走模板兜底 |
| P2 | `test_validation.py` | 空姓名拒绝 / 电话格式校验 / 答案重复提交处理 |
| P2 | `test_api.py` | 未认证请求返回 401 / 完整报告未解锁返回 403 / 健康检查返回 200 |

---

## 10. 部署架构（微信云托管）

### 10.1 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 云托管默认使用 80 端口（PORT 环境变量由平台注入）
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 10.2 架构图

```
┌─────────────────────────────────────────────────┐
│              微信小程序（用户端）                  │
│      wx.request(云托管域名)                       │
└──────────────────────┬──────────────────────────┘
                       │ HTTPS（自动）
┌──────────────────────▼──────────────────────────┐
│            微信云托管 (CloudBase Run)              │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │           Docker 容器 (Python/FastAPI)        │ │
│  │                                              │ │
│  │  ┌──────┐ ┌─────────┐ ┌──────────────────┐ │ │
│  │  │ API  │ │ Service │ │ AI 报告(DeepSeek) │ │ │
│  │  │ 路由  │ │  逻辑   │ │                  │ │ │
│  │  └──────┘ └─────────┘ └──────────────────┘ │ │
│  └─────────────────────────────────────────────┘ │
│                       │                           │
│  ┌────────────────────▼────────────────────────┐ │
│  │     云开发数据库 (TencentDB for MySQL)        │ │
│  │    users / questions / assessments / ...     │ │
│  └─────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────┘
```

### 10.3 部署步骤

```bash
# 1. 安装 CloudBase CLI
npm install -g @cloudbase/cli

# 2. 登录
tcb login

# 3. 初始化云托管（在项目根目录）
tcb init

# 4. 部署
tcb deploy

# 或通过微信开发者工具：
# 云开发 → 云托管 → 新建服务 → 上传 Dockerfile
```

### 10.4 环境变量配置

在云托管控制台设置以下环境变量（对应 `config.py` 中的 Settings）：

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `LB_DB_HOST` | MySQL 主机地址 | ✅ |
| `LB_DB_PORT` | MySQL 端口 | ✅ |
| `LB_DB_USER` | 数据库用户名 | ✅ |
| `LB_DB_PASSWORD` | 数据库密码 | ✅ |
| `LB_DB_NAME` | 数据库名 | ✅ |
| `LB_LLM_API_KEY` | DeepSeek API Key | ✅ |
| `LB_JWT_SECRET` | JWT 签名密钥 | ✅ |
| `LB_WX_APPID` | 小程序 AppID | ✅ |
| `LB_WX_SECRET` | 小程序 AppSecret | ✅ |
| `LB_AI_REPORT_ENABLED` | AI 报告开关 | 否（默认 true） |

### 10.5 云托管优势

| 对比项 | 自建服务器 | 微信云托管 |
|--------|-----------|-----------|
| ICP 备案 | 需要（7-20 天） | **不需要** |
| HTTPS 证书 | 自己申请配 | **自动分配** |
| 域名白名单 | 手动添加 | **自动加入** |
| 弹性伸缩 | 手动升级 | **自动扩缩容** |
| 环境管理 | 自己配 | **控制台管理** |
| 成本 | ECS 月费固定 | **按调用量计费** |

---

## 11. 决策记录

| 决策 | 选项 | 结论 | 理由 |
| --- | --- | --- | --- |
| AI 编排框架 | LangChain / 无框架 | **无框架** | 本项目 AI 调用模式单一（一次 Prompt→一次输出），引入框架增加复杂度无收益 |
| 结构化输出 | Instructor / 手动 Pydantic | **手动 Pydantic 校验** | DeepSeek 对 Instructor 支持不稳定；手动校验代码量小且可控 |
| 评分规则位置 | 数据库存储 / 代码硬编码 | **代码硬编码** | 规则简单（15 题求和+4 段映射），硬编码可读性更好，改动频率极低 |
| 题目配置 | 数据库 / 代码硬编码 | **数据库配置** | 题目可能需要调整，配置化避免发版 |
| AI 开关 | 配置文件 / 环境变量 | **环境变量** | `ai_report_enabled` 控制 AI 启用/关闭，紧急情况不改代码就能切换模板模式 |
| 前端轮询 | WebSocket / 定时轮询 | **定时轮询（1.5s）** | 微信小程序 WebSocket 支持不如 HTTP 成熟；1.5 秒间隔足够平滑 |
| 完整报告解锁 | 前端判断 / 后端判断 | **后端判断** | 解锁状态必须由后端控制，避免前端篡改 |
| 状态机 | LangGraph / 手写 | **手写（if-else 分支）** | 主流程只有 1 条链路，无复杂循环分支，手写可读性更高 |
| 鉴权方式 | 请求体传 user_id / JWT 解析 | **JWT 解析** | 请求体传 user_id 不安全，客户端可伪造；JWT 由后端签发不可篡改 |
| 完整报告解锁 | 客户端 Header / 后端校验 | **后端校验是否有 lead 记录** | 前端传 Header 不安全，用户可伪造；由后端查询 lead 表判断 |
| ORM 模式 | 同步 / 异步 | **同步 SQLAlchemy** | 瓶颈在 AI 调用不在 DB，同步代码更简单；线程池不影响事件循环 |
| 部署方案 | 自建 ECS / 微信云托管 | **微信云托管** | 免 ICP 备案、自动 HTTPS、自动域名白名单、按量计费适合 MVP |
| Python 版本 | 3.11 / 3.9 | **3.9** | 本地开发机只有 3.9，通过 `from __future__ import annotations` + `eval_type_backport` 兼容新语法 |
| 评分域 v2.0 | 17 题计分（18 题，第 1 题不计分）| **原始分 17-68，展示分 +43** | 第 1 题行业用于分销路由；评分只计 17 题选择题 |
| AI 报告模式 | 一次性生成 / 两阶段（逐题诊断+合成）| **两阶段** | 逐题静默诊断不打断用户；最终报告基于 18 条诊断记忆合成 |
| 报告结构 | 传统结构化 / 强成交人设三段式 | **融合版** | 三段框架（定位/内容/转化）+ 结构化评分 |

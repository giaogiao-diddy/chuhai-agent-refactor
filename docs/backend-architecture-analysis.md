# 后端架构分析报告

> 生成日期：2026-06-17 · 分支：feat/lin-backend

---

## 一、整体架构概览

项目拥有 **两套后端**，当前生产环境使用 **CloudBase 云函数后端**，Python FastAPI 后端作为 V1/V2 历史版本保留。

```
┌──────────────────────────────────────────────────────┐
│                  微信小程序（前端）                      │
│          miniprogram/  ·  AppID: wx7ed6bdb5ed913fa9   │
├──────────────────────┬───────────────────────────────┤
│   cloudApi.js        │   config.js                    │
│   wx.cloud.callFunc  │   HTTP → 127.0.0.1:8000        │
│   → 云函数调用        │   → Python 后端（已废弃）        │
└─────────┬────────────┴───────────┬───────────────────┘
          │                        │
          ▼                        ▼
┌──────────────────┐   ┌──────────────────────────────┐
│ CloudBase 后端    │   │ Python FastAPI 后端 (V1/V2)   │
│ ✅ 当前使用        │   │ 🔒 历史版本 · 只读参考          │
│                  │   │                              │
│ 12 个云函数       │   │ FastAPI + SQLAlchemy + MySQL │
│ NoSQL 文档数据库  │   │ JWT 认证 · 微信登录           │
│ wx-server-sdk    │   │ DeepSeek AI · Pydantic v2    │
│ 模板报告（无AI）   │   │ AI报告 + 模板兜底              │
└──────────────────┘   └──────────────────────────────┘
```

---

## 二、CloudBase 后端（当前使用）详细分析

**环境 ID**: `cloud1-d8gh82s3a39eff92d`

### 2.1 架构模式

```
cloudfunctions/
├── shared/                          ← 共享模块（代码拷贝到各云函数）
│   ├── db.js                        ← wx-server-sdk 初始化，导出 db/_/getContext/now
│   ├── questionFlow.js              ← 题目定义（15题）+ 分支逻辑 + 题目获取
│   ├── scoring.js                   ← 双维度评分：feasibility_score + lead_score
│   ├── reportTemplate.js            ← 模板报告生成（客户版 + 顾问版）
│   ├── validators.js                ← 答案校验（5种题目类型）
│   └── __tests__/shared.test.js     ← 共享模块单元测试
│
├── createAssessment/                ← 创建测评
├── getQuestionFlow/                 ← 获取题目流（支持分支）
├── submitAnswer/                    ← 提交单题答案（upsert）
├── completeAssessment/              ← 完成测评 → 算分 → 生成报告
├── generateReport/                  ← 生成报告（delegates to completeAssessment）
├── getReportList/                   ← 获取用户报告列表
├── getReportDetail/                 ← 获取报告详情（partial/full）
├── getConsultantLeadReport/         ← 获取顾问跟进行报告
├── createWecomUnlockSession/        ← 创建企微解锁会话
├── getWecomUnlockStatus/            ← 查询解锁状态
└── mockUnlock/                      ← 开发环境模拟解锁
```

### 2.2 数据模型（CloudBase NoSQL 文档数据库）

| 集合(Collection) | 用途 | 关键字段 |
|---|---|---|
| `assessments` | 测评记录 | openid, status, branch, answers, feasibility_score, lead_score, feasibility_tag, lead_priority, is_unlocked |
| `answers` | 答案明细 | openid, assessment_id, question_id, question_type, option_id, option_ids, answer_text, score_detail |
| `reports` | 客户报告 | openid, assessment_id, generation_type, generation_status, is_unlocked, report_json |
| `lead_reports` | 顾问跟进行报告 | openid, assessment_id, report_json (lead_score, lead_priority, followup_focus, opening_script) |
| `wecom_unlock_sessions` | 企微解锁会话 | openid, assessment_id, report_id, status |
| `ai_report_logs` | AI调用日志（待实现） | — |
| `uploaded_files` | 文件上传（待实现） | — |
| `users` | 用户表（待实现） | — |

### 2.3 核心业务流程

#### 测评流程
```
1. createAssessment  →  创建测评，状态: in_progress
2. getQuestionFlow   →  获取题目列表（含分支判断）
3. submitAnswer ×N   →  逐题保存答案（重复提交=覆盖）
   ↓ (回答 q_has_overseas 后建立 branch: "has_overseas" | "no_overseas")
   ↓ (重新调用 getQuestionFlow 获取分支专属题)
4. completeAssessment → 校验必答题完整 → 双维度算分 → 生成报告 → 状态: completed
```

#### 报告结构
```
report_json
├── hero                    ← 标题/分数/标签/一句话判断/核心矛盾
├── summary_report          ← 公开可见的部分报告
│   ├── industry_market
│   ├── preliminary_judgment
│   ├── strengths / risks / recommended_path
│   └── unlock_hint
└── full_report             ← 解锁后可见
    ├── summary_conclusion
    ├── industry/pathway/positioning/content/conversion_assessment
    ├── dimension_scores (feasibility / lead)
    ├── risk_cards (市场路径/短视频适配/交付兑现)
    ├── action_plan_30days
    └── consultant_guide
```

### 2.4 题目系统（动态分支流）

**15 道题目，3 组结构：**

| 组 | 题目 | 分支 |
|---|---|---|
| 基础题（必答） | q_industry, q_company_type, q_team_scale, q_revenue_pressure, q_has_overseas | common |
| 有出海经验分支 | q_overseas_channels, q_overseas_market, q_order_quality | has_overseas |
| 无出海经验分支 | q_domestic_strength, q_first_overseas_goal | no_overseas |
| 公共题（必答） | q_product_advantages, q_materials, q_short_video_restriction, q_execution_willingness, q_biggest_concern | common |

**支持 6 种题目类型**: `single_choice`, `multiple_choice`, `text`, `number`, `file`, `url`

### 2.5 评分体系

每个选项带有两个独立分数：

| 维度 | 作用 | 分值范围 | 分级 |
|---|---|---|---|
| `feasibility_score` | 出海可行性（客户可见） | 0-80 | 观察准备型(≤20) / 轻量试探型(≤35) / 基础具备型(≤50) / 优先布局型(>50) |
| `lead_score` | 顾问跟进优先级（仅顾问可见） | 0-80 | P0-立即跟进(≥45) / P1-重点跟进(≥30) / P2-培育跟进(≥18) / P3-低频触达(<18) |

### 2.6 认证与鉴权

- **身份识别**: `cloud.getWXContext().OPENID` — 微信原生 OpenID，无需 JWT
- **数据隔离**: 所有查询加 `openid` 过滤
- **归属校验**: 操作前校验 `assessment.data.openid === OPENID`
- **顾问权限**: 当前 MVP 顾问报告只能由报告所有者查看（待实现顾问角色系统）

### 2.7 当前状态评估

| 维度 | 状态 |
|---|---|
| 核心测评流程 | ✅ 已完成（create → answer → complete → report） |
| 题目分支系统 | ✅ 已完成 |
| 双维度评分 | ✅ 已完成 |
| 模板报告（客户+顾问） | ✅ 已完成 |
| 报告列表/详情/部分解锁 | ✅ 已完成 |
| 企微解锁基础流程 | ✅ 已完成 |
| 单元测试 | ✅ shared 模块有测试 |
| AI 报告生成 | ❌ 未实现（generateReport 直接 delegate 到 completeAssessment） |
| DeepSeek AI 集成 | ❌ 未迁移（Python 版有完整实现） |
| 文件上传 | ❌ 未实现 |
| 后台管理/顾问端 | ❌ 未实现（API_CONTRACT.md 中规划了 11 个接口） |
| 微信登录集成 | ❌ 未实现（Python 版有完整 JWT 流程） |
| 留资表单 | ❌ 未迁移 |
| 单题 AI 诊断记忆 | ❌ 未迁移 |

---

## 三、Python FastAPI 后端（历史版本）详细分析

### 3.1 架构模式

```
backend/
├── main.py                    ← FastAPI 入口 · lifespan 建表 · 路由挂载 · 中间件
├── config.py                  ← Pydantic Settings · 环境变量集中管理
├── Dockerfile                 ← 部署用 Docker 构建
├── requirements.txt           ← Python 依赖
├── seed_dev.py                ← 开发环境种子数据脚本
├── seed_admin.py              ← 管理员账号种子脚本
│
├── app/
│   ├── api/                   ← FastAPI 路由（thin layer）
│   │   ├── auth.py            ← 微信登录 → JWT 签发
│   │   ├── questions.py       ← 题库查询（18 题，MySQL 存储）
│   │   ├── assessments.py     ← 测评 CRUD + 答题 + 完成 + 后台任务
│   │   ├── reports.py         ← 报告查询（summary/full/my）
│   │   ├── leads.py           ← 留资 + 转发记录
│   │   ├── admin.py           ← 后台管理（登录/线索/测评详情/AI日志/跟进备注）
│   │   └── wecom.py           ← 企微解锁（创建会话/查询状态/回调/模拟解锁）
│   │
│   ├── core/                  ← 基础设施
│   │   ├── database.py        ← SQLAlchemy 引擎 + Session + init_db
│   │   ├── deps.py            ← JWT 依赖注入（get_current_user / require_admin）
│   │   └── middleware.py      ← 请求日志 + 速率限制（空壳）
│   │
│   ├── models/                ← SQLAlchemy ORM 模型（10 张表）
│   │   ├── user.py            ← User (openid, unionid, nickname, avatar)
│   │   ├── question.py        ← Question + QuestionOption (题库)
│   │   ├── assessment.py      ← Assessment (测评)
│   │   ├── answer.py          ← Answer (答案)
│   │   ├── report.py          ← Report (报告)
│   │   ├── lead.py            ← Lead (留资)
│   │   ├── share_record.py    ← ShareRecord (转发)
│   │   ├── follow_note.py     ← FollowNote (跟进备注)
│   │   ├── admin_user.py      ← AdminUser (管理员)
│   │   └── ai_report_log.py   ← AIReportLog (AI调用日志)
│   │
│   ├── schemas/               ← Pydantic v2 请求/响应模型
│   │   ├── auth.py · assessment.py · question.py · report.py
│   │   ├── lead.py · admin.py · wecom.py
│   │
│   └── services/              ← 业务逻辑层
│       ├── scoring_service.py       ← 评分规则（纯函数，17-68 → 60-111）
│       ├── report_service.py        ← AI 报告生成 + JSON 校验 + 字段完整性检测 + 兜底
│       ├── template_report.py       ← 模板报告（4 个标签 × V2 结构）
│       ├── prompts.py               ← DeepSeek Prompt 常量（单题诊断 + 完整报告）
│       ├── auth_service.py          ← 微信登录 + JWT 签发
│       ├── lead_service.py          ← 留资 + 报告解锁
│       └── wecom_unlock_service.py  ← 企微解锁服务
│
├── tests/
│   ├── unit/                  ← 单元测试（评分/模板/校验/报告解析）
│   ├── integration/           ← 集成测试（API/测评流程）
│   ├── conftest.py            ← 测试配置 + SQLite
│   └── fixtures/              ← 种子数据 JSON
│
├── migrations/                ← Alembic 数据库迁移
│   └── versions/20260616_v2_assessment_ai_memory.py
│
└── static/admin.html          ← 管理后台单页
```

### 3.2 数据模型（MySQL 8.x 关系型）

**10 张表：**

| 表 | 用途 | 核心字段 |
|---|---|---|
| `users` | 微信用户 | id, openid(UK), unionid, nickname, avatar, created_at, last_login_at |
| `questions` | 题库 | id, title, description, dimension, sort_order, is_active, is_scored |
| `question_options` | 选项 | id, question_id(FK), option_text, score(1-4), sort_order |
| `assessments` | 测评 | id, user_id(FK), total_score, tag, status, benefit_minutes, created_at, completed_at |
| `answers` | 答案 | id, assessment_id(FK), question_id(FK), option_id(FK), answer_text, score |
| `reports` | 报告 | id, assessment_id(FK, UK), summary_report_json, full_report_json, is_unlocked, generation_type, generation_status |
| `leads` | 留资 | id, user_id(FK), assessment_id(FK), name, contact, company, role |
| `share_records` | 转发记录 | id, user_id(FK), assessment_id(FK), share_scene, reward_minutes |
| `follow_notes` | 跟进备注 | id, lead_id(FK), owner, status, remark |
| `admin_users` | 管理员 | id, username(UK), password_hash, role |
| `ai_report_logs` | AI日志 | id, assessment_id(FK), question_id, model, prompt_version, request/response/parsed, diagnosis_tag, report_memory, sales_hint, status, latency_ms |

### 3.3 API 路由表

| Method | Path | Auth | 功能 |
|---|---|---|---|
| POST | `/api/auth/wechat-login` | 无 | 微信登录 → JWT |
| GET | `/api/questions` | 无 | 获取 18 题 + 选项 |
| POST | `/api/assessments` | JWT | 创建测评 |
| POST | `/api/assessments/{id}/answers` | JWT | 提交答案（upsert） |
| POST | `/api/assessments/{id}/complete` | JWT | 完成测评 → 算分 → 后台生成报告 |
| GET | `/api/assessments/{id}/report-status` | JWT | 轮询报告生成状态 |
| GET | `/api/reports/{id}/summary` | 无 | 获取部分报告（公开） |
| GET | `/api/reports/my` | JWT | 我的最新报告 |
| GET | `/api/reports/my/list` | JWT | 报告列表 |
| GET | `/api/reports/{id}/full` | JWT | 完整报告（需解锁） |
| POST | `/api/leads` | JWT | 留资 + 解锁报告 |
| POST | `/api/share-records` | JWT | 记录转发 |
| POST | `/api/wecom/unlock-session` | JWT | 创建企微解锁会话 |
| GET | `/api/wecom/unlock-status/{id}` | JWT | 查询解锁状态 |
| POST | `/api/wecom/customer-added` | SCRM | 企微回调确认 |
| POST | `/api/wecom/mock-unlock` | JWT | 开发环境模拟解锁 |
| POST | `/api/admin/login` | 无 | 管理员登录 |
| GET | `/api/admin/leads` | Admin | 线索列表 |
| GET | `/api/admin/assessments/{id}` | Admin | 测评详情 |
| GET | `/api/admin/ai-report-logs` | Admin | AI 调用日志 |
| POST | `/api/admin/follow-notes` | Admin | 跟进备注 |
| GET | `/health` | 无 | 健康检查 |
| GET | `/health/db` | 无 | 数据库检查 |

### 3.4 Python 后端的独特能力（CloudBase 版未实现）

1. **AI 报告生成**: DeepSeek API 调用 → JSON 解析校验 → 字段完整性检测 → 模板兜底
2. **单题 AI 诊断记忆**: 每题回答后后台静默生成诊断（diagnosis_tag + report_memory + sales_hint），异常不影响主流程
3. **AI 输出净化**: 多层正则清理（内部题号过滤、方括号占位符检测、中英文标点规范化）
4. **规则字段覆盖**: 分数/标签由后端规则计算，AI 只补充诊断文案
5. **JWT 认证体系**: 微信登录 → JWT 签发 → 依赖注入 → 管理员鉴权
6. **Alembic 数据库迁移**: 版本化的 schema 变更管理
7. **管理后台**: HTML 静态页面 + Admin API（线索管理、跟进备注）
8. **转发收益系统**: 转发奖励 10 分钟，累计顾问解读权益
9. **完整的测试覆盖**: 单元测试（评分/模板/校验）+ 集成测试（API/流程）

---

## 四、两套后端的核心差异对比

| 维度 | Python FastAPI | CloudBase 云函数 |
|---|---|---|
| **状态** | 历史版本 · 只读参考 | ✅ 当前使用 |
| **数据库** | MySQL 8.x (SQLAlchemy ORM) | CloudBase NoSQL 文档数据库 |
| **认证** | JWT Token (微信 code → openid → JWT) | 微信原生 OPENID (cloud.getWXContext) |
| **题目数量** | 18 题（固定，无分支） | 15 题（动态分支：has_overseas / no_overseas） |
| **题目存储** | MySQL questions / question_options 表 | JavaScript 常量（questionFlow.js） |
| **评分体系** | 单维度（总分 17-68 → 4 个标签） | **双维度**（feasibility + lead，各 0-80） |
| **报告结构** | V2 结构（summary_report + full_report + sales_followup） | 简化结构（hero + summary_report + full_report） |
| **报告类型** | 客户报告 | 客户报告 + **顾问跟进行报告** |
| **AI 能力** | DeepSeek 完整集成 + 单题诊断记忆 + 模板兜底 | ❌ 仅有模板报告 |
| **前端通信** | HTTP REST（wx.request → localhost:8000） | wx.cloud.callFunction |
| **部署** | Docker → 微信云托管 (CloudBase Run) | 微信云开发云函数 |
| **环境隔离** | .env 文件 + 环境变量前缀 `LB_` | CloudBase 环境 ID |
| **配置管理** | Pydantic Settings（集中式） | 硬编码 + cloudbaserc.json |
| **类型安全** | Python 类型注解 + Pydantic v2 校验 | JavaScript（无类型） |
| **测试** | pytest（单元 + 集成） | Node assert（仅 shared 模块） |
| **数据库迁移** | Alembic 版本化管理 | 无（手工建集合） |
| **后台管理** | admin.html + Admin API | ❌ 未实现 |
| **产品名称** | 罗宾出海分析 Agent | **深度未来** |

---

## 五、架构演进建议

### 5.1 CloudBase 后端的优势
- **零部署成本**: 云函数免运维，推送即部署
- **原生 OpenID**: 无需额外的 JWT 层，微信身份天然可信
- **双报告体系**: 客户版 + 顾问版分离，支持后续的商业闭环
- **动态分支**: 题目流根据用户是否有出海经验分叉，体验更好
- **NoSQL 灵活**: 报告 JSON 结构变更无需 migration

### 5.2 待补全的能力（从 Python 版迁移）
按优先级排序：

1. **P0 — AI 报告生成**: 将 `prompts.py` → `prompts.js`，`report_service.py` → Node.js，接入 DeepSeek API
2. **P0 — 用户系统**: 实现 `users` 集合 + 微信头像昵称获取
3. **P1 — 留资表单**: 将 lead 相关逻辑从 Python 版迁移
4. **P1 — 后台管理/顾问端**: 参考 `API_CONTRACT.md` 的 11 个接口定义
5. **P2 — 文件上传**: 产品目录 PDF/PPT 上传 + 云存储
6. **P2 — 单题 AI 诊断**: 答题过程中静默生成诊断记忆
7. **P2 — 数据库迁移工具**: 引入 collection schema 版本管理

### 5.3 可直接复用的 Python 资产
- `backend/app/services/prompts.py`: DeepSeek Prompt 模板（200+ 行精心设计的 Prompt）
- `backend/app/services/template_report.py`: 4 个标签的完整模板文案
- `backend/tests/fixtures/sample_questions.json`: 18 题种子数据
- `backend/app/services/report_service.py`: AI 输出校验逻辑（`validate_report_fields`）
- `API_CONTRACT.md`: 完整的接口契约定义

---

## 六、文件导航速查

| 关注点 | Python 版位置 | CloudBase 版位置 |
|---|---|---|
| 入口 | [backend/main.py](../backend/main.py) | 各云函数 `index.js` |
| 配置 | [backend/config.py](../backend/config.py) | 硬编码 + `project.config.json` |
| 数据库 | [backend/app/core/database.py](../backend/app/core/database.py) | [cloudfunctions/shared/db.js](../cloudfunctions/shared/db.js) |
| 题目定义 | [backend/tests/fixtures/sample_questions.json](../backend/tests/fixtures/sample_questions.json) | [cloudfunctions/shared/questionFlow.js](../cloudfunctions/shared/questionFlow.js) |
| 评分逻辑 | [backend/app/services/scoring_service.py](../backend/app/services/scoring_service.py) | [cloudfunctions/shared/scoring.js](../cloudfunctions/shared/scoring.js) |
| 模板报告 | [backend/app/services/template_report.py](../backend/app/services/template_report.py) | [cloudfunctions/shared/reportTemplate.js](../cloudfunctions/shared/reportTemplate.js) |
| AI Prompt | [backend/app/services/prompts.py](../backend/app/services/prompts.py) | ❌ 未迁移 |
| API 契约 | — | [API_CONTRACT.md](../API_CONTRACT.md) |
| 迁移方案 | — | [2026-06-17-cloudbase-migration.md](../2026-06-17-cloudbase-migration.md) |

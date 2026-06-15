# 罗宾出海分析 Agent 开发规范

## 行为准则（Karpathy 四原则）

> **注意**：这些准则面向所有任务，倾斜于谨慎而非速度。对简单的任务可酌情略过。

### 1. 先推理再写代码（Think Before Coding）

**不假设、不隐藏困惑、主动暴露权衡。**

写代码前：
- 显式陈述假设。如果不确定，直接问。
- 如果存在多种理解，全部列出——不要悄悄选一个。
- 如果存在更简单的方案，直接说出来。在有必要时 push back。
- 如果有不清楚的地方，停下来。说出哪里困惑，然后问。

### 2. 简洁优先（Simplicity First）

**用最少代码解决问题，不写推测性代码。**

- 不做需求之外的功能。
- 不为只调用一次的代码建抽象层。
- 不加用户没要求的"灵活性"或"可配置性"。
- 不为不可能出现的场景写错误处理。
- 如果写了 200 行，50 行就能搞定——重写。

自问："高级工程师会认为这个过度复杂吗？"如果是，简化它。

### 3. 精准修改（Surgical Changes）

**只改必须改的，只清理你自己造成的烂摊子。**

编辑既有代码时：
- 不要"顺手优化"相邻的代码、注释或格式。
- 不要重构没有坏的东西。
- 遵循已有风格，即使你跟它做法不同。
- 如果发现了无关的 dead code，提出来——不要删。

当你自己的改动制造了孤儿代码时：
- 删除**你自己的改动**造成的未使用 import/变量/函数。
- 不要删除既有的 dead code，除非明确要求。

检验标准：每行改动都应该能直接追溯到你的修改目标。

### 4. 目标驱动执行（Goal-Driven Execution）

**定义成功标准，循环验证直到达标。**

把任务转化为可验证的目标：
- "加校验" → "先写非法输入的测试，再让它们通过"
- "修 bug" → "先写能复现的测试，再让它通过"
- "重构 X" → "确保重构前后测试都通过"

多步骤任务先写简要计划：
```
1. [步骤] → 验证: [检查方式]
2. [步骤] → 验证: [检查方式]
3. [步骤] → 验证: [检查方式]
```

强成功标准让你能独立循环推进。弱标准（"搞搞看能不能跑"）则需要不断拉人澄清。

**四条准则有效的标志：** diff 里不必要的改动变少、因过度复杂导致的返工变少、澄清性问题出现在实现之前而非出错之后。

---

## 项目概述

出海机会测评获客小程序。学员完成 15 道选择题 → 系统算分打标签 → AI 生成评估报告 → 留资解锁完整报告 → 企微转化。详见 [PRD.md](../PRD.md) 和 [TECH_DESIGN.md](../TECH_DESIGN.md)（待创建）。

## 技术栈

- **前端**: 微信小程序原生开发
- **后端**: Python 3.9+ / FastAPI（需 `from __future__ import annotations`）
- **数据库**: MySQL 8.x（SQLAlchemy 2.0 + Alembic）
- **AI**: DeepSeek API（后端统一调用，前端不接触 Key）
- **部署**: 微信云托管（CloudBase Run）+ Docker
- **包管理**: pip / requirements.txt

## 代码风格

- Python 全面使用类型注解（`list[str]` 而非 `List[str]`，`str | None` 而非 `Optional[str]`）
- 数据模型统一用 Pydantic v2 BaseModel
- FastAPI 路由和 AI 调用使用 `async def`；纯计算函数用同步 `def`
- 导入顺序：stdlib → 第三方 → 本项目，各组之间空一行
- 字符串统一用双引号 `"`
- 函数/类只在逻辑不明显时写简短 docstring（不说显而易见的事）

## 架构约束

### 目录结构

```
backend/
├── main.py              # FastAPI 入口，初始化 + 路由挂载
├── config.py            # Pydantic Settings，所有配置集中在此
├── app/
│   ├── api/             # FastAPI 路由（thin，委托给 services）
│   ├── core/            # 数据库连接、依赖注入、中间件
│   ├── models/          # SQLAlchemy ORM 模型（纯数据定义）
│   ├── schemas/         # Pydantic 请求/响应模型
│   └── services/        # 业务逻辑（评分、AI 报告、模板、留资）
│       ├── scoring.py   # 评分规则 + 标签生成
│       ├── ai_report.py # AI 报告生成调用
│       ├── template_report.py  # 模板报告兜底
│       └── lead.py      # 留资逻辑
├── tests/
│   ├── unit/            # 单元测试
│   ├── integration/     # 集成测试
│   └── fixtures/        # 测试数据（JSON）
├── migrations/          # Alembic 迁移文件
└── requirements.txt
```

小程序端由刘澳负责，以下目录他只读不写：

```
miniprogram/
├── pages/
│   ├── index/             # 首页
│   ├── assessment/        # 测评页
│   ├── report-generating/ # 报告生成中
│   ├── report-partial/    # 部分报告
│   ├── lead/              # 留资页
│   ├── report-full/       # 完整报告
│   └── my-report/         # 我的报告
├── components/
├── utils/
└── images/
```

### 层级依赖规则

```
api → services → core, models, schemas, config
```

- **禁止反向依赖**：`models/` 和 `config.py` 不能 import 任何其他业务模块
- **API 层不做业务逻辑**：路由函数只做入参校验和响应返回，具体实现委托给 `services/`
- **评分规则独立**：`scoring.py` 是纯函数模块，不依赖数据库和 AI 服务
- **AI 报告有兜底**：`ai_report.py` 失败后由 `template_report.py` 接管，前端无感知

## 开发工作流（Vibecoding 适配版）

### 每个功能的标准步骤

1. **先 /plan** — 让 AI 列出要改哪些文件、怎么改，你确认后再开始
2. **先测试** — 在 `tests/unit/` 或 `tests/integration/` 中写测试（happy path + 异常 case）
3. **运行测试确认失败（红）**
4. **写最小实现使测试通过（绿）**
5. **运行 /review** — AI 自动审查代码中的 bug 和边界问题
6. **运行 /simplify** — AI 自动清理冗余代码
7. **git diff 审查** — 看完 AI 改了什么再提交
8. **commit** — 按 Git 规范提交

### Claude Code 内置命令用法

| 命令 | 时机 | 作用 |
|------|------|------|
| `/plan` | 写任何代码前 | 先规划再执行 |
| `/review` | 实现完成后 | 审查 bug 和边界 |
| `/simplify` | review 之后 | 清理冗余代码 |
| `/effort high` | 复杂逻辑时 | 提高推理深度 |
| `/compact` | 上下文太长时 | 压缩对话 |

### Skills 使用指南

- **Superpowers** (`using-superpowers`)：完整开发工作流，从头脑风暴到合并
- **planning-with-files** (`planning-with-files-zh`)：跨 session 保持计划不丢失
- **test-driven-development**：按 TDD 流程开发
- **systematic-debugging**：系统化排查问题

## 测试规范

- 单元测试放 `tests/unit/`，集成测试放 `tests/integration/`
- 测试数据放 `tests/fixtures/`（JSON 格式）
- 测试函数命名：`test_<功能>_<场景>`（如 `test_scoring_returns_correct_tag`）
- AI 调用必须 mock，单元测试**绝不消耗** API Token
- 运行测试：`pytest tests/ -v`
- 运行单个模块：`pytest tests/unit/test_scoring.py -v`

### 必须优先测试的对象
1. 评分规则（纯函数，最容易验证）
2. 标签生成逻辑
3. 模板报告拼装
4. AI 输出 JSON 解析校验
5. 留资表单校验

## 编码规则

### 必须遵守

- 所有配置通过 `config.py` 的 `Settings` 类读取，禁止硬编码
- AI 报告输出必须做 JSON 校验 + 字段缺失检测，失败走模板兜底
- AI 输出限制：不承诺收益，不输出确定性合规结论，不编造用户未提供的信息，不使用强否定表达
- 题目、分值、标签全部配置化存在数据库，不硬编码在代码中
- 错误处理：API 层统一返回 `{ "data": ..., "error": ... }` 结构
- 评分规则是纯函数，不依赖数据库连接和 AI 服务

### 禁止事项

- 禁止在 API 路由中写业务逻辑
- 禁止 `from xxx import *`
- 禁止 `print()` 调试，用 `logging` 模块
- 禁止在前端暴露 API Key
- 禁止在 `models/` 目录中写业务逻辑
- 禁止引入 PRD 中未列出的第三方依赖（先讨论）
- 不允许在微信小程序中加入聊天框或自由输入

## AI 报告服务规范

### 调用流程
1. 后端接收 `complete` 请求 → 校验 15 题完整性
2. 评分服务计算总分 + 标签（纯规则，不调 AI）
3. AI 报告服务生成报告（DeepSeek API）
4. JSON 校验通过 → 存入 `reports` 表
5. JSON 校验失败 / API 超时 / 接口错误 → 切模板兜底
6. 前端轮询状态 → 展示报告

### Prompt 管理
- MVP 阶段所有 Prompt 以 Python 字符串常量形式放在 `services/prompts.py`
- 常量命名：`SYSTEM_<功能>`（如 `SYSTEM_SUMMARY_REPORT`、`SYSTEM_FULL_REPORT`）
- Prompt 中动态部分用 `{variable_name}` 占位，通过 `.format()` 注入
- 修改 Prompt 时必须同步更新对应测试

## Git 规范

- 分支命名：`feat/<功能>`（你的分支 `feat/lin-backend`）
- Commit message：`<type>: <简要描述>`
  - type: `feat` | `fix` | `test` | `refactor` | `docs` | `chore`
  - 示例：`feat: 实现评分规则和标签生成`
- commit 前运行 `pytest tests/` 确保不破坏已有测试

## 构建与运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest tests/ -v

# 启动后端（开发）
uvicorn main:app --reload --port 8000

# 数据库迁移
alembic upgrade head
alembic revision --autogenerate -m "描述"

# Docker 构建（部署用）
docker build -t luobin-agent .

# 部署到云托管（需先安装 CloudBase CLI）
# npm install -g @cloudbase/cli
# tcb login
# tcb deploy
```

## 兜底与降级策略

- **AI 生成失败** → 自动切模板报告（`template_report.py`）
- **算法备案不过** → 关闭 AI 开关（`LB_AI_REPORT_ENABLED=false`），全程模板报告
- **微信审核不通过** → 检查定位是否为"测评报告生成"而非"AI 问答"
- **后端超时** → 接口统一返回 `{ "error": "请求超时，请重试" }`
- **部署问题** → 通过云托管控制台查看日志；本地 `uvicorn main:app` 可独立调试

## 部署说明

- **前端（小程序）**：刘澳通过微信开发者工具上传
- **后端（Python）**：通过云托管部署，Dockerfile 在 `backend/Dockerfile`
- **数据库**：使用云开发 TencentDB for MySQL
- **免 ICP 备案**：云托管不需要 ICP 备案，加速上线

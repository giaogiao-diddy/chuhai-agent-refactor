# 罗宾出海分析 Agent

> 出海机会测评获客小程序 — 筛选有出海意向的国内商家，沉淀可跟进线索。

## 项目简介

面向已购买罗宾课程的学员，通过 **15 道选择题** 完成出海准备度测评，系统根据答案计算分数与标签，并生成 AI 评估报告。报告先展示部分内容，学员留资后解锁完整报告，最终通过企业微信承接 1 对 1 报告解读。

**核心链路**：测评 → 部分报告 → 留资 → 完整报告 → 企微转化

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | 微信小程序原生开发 |
| 后端 | Python 3.9+ / FastAPI |
| 数据库 | MySQL 8.x / SQLAlchemy 2.0 / Alembic |
| AI | DeepSeek API（模板报告兜底） |
| 部署 | 微信云托管（CloudBase Run）+ Docker |

## 项目结构

```
luobin-abroad-agent/
├── backend/                     # Python 后端
│   ├── main.py                  # FastAPI 入口
│   ├── config.py                # 全局配置
│   ├── app/
│   │   ├── api/                 # 路由层（6 个模块）
│   │   ├── core/                # 基础设施（DB、依赖注入、中间件）
│   │   ├── models/              # SQLAlchemy ORM 模型（9 张表）
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   └── services/            # 业务逻辑（评分、AI报告、模板、留资）
│   ├── migrations/              # Alembic 迁移文件
│   ├── tests/                   # 测试
│   └── requirements.txt
├── miniprogram/                 # 微信小程序（刘澳维护）
│   └── pages/
│       ├── index/               # 首页
│       ├── assessment/          # 测评页
│       ├── report-generating/   # 报告生成中
│       ├── report-partial/      # 部分报告
│       ├── lead/                # 留资页
│       ├── report-full/         # 完整报告
│       └── my-report/           # 我的报告
├── .claude/
│   └── CLAUDE.md                # AI 开发规范
├── .env.example                 # 环境变量模板
├── PRD.md                       # 产品需求文档
├── TECH_DESIGN.md               # 技术设计文档
└── VIBECODING_BUILD_ORDER.md    # 开发方法论
```

## 快速开始

### 前置条件

- Python 3.9+
- MySQL 8.x（推荐使用云开发 TencentDB）
- DeepSeek API Key
- 微信云托管环境（部署时）

### 1. 本地开发

```bash
cd backend
cp .env.example .env
# 编辑 .env，填入数据库连接、API Key 等信息
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档（Swagger UI）。

### 2. 运行测试

```bash
cd backend
pytest tests/ -v
```

### 3. 部署到云托管

```bash
# 安装 CloudBase CLI
npm install -g @cloudbase/cli

# 登录
tcb login

# 在项目根目录初始化
tcb init

# 部署（自动构建 Docker 镜像并推送）
tcb deploy
```

或通过微信开发者工具：**云开发 → 云托管 → 新建服务 → 上传服务**，选择 `backend/` 目录。

## API 总览

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/wechat-login` | POST | 微信登录 |
| `/api/questions` | GET | 获取题库 |
| `/api/assessments` | POST | 创建测评 |
| `/api/assessments/{id}/answers` | POST | 提交答案 |
| `/api/assessments/{id}/complete` | POST | 完成测评 |
| `/api/assessments/{id}/report-status` | GET | 查询报告状态 |
| `/api/reports/{assessment_id}/summary` | GET | 获取部分报告 |
| `/api/reports/{assessment_id}/full` | GET | 获取完整报告 |
| `/api/leads` | POST | 留资解锁 |
| `/api/share-records` | POST | 转发记录 |
| `/api/admin/leads` | GET | 后台线索列表 |
| `/api/admin/assessments/{id}` | GET | 后台测评详情 |
| `/api/admin/ai-report-logs` | GET | AI 日志 |
| `/api/admin/follow-notes` | POST | 跟进备注 |

## 开发规范

详见 [.claude/CLAUDE.md](.claude/CLAUDE.md) — AI 辅助开发的约束规范。

## 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| ORM 模式 | 同步 SQLAlchemy | 瓶颈在 AI 调用不在 DB，同步代码更简单 |
| AI 编排 | 无框架 | 单一调用模式，引入 LangChain 增加复杂度无收益 |
| 结构化输出 | 手动 Pydantic | DeepSeek 对 Instructor 支持不稳定 |
| 报告兜底 | 模板报告 | AI 失败时无感切换，保证用户体验 |
| 解锁控制 | 后端校验 | 避免前端篡改解锁状态 |

## 许可

内部项目 — NingBoDeepFuture

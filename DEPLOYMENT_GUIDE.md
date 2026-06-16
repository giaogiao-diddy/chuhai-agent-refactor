# 云端部署手册 — 微信云托管（CloudBase Run）

> 本文供 Claude Code 执行会话逐步骤执行。
> 目标：将 `backend/` 部署到微信云托管，小程序可以 HTTPS 访问后端 API。

---

## 前置检查

```bash
# 1. 确认 Python 版本
python3 --version   # 应为 3.9+

# 2. 确认 Node.js 可用（如果没有，跳到步骤 A）
node --version      # 应为 v22+
npx --version

# 3. 确认项目目录
cd /Users/lkh/Desktop/罗宾出海Agent
ls backend/Dockerfile backend/.dockerignore  # 两者都应存在
```

---

## 步骤 A：安装缺少的工具（如果需要）

如果 `node` 或 `npx` 命令不可用：

```bash
# Node.js 已经安装在 ~/.local/ 下，只需要加到 PATH
export PATH="$HOME/.local/bin:$PATH"
node --version     # 验证
npx --version      # 验证
```

如果 Docker 未安装：

```bash
# 安装 Docker Desktop for Mac (ARM64)
# 手动下载安装包：https://desktop.docker.com/mac/main/arm64/Docker.dmg
# 或者用 Homebrew（如果装过）：
# brew install --cask docker
```

---

## 步骤 B：安装 CloudBase CLI

```bash
export PATH="$HOME/.local/bin:$PATH"

# 安装（如果之前没装过）
npm install -g @cloudbase/cli

# 登录 — 会弹出浏览器窗口，用微信扫码即可
tcb login
```

---

## 步骤 C：在微信开发者工具中准备环境

打开**微信开发者工具** → 进入小程序项目 → 左侧栏点**云开发**：

```
1. 如果未开通云开发 → 点击「开通」，选择「按量计费」
2. 记下左上角的环境 ID，例如：luobin-1a2b3c
3. 进入「云托管」标签 → 确认状态为「已开通」
4. 进入「数据库」标签 → 新建 → 选择「MySQL」
   - 记下内网地址：xxx.sql.tencentcdb.com
   - 记下端口：3306
   - 记下用户：root
   - 记下密码（自己设置一个）
   - 数据库名：luobin_agent
```

> **重要**：数据库选**云开发 MySQL**，**不是**「文档型数据库」。否则 SQLAlchemy 无法连接。

---

## 步骤 D：配置云托管环境变量

两种方式任选其一：

**方式 1 — 微信开发者工具**

```
云开发 → 云托管 → 环境变量 → 新增
```

**方式 2 — CloudBase CLI**

```bash
tcb env:set \
  LB_DB_HOST=xxx.mysql.tencentcdb.com \
  LB_DB_PORT=3306 \
  LB_DB_USER=root \
  LB_DB_PASSWORD=你的数据库密码 \
  LB_DB_NAME=luobin_agent \
  LB_LLM_API_KEY=sk-你的DeepSeekKey \
  LB_JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))") \
  LB_WX_APPID=你的小程序AppID \
  LB_WX_SECRET=你的小程序AppSecret
```

---

## 步骤 E：部署后端到云托管

```bash
cd /Users/lkh/Desktop/罗宾出海Agent/backend
export PATH="$HOME/.local/bin:$PATH"

# 初始化云托管项目（第一次）
tcb init
# 选择：微信云托管 → 已有环境 → 选择你的环境 → 其他语言（Docker）

# 部署
tcb deploy
```

**部署过程**（约 3-8 分钟）：
1. 构建 Docker 镜像 → 解决依赖
2. 推送镜像到云托管仓库
3. 创建/更新云托管服务
4. 分配 HTTPS 域名

**部署成功后你会看到**：
```
✓ 部署成功
  访问地址：https://xxx-xxx.ap-shanghai.run.tcloudbase.com
```

记下这个地址。

---

## 步骤 F：初始化数据库（建表 + 种子数据）

### F1. 远程执行 Alembic 迁移

```bash
# 在云托管容器中运行（通过 CloudBase CLI）
tcb run "cd /app && alembic upgrade head"
```

### F2. 种子题目数据

在微信开发者工具中：
```
云开发 → MySQL → 打开数据库管理 → SQL 执行
```

执行种子 SQL（将 `sample_questions.json` 中的 15 道题目插入 `questions` 和 `question_options` 表）。

或者通过 CloudBase CLI 远程运行种子脚本：

```bash
# 写一个种子脚本（如果后端有这个文件的话）
# 或直接通过 API 传数据
curl -X POST https://xxx.ap-shanghai.run.tcloudbase.com/api/admin/seed-questions
```

---

## 步骤 G：配置小程序白名单

```
微信公众平台 (mp.weixin.qq.com) →
  开发管理 →
    开发设置 →
      request 合法域名 →
        添加：https://xxx.ap-shanghai.run.tcloudbase.com
```

> ⚠️ 云托管**不会**自动把域名加入白名单，这一步必须手动做。

---

## 步骤 H：验证部署

```bash
# 1. 健康检查
curl https://xxx.ap-shanghai.run.tcloudbase.com/health
# 预期：{"status": "ok"}

# 2. 获取题库
curl https://xxx.ap-shanghai.run.tcloudbase.com/api/questions
# 预期：返回 15 道题目

# 3. 微信登录（测试用，用 mock code）
curl -X POST https://xxx.ap-shanghai.run.tcloudbase.com/api/auth/wechat-login \
  -H "Content-Type: application/json" \
  -d '{"code": "test_code"}'
# 预期：返回 {"user_id": x, "token": "eyJ...", "is_new": true}

# 4. 完整 Swagger 文档
open https://xxx.ap-shanghai.run.tcloudbase.com/docs
```

---

## 故障排查

| 症状 | 可能原因 | 解决 |
|------|---------|------|
| `tcb login` 失败 | 未装 CloudBase CLI | 回到步骤 B |
| `docker build` 失败 | Docker 未运行 | 启动 Docker Desktop |
| 部署后访问 502 | 容器启动失败 | 云托管控制台 → 查看日志 |
| 数据库连接失败 | 环境变量未设 | 检查步骤 D，确保 `LB_DB_*` 都已配置 |
| `/api/questions` 返回空 | 未种子题目 | 执行步骤 F2 |
| 小程序请求失败 | 域名未加白名单 | 执行步骤 G |
| 云托管平台没有 MySQL 选项 | 选错了数据库类型 | 新建数据库时选「MySQL」不是「文档型」 |

---

## 附：给刘澳的联调备忘

联调时把小程序的 `wx.request` 基础 URL 改为：

```javascript
const BASE_URL = "https://xxx.ap-shanghai.run.tcloudbase.com"
```

接口调用示例：

| 接口 | 前端调用 |
|------|---------|
| 微信登录 | `POST /api/auth/wechat-login` — 传 `{code: wx.login()返回的code}` |
| 获取题目 | `GET /api/questions` — 无需参数 |
| 创建测评 | `POST /api/assessments` — Header 带 JWT |
| 提交答案 | `POST /api/assessments/{id}/answers` — 传 `{question_id, option_id}` |
| 完成测评 | `POST /api/assessments/{id}/complete` — 无需参数 |
| 轮询状态 | `GET /api/assessments/{id}/report-status` — 每 1.5s 一次 |
| 部分报告 | `GET /api/reports/{assessment_id}/summary` |
| 留资 | `POST /api/leads` — 传 `{name, contact, company, role}` |
| 完整报告 | `GET /api/reports/{assessment_id}/full` — 需已留资 |
| 转发 | `POST /api/share-records` — 传 `{assessment_id, share_scene}` |
| 我的报告 | `GET /api/reports/my` — 返回最近一次报告 |

JWT 存储在本地，后续所有请求 Header 都携带：`Authorization: Bearer <token>`

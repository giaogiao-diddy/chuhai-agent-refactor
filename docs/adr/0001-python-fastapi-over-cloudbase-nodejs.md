# 0001-python-fastapi-over-cloudbase-nodejs

## 决策：Agent 对话链路从 CloudBase 云函数 Node.js 迁移到 Python FastAPI 后端

**背景**：项目进入 Agent 对话阶段后，CloudBase 云函数暴露出三个致命瓶颈：
1. 云函数 20s 硬时限，无法承载 AI 报告生成（需 60s+）
2. `wx.cloud.callFunction` 不支持 SSE 流式返回，前端用 `setInterval` 30ms 假打字机伪装
3. 微信小程序禁止聊天框/自由输入，Agent 对话页存在合规风险

**决策**：将 Agent 链路（startConversation / continueConversation / finishConversation）从 CloudBase Node.js 迁移到独立部署的 Python FastAPI 后端。

**原因**：
- Python 拥有最完整的 AI SDK 生态（DeepSeek SDK、流式输出、Function Calling）
- FastAPI 原生支持 StreamingResponse，可实现真正的 SSE
- 独立部署不受云函数 20s 限制
- Agent 对话页可以通过 Web 端或独立 App 承载，不受微信审核约束
- 旧 18 题固定问卷链路（submitAnswer / completeAssessment）保留在 CloudBase，作为微信小程序获客入口

**后果**：
- 仓库将同时存在 Node.js（旧链路）和 Python（Agent 链路）两套代码
- 需要独立的服务器/容器部署 Python 后端（非 CloudBase 云函数）
- 前端需要新增 Web 端或独立 App 承载 Agent 对话页
- 两套系统共享 CloudBase NoSQL 数据库或迁移到 MySQL

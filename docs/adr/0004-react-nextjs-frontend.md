# 0004-react-nextjs-frontend

## 决策：React + Next.js + 组件库作为前端技术栈

**背景**：Web 应用需要企业级 UI，开发者前端经验有限。需要选择 AI 辅助友好、生态成熟、组件库丰富的前端框架。

**决策**：使用 React 19 + Next.js（App Router）+ 组件库。

**原因**：
- React 生态中 AI 辅助开发最成熟（Claude/GPT 对 React 代码生成质量最高）
- Next.js App Router 支持 SSE 流式、Server Actions、API Routes，与 Python 后端互补
- shadcn/ui 或 Mantine 提供企业级组件库，不必从零写 UI
- 单人开发可以在 Next.js 中同时处理前端和后端桥接层（BFF）

**后果**：
- 需要学习 React/JSX/Next.js 基础概念（但 AI 可以辅助大部分编码）
- 需要独立部署前端（CloudBase 静态托管或 Node.js 容器）
- 技术栈从前端到后端：Next.js → FastAPI → MySQL

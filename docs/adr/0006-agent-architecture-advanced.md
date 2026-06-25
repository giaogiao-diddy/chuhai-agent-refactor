# 0006-agent-architecture-advanced

## 决策：采用 SSE 流式 + 向量 RAG + 多 Agent 协作架构

**背景**：旧 CloudBase 架构存在三个产品级缺陷：
1. 假打字机伪装流式（setInterval 30ms）
2. 关键词正则 RAG（命中率靠运气）
3. 单一大 Prompt 对话（不可控、难调试）

**决策**：Python 版 Agent 采用三层企业级架构：

### 一、SSE 真流式对话
- FastAPI `StreamingResponse` + DeepSeek `stream=True`
- 前端 `EventSource` 逐 token 渲染
- 替代假打字机，用户感知延迟从 3-8s → 首 token < 1s

### 二、向量化 RAG
- 使用 text-embedding 模型将行业知识库向量化
- pgvector 存储 + 余弦相似度检索
- 召回精度从"关键词碰运气"升级为语义匹配
- 支持混合检索：向量相似度 + 行业标签过滤 + 目标市场加权

### 三、多 Agent 协作（LangGraph）
- **对话 Agent**：DeepSeek，负责自然语言对话 + 槽位提取 + Function Calling
- **报告 Agent**：DeepSeek，基于完整槽位 + RAG 上下文生成诊断报告
- **审计 Agent**：规则引擎 + 轻量 LLM，校验报告结构/违禁词/字数，不合格打回重写
- 状态图由 LangGraph StateGraph 管理，替代手写 if-else 状态机

**后果**：
- 开发周期显著增加（约 2-3 倍）
- 需要 pgvector 扩展或独立向量数据库
- LangGraph 引入额外的学习成本和依赖
- DeepSeek API 调用次数增加（审计反馈循环），成本上升约 30-50%

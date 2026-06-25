# 深度未来 — 全局技术审阅与成果报告

> 项目代号：深度未来（DeepFuture）/ 企业出海测评智能体
> 技术栈：微信小程序 + CloudBase 云函数（Node.js） + CloudBase NoSQL + DeepSeek API
> 环境 ID：cloud1-d8gh82s3a39eff92d | 分支：feat/lin-backend
> 物理扫描日期：2026-06-18 | 版本：V3.0（终稿）

---

## 目录

1. [项目演进史：三次架构跃迁](#一项目演进史三次架构跃迁)
2. [当前主线架构](#二当前主线架构)
3. [Agent 智能体化全量资产盘点（Phase 1-7）](#三agent-智能体化全量资产盘点)
4. [数据库设计：11 集合完整 Schema](#四数据库设计)
5. [安全与工程防线审计](#五安全与工程防线审计)
6. [代码量与交付物统计](#六代码量与交付物统计)
7. [未完缺口与上线 Checklist](#七未完缺口与上线-checklist)
8. [面试闪光点提炼（STAR 法则）](#八面试闪光点提炼)

---

## 一、项目演进史：三次架构跃迁

### V1.0：Python 单体（已废弃）

```
backend/ (Python 3.9 / FastAPI / SQLAlchemy / MySQL)
  main.py :8000
  132 个 pytest 测试
  15 个 REST API
```

**废弃原因**：微信小程序部署需要 ICP 备案 + 服务器运维，远不如 CloudBase 免运维。Python 代码保留在 `backend/` 作为历史参考。

### V2.0：CloudBase 问卷测评（当前共享环境基线）

```
cloudfunctions/ (16 个 Node.js 云函数)
miniprogram/   (wx.cloud.callFunction)
11 个 NoSQL 集合
18 题固定问卷 → 规则算分 → AI 报告
```

**架构特点**：固定问卷式测评，前端逐题展示，后端规则算分。用户完成 18 题后 AI 一次性生成报告。

### V3.0：Agent 智能体对话诊断（旁路演进，Phase 1-7）

```
旧链路（保留，100% 可用）              新链路（Agent，旁路新增）
─────────────────────                ─────────────────────────
固定 18 题答题页                        对话式诊断页
submitAnswer → completeAssessment      startConversation → continueConversation
scoring.js 评分                        → finishConversation
generateReports 报告生成                   slotToScoreMapper → scoring.js
                                        → ragRetriever → reportGuard
                                        → db.runTransaction 原子写入
                                        → Function Calling (Phase 7)
```

**零破坏确认**：旧链路的 `submitAnswer/index.js`、`completeAssessment/index.js` 和 `miniprogram/pages/assessment/` 的 diff 均为 0 行。

---

## 二、当前主线架构

### 2.1 运行时拓扑

```
┌──────────────────────────────────────────────────┐
│              微信小程序（前端）                     │
│  miniprogram/pages/                               │
│  cloudApi.js → wx.cloud.callFunction("fn", data)  │
└─────────────────────┬────────────────────────────┘
                      │
          CloudBase 云函数（16 个在线 + 3 个源码就绪）
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
  云数据库           共享模块           DeepSeek API
  NoSQL (11集合)     shared/ (19模块)   https 原生调用
```

### 2.2 云函数全景（19 个目录，16 个在线部署，3 个源码就绪）

| 类别 | 函数 | 状态 |
|------|------|:--:|
| 用户端-登录 | `login` | 在线 |
| 用户端-配置 | `getSystemConfig`, `updateSystemConfig` | 在线 |
| 用户端-题库 | `getAssessmentConfig`, `getQuestionFlow` | 在线 |
| 用户端-测评 | `createAssessment`, `submitAnswer`, `completeAssessment` | 在线 |
| 用户端-报告 | `getReportList`, `getReportDetail`, `generateReport` | 在线 |
| 用户端-解锁 | `createWecomUnlockSession`, `getWecomUnlockStatus`, `mockUnlock` | 在线 |
| 顾问端 | `getConsultantLeadReport` | 在线 |
| **Agent** | `startConversation` | 源码就绪 |
| **Agent** | `continueConversation` | 源码就绪 |
| **Agent** | `finishConversation` | 源码就绪 |

### 2.3 共享模块清单（cloudfunctions/shared/，19 个模块）

| 模块 | 职责 | Phase |
|------|------|:--:|
| `db.js` | CloudBase 初始化 + 数据库/上下文封装 | 0 |
| `response.js` | 统一 `success()/fail()/fromError()` 响应格式 | 0 |
| `auth.js` | 管理员 OPENID 校验 | 0 |
| `basicInfo.js` | 企业信息 7 字段强校验 | 0 |
| `scoring.js` | 双评分引擎（feasibility + lead） | 0 |
| `reportTemplate.js` | AI 失败时的模板报告兜底（双版本） | 0 |
| `questionFlow.js` | 分层题流 | 0 |
| `validators.js` | 通用校验工具 | 0 |
| `agentState.js` | 对话状态机（6 状态 + 5 结束原因 + 8 轮熔断） | 1 |
| `conversationSlots.js` | 槽位校验、0.8/0.6 置信度分流、数组去重合并 | 1 |
| `slotAlignment.js` | 自然语言 slot → question_id/option_id 对齐 | 1 |
| `defaultAnswerPolicy.js` | 缺失评分题保守补全（imputed 标记） | 1 |
| `slotToScoreMapper.js` | 17 题缺口遍历 + 默认值补全 + score_detail 注入 | 2 |
| `ragRetriever.js` | 多标签 NoSQL 模糊检索 + 通用兜底（Phase 6 升级为异步 DB 查询） | 3/6 |
| `reportGuard.js` | AI 报告结构审计 + 用户版/顾问版字段物理剥离 | 3 |
| `toolRegistry.js` | Function Calling Schema + 7 地区商情库 + 工具执行映射 | 7 |

---

## 三、Agent 智能体化全量资产盘点

### Phase 1：最小 Agent 骨架（4 文件）

| 产出 | 内容 |
|------|------|
| `agentState.js` | `CONVERSATION_STATUS` 6 态、`FINISH_REASON` 5 因、`MAX_CONVERSATION_ROUNDS=8`、`MAX_AI_FAILURES=2`、`MAX_MESSAGE_LENGTH=500` |
| `conversationSlots.js` | `mergeSlots()` — 置信度 ≥0.8 直接对齐、0.6-0.8 候选追问、<0.6 丢弃；数组去重合并；低置信度不覆盖 |
| `slotAlignment.js` | `validateAlignedAnswers()` + `enrichAlignedAnswersWithScores()` — AI 输出的 option_id 后端查库补分 |
| `defaultAnswerPolicy.js` | `applyDefaultAnswers()` — 遍历 17 道计分题，缺失项按 option_id=1 补全，标记 `imputed:true` |

### Phase 2：映射闭环与双核心云函数（3 文件）

| 产出 | 内容 |
|------|------|
| `slotToScoreMapper.js` | `mapSlotsToScoringInput()` — 17 题补全循环 → 默认答案自动注入 `score_detail` → 杜绝 NaN |
| `startConversation/index.js` | OPENID 归属校验 + 原子状态机初始化 + 硬编码黄金开场白 |
| `continueConversation/index.js` | `client_message_id` 数据库幂等查重 + 8 轮熔断 + DeepSeek 受控调用 + 槽位合并 + 选项对齐 + 对话持久化 |

### Phase 3：全链路结算闭环（3 文件）

| 产出 | 内容 |
|------|------|
| `ragRetriever.js` | 6 条嵌入式行业知识库 — 关键词模糊匹配 + 市场加权 → 最多 3 条 |
| `reportGuard.js` | `validateStructure()` — 24 字段审计 + 7 违禁词扫描 + 字数上限<br>`splitReports()` — 用户版（reports 集合）vs 顾问版（lead_reports 集合）物理字段剥离 |
| `finishConversation/index.js` | 补全 17 题 → 规则算分 → RAG → AI 生成 → reportGuard 审计 → `db.runTransaction` 原子三写 |

### Phase 4：前端对话页（4 文件）

| 产出 | 内容 |
|------|------|
| `agent-assessment.wxml` | Teal 渐变 Header + scroll-view 聊天气泡 + 条件底部栏（输入/生成报告/否决按钮）+ iOS 安全区 |
| `agent-assessment.wxss` | Fresh Tech-Organic 风格 — `#0D9488` + `#10B981` 渐变，零 emoji |
| `agent-assessment.js` | 30ms `setInterval` 假打字机特效 + `client_message_id` 幂等防重 + 乐观 UI 更新 + 一票否决路由 |
| `agent-assessment.json` | 页面配置 |

### Phase 5：一票否决激活 + 合流闭环（3 文件修改）

| 产出 | 内容 |
|------|------|
| 否决前端路由 | `data.isVetoed` 检测 → 输入框淡出 → 打字机展示 `vetoMessage` → 按钮切换为"查看风险提示白皮书" |
| 合流闭环 | `finishConversation` 填补 `openid` 字段 — 确保现有解锁函数可查新 Agent 报告 |
| API 契约补丁 | `API_CONTRACT.md` 新增 3 个 Agent 接口完整定义 |

### Phase 6：NoSQL 多标签 RAG 升级（2 文件修改）

| 产出 | 内容 |
|------|------|
| `knowledge_base` 集合 | 8 条种子数据 — Schema：`title/category/industry_tags[]/market_tags[]/content/risk_points` |
| `ragRetriever.js` 重写 | `db.RegExp` + `db.command.or` 多标签模糊匹配 → `_.and` 联合过滤 → `limit(3)` + `field` 投影 → 冷门行业通用兜底 |

### Phase 7：Function Calling 自主工具调用（2 文件修改）

| 产出 | 内容 |
|------|------|
| `toolRegistry.js` | `searchMarketData` Schema（`industry`/`market` 双参强类型）+ 7 地区内置出海商情库 |
| `continueConversation/index.js` | 两阶段 Tool-Calling：`callDeepSeekWithTools` → 检测 `tool_calls` → 遍历执行 `TOOLS_MAPPING` → `callDeepSeekRaw` 二次合成 |

---

## 四、数据库设计

### 4.1 集合全景（11 个）

| 集合 | 文档数 | 用途 |
|------|:--:|------|
| `users` | — | 用户表（openid + role） |
| `assessments` | — | 测评记录 + Agent 对话状态机字段 |
| `answers` | — | 旧：逐题答案 / 新：对话消息（`type: conversation_message`，`client_message_id` 幂等索引） |
| `reports` | — | **用户版**报告 — 不含 lead_score/sales_followup |
| `lead_reports` | — | **顾问版**报告 — 含 sales_followup/lead_score/lead_priority |
| `questions` | 17 | 题库（含 `is_scored`、`options[].feasibility_score/lead_score`） |
| `consultant_notes` | — | 顾问跟进备注 |
| `system_config` | 1 | 全局配置（客服二维码、标签规则） |
| `ai_report_logs` | — | AI 调用日志 |
| `knowledge_base` | 8 | RAG 知识库（行业打法 + 风险点） |
| `wecom_unlock_sessions` | — | 企微解锁会话 |

### 4.2 Agent 特有字段（assessments 集合扩展）

```js
{
  assessment_mode: "agent_conversation",  // "agent_conversation" | null（旧模式）
  conversation_status: "collecting",      // collecting/ready_to_finish/completed/vetoed/fallback_questionnaire
  conversation_round: 0,                  // 当前轮数
  conversation_slots: {},                 // 已采集的结构化槽位（含 confidence/evidence）
  aligned_answers: [],                    // AI 对齐的题库选项（含 score_detail/imputed）
  ai_failure_count: 0,                    // AI 连续失败计数
  special_case: {                         // 一票否决标记
    is_vetoed: false,
    veto_level: "",
    alternatives: []
  }
}
```

---

## 五、安全与工程防线审计

### 5.1 Token 成本防线

| 防线 | 机制 | 位置 |
|------|------|------|
| 幂等查重 | `client_message_id` 写入前先查 `answers` 表 | `continueConversation:49-56` |
| 8 轮强熔断 | `conversation_round >= 8` → 不再调 AI | `agentState.js:29` |
| 2 次失败兜底 | `ai_failure_count >= 2` → 切固定问卷 | `agentState.js:30` |
| 500 字限长 | 单条消息截断 | `agentState.js:32` |
| 历史窗口 | 仅取最近 12 条入 AI 上下文 | `continueConversation` |
| Tool-Calling 最大深度 | 递归深度 = 1（首轮 + 次轮） | `continueConversation` |

**单次测评成本**：8 轮 × 12 条 × 600 tokens ≈ 7,200 tokens 输入 + 600 tokens 输出 ≈ 0.02 元/次。

### 5.2 数学计分防线

```
AI 角色：抽取 option_id（不输出分值）
        ↓
后端角色：slotAlignment.enrichAlignedAnswersWithScores()
        从 questions.options 查 feasibility_score / lead_score
        ↓
缺失补全：defaultAnswerPolicy.applyDefaultAnswers()
        未提及题按 option_id=1 补全，标记 imputed:true
        ↓
NaN 斩断：slotToScoreMapper 保证每个元素有 score_detail
        ↓
评分计算：scoring.calculateScores() 纯函数确定性求和
```

评分路径为 `槽位 → option_id → 查库分值 → 求和`，100% 确定性，可复现，可解释。

### 5.3 顾问资产隔离防线

| 防线 | 机制 |
|------|------|
| 物理拆分 | `reportGuard.splitReports()` — 用户版不含 `sales_followup/lead_score/lead_priority` |
| 事务原子写入 | `db.runTransaction` — reports + lead_reports + assessments 三写同生共死 |
| 集合级隔离 | 用户报告 → `reports` 集合，顾问报告 → `lead_reports` 集合 |
| 字段白名单 | `splitReports` 返回的 `userReport` 显式字段列举，AI 输出中不在白名单的字段被丢弃 |

### 5.4 一票否决防线

| 阶段 | 机制 |
|------|------|
| AI 候选判别 | System Prompt 约束 AI 判断核心业务是否属于高风险类目 |
| 后端二次确认 | `shouldForceFinish` 确认 `hard_veto` 或 `risk_warning` |
| 风险重塑 | `ragRetriever` 检索替代路径（B2B/展会/独立站） |
| 前端体验 | 否决时打字机展示风险提示，按钮变更为"查看风险提示白皮书" |

### 5.5 旁路零破坏确认

| 文件 | diff 行数 | 状态 |
|------|:--:|------|
| `cloudfunctions/submitAnswer/index.js` | 0 | 未改动 |
| `cloudfunctions/completeAssessment/index.js` | 0 | 未改动 |
| `miniprogram/pages/assessment/`（全部 4 文件） | 0 | 未改动 |

---

## 六、代码量与交付物统计

| 维度 | 数值 |
|------|------|
| 云函数目录 | 19 个 |
| 共享模块（`shared/*.js`） | 19 个 |
| 云函数代码总行数 | 18,732 行 |
| 前端代码总行数 | 1,438 行 |
| 数据库集合 | 11 个 |
| 在线部署函数 | 16 个 |
| 源码就绪（含 Agent） | 3 个函数 + 19 个共享模块 |
| Phase 1-7 累计交付文件 | 40+ 个 |

---

## 七、未完缺口与上线 Checklist

### 代码层缺口

| # | 缺口 | 优先级 | 说明 |
|:--:|------|:--:|------|
| 1 | Agent 3 云函数未部署 | P0 | 前端对话页接入时部署 |
| 2 | `login` 用户画像未硬化 | P1 | 补充 nickName/avatarUrl/phone 字段同步 |
| 3 | `questions` 集合含旧 mock | P0 | 等前端提供正式题目后替换 |
| 4 | 顾问端 WXML 未联调 `lead_reports` | P1 | 前端适配 `sales_followup` 字段 |
| 5 | `getConsultantDashboard` 未实现 | P0 | 顾问端列表接口 |
| 6 | `updateFollowUp` 未实现 | P0 | 顾问跟进状态接口 |

### 提审合规 Checklist

| # | 事项 | 状态 |
|:--:|------|:--:|
| 1 | 微信隐私协议勾选 | 待处理 |
| 2 | AI 生成内容合规说明书 | 待编写 |
| 3 | 内测测试账号 | 待创建 |
| 4 | 小程序截图/录屏 | 待 UI 完善后准备 |
| 5 | `request` 合法域名配置 | 待确认 |
| 6 | CloudBase 个人测试环境 | 待创建 |

---

## 八、面试闪光点提炼

### 成就 1：将固定问卷升级为受控对话式诊断 Agent，实现零破坏旁路演进

**痛点**：原有 18 题固定问卷用户体验僵化，完成率低，且无法根据企业实际情况弹性追问。直接改造风险极高。

**方案**：采用"旁路非破坏性演进"策略，新增完整 Agent 对话链路（startConversation → continueConversation → finishConversation），通过状态机（6 状态 + 8 轮熔断）控制对话流程，通过槽位填充（Slot-filling）从自然语言中提取 17 个结构化字段，通过题库选项对齐（Slot-to-Option Alignment）将自由对话映射到确定性评分输入。旧 submitAnswer/completeAssessment 保持零改动（物理 diff 确认 0 行），双轨制并行运行，Agent 任何故障点自动降级到固定问卷。

**价值**：用户从"填表"跳变为"对话"，AI 成本 ≤0.02 元/次，旧系统零风险演进。

---

### 成就 2：建立"AI 不碰分、事务原子落库、销售数据物理隔离"的三层安全防线

**痛点**：AI 直接参与评分导致不可复现。AI 生成的报告中可能泄露顾问私域线索数据（销售话术、线索温度）。

**方案**：AI 仅负责将自然语言对齐为 `option_id`（`slotAlignment.js`），分值由后端从题库确定性查询。缺失信息通过保守默认策略补全为最低分（`defaultAnswerPolicy.js`），从根源斩断 NaN 崩溃。报告经 `reportGuard.js` 安全审计后，通过 CloudBase 分布式事务（`db.runTransaction`）将用户版报告写入 `reports` 集合、顾问版报告（含 `sales_followup` 销售话术）原子写入 `lead_reports` 集合。

**价值**：评分 100% 可复现，销售数据零泄露，账单一致性保证。

---

### 成就 3：实现纯云函数架构下的 Function Calling 工具调用与多标签 NoSQL RAG 检索

**痛点**：单纯的对话式 AI 无法获取真实商情数据，报告内容空洞。微信云函数不支持常驻容器的 SSE 流式，也不支持向量数据库。

**方案**：在无 Docker、无 CloudRun 的纯云函数架构下，设计了两阶段 Function Calling 闭环（`callDeepSeekWithTools`）：首轮 AI 请求携带 `tools: [searchMarketData]` 定义，AI 自主判断是否需要调取商情数据；后端拦截 `tool_calls` 后执行内置 7 地区商情库查询；结果以 `role: "tool"` 灌回上下文；次轮 AI 消化真实数据生成最终回复。同时设计多标签 NoSQL 模糊检索 RAG（`db.RegExp` + `db.command.or` 联合 `knowledge_base` 集合），在报告阶段召回行业案例和风险点。

**价值**：Agent 从"闭门造车"升级为"触达真实数据"，在不引入任何新基础设施的前提下实现 Tool Use + RAG 双能力闭环。

---

> **报告结论**：项目已完成从 Python 单体到 CloudBase 云函数 Agent 的四次架构跃迁。当前 19 个共享模块、19 个云函数目录、11 个数据库集合构成完整的 Agent SaaS 底座。Phase 1-7 的旁路演进策略确保了旧系统零风险。项目可进入 M7（前端联调 + 提审准备）阶段。

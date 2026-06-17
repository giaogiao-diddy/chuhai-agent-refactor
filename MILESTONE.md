# 开发里程碑计划

> 当前日期：2026-06-17 | 项目：深度未来 — 企业出海测评小程序

---

## 里程碑总览

| # | 里程碑 | 开始 | 预期完成 | B | A | 状态 |
|:--:|------|------|------|:--:|:--:|:--:|
| 0 | 环境搭建 | 6/17 | 6/17 | ✅ | ✅ | 完成 |
| 1 | 数据模型对齐 | 6/17 | 6/18 | 🔴 | — | 进行中 |
| 2 | 基础接口（login + 配置） | 6/18 | 6/18 | 🔴 | — | 待开始 |
| 3 | 题库 + 测评配置 | 6/18 | 6/19 | 🔴 | 🔴 | 待开始 |
| 4 | 答题 + 评分 | 6/19 | 6/20 | 🔴 | 🔴 | 待开始 |
| 5 | 报告生成（AI + 模板） | 6/20 | 6/22 | 🔴 | — | 待开始 |
| 6 | 解锁 + 顾问端 | 6/22 | 6/23 | 🔴 | 🔴 | 待开始 |
| 7 | 联调 + 验收 | 6/23 | 6/25 | 🔴 | 🔴 | 待开始 |

---

## 详细任务

### M0：环境搭建 ✅ 完成

| 任务 | B | A | 状态 |
|------|:--:|:--:|:--:|
| CloudBase 环境 | ✅ | — | cloud1-d8gh82s3a39eff92d |
| 8 个数据库集合 | ✅ | — | 已创建 |
| 小程序框架 | — | ✅ | miniprogram/ |
| cloudApi.js 封装 | ✅ | ✅ | wx.cloud.callFunction |
| API_CONTRACT.md | ✅ | — | 11 个接口已定义 |

---

### M1：数据模型对齐 🔴 进行中

| 任务 | B | A | 交付物 |
|------|:--:|:--:|------|
| 创建 `questions` 集合 | 🔴 | — | 题目数据结构设计 |
| 创建 `consultant_notes` 集合 | 🔴 | — | |
| 创建 `system_config` 集合 | 🔴 | — | |
| 定稿 questions 字段结构 | 🔴 | 🔴 | API_CONTRACT.md §2 |
| 定稿 answers 提交格式 | 🔴 | 🔴 | API_CONTRACT.md §4 |
| 定稿报告结构（brief/full/sales） | 🔴 | 🔴 | API_CONTRACT.md §5 |

**A 需要知道的：**
- 每道题的 JSON 结构（type/options/scoringRules/branch）
- 答案提交格式（questionCode + value）
- 报告分段的字段名

---

### M2：基础接口 🔴 待开始

| 任务 | B | A | 云函数 |
|------|:--:|:--:|------|
| `login` — 微信登录返回角色 | 🔴 | — | 待写 |
| `getSystemConfig` — 客服二维码+标签 | 🔴 | — | 待写 |
| `updateSystemConfig` — 管理员配置 | 🔴 | — | 待写 |

**A 需要知道的：**
- `login` 返回 `{ user, isNewUser }`，`user.role` 决定能否进顾问端
- `getSystemConfig` 返回客服二维码 URL

---

### M3：题库 + 测评配置 🔴 待开始

| 任务 | B | A | 交付物 |
|------|:--:|:--:|------|
| 题目 json 数据准备 | — | 🔴 | questions 种子数据 |
| 评分规则配置 | 🔴 | — | 每道题 overseas + consultant 分值 |
| `getAssessmentConfig` | 🔴 | — | 返回题目 + 评分规则 + 标签表 |
| `createAssessment` | 🔴 | — | 保存企业信息 + 创建测评 |

**A 需要知道的：**
- `getAssessmentConfig` 返回的题目顺序 = 展示顺序
- 题目 `branch` 字段控制分层显示（`all`/`experienced`/`newbie`）
- 前端不需要展示 `scoringRules`，只展示 `title`/`description`/`options`

---

### M4：答题 + 评分 🔴 待开始

| 任务 | B | A | 交付物 |
|------|:--:|:--:|------|
| 答题页分层逻辑 | — | 🔴 | 根据 branch 展示不同题目 |
| 答案保存 | 🔴 | — | 每答一题实时保存 |
| `submitAssessment` | 🔴 | — | 提交全部答案 → 算分 → 触发报告 |
| 评分引擎 | 🔴 | — | 0-100 换算 + 双标签 |

**A 需要知道的：**
- 答案提交格式：`{ questionCode, value }`（多选题 value 是数组）
- 提交返回：`{ overseasScore, overseasTag }`（consultantScore 在前端**不展示**）
- 报告状态：`generating` 时显示加载页，`completed` 后跳转结果页

---

### M5：报告生成 🔴 待开始

| 任务 | B | A | 交付物 |
|------|:--:|:--:|------|
| AI Prompt 设计 | 🔴 | — | 三段 Prompt |
| `generateReport` | 🔴 | — | 生成 brief + full + sales 报告 |
| 模板兜底 | 🔴 | — | AI 失败时的 fallback |
| `getUserReport` | 🔴 | — | 按解锁状态返回不同内容 |
| 报告展示页 | — | 🔴 | 部分报告 + 完整报告预览 |

**A 需要知道的：**
- 未解锁时只返回 `briefReport` + `fullReportPreview`（不返回 `fullReport`）
- `briefReport` 包含行业分析和推荐路径
- `fullReport` 18 个字段，A 按需展示

---

### M6：解锁 + 顾问端 🔴 待开始

| 任务 | B | A | 交付物 |
|------|:--:|:--:|------|
| `unlockReportAfterWechatAdded` | 🔴 | — | |
| 顾问端所有页面 | — | 🔴 | 列表/详情/跟进 |
| `getConsultantDashboard` | 🔴 | — | 筛选+分页 |
| `getConsultantAssessmentDetail` | 🔴 | — | 用户全量数据 |
| `updateFollowUp` | 🔴 | — | 跟进状态+备注 |

**A 需要知道的：**
- 顾问端获取的 `consultantScore`/`consultantTag`/`salesFollowUpReport` **禁止**返回到用户端
- 用户端 `getUserReport` 永远不返回顾问字段

---

### M7：联调 + 验收 🔴 待开始

| 任务 | B | A |
|------|:--:|:--:|
| 用户端完整链路 | 🔴 | 🔴 |
| 顾问端完整链路 | 🔴 | 🔴 |
| 权限校验 | 🔴 | — |
| 异常状态（生成失败/未解锁/超时） | 🔴 | 🔴 |
| UI 细节 | — | 🔴 |
| 验收标准逐项检查 | 🔴 | 🔴 |

---

## 当前阻塞

| 阻塞项 | 原因 | 解阻塞方 |
|--------|------|:--:|
| 前后端函数冲突 | 22 个函数混布，旧 11 个需重写 | B |
| 题库未定 | questions 集合还没建，字段结构待确认 | B + A |
| 题目内容 | 18+ 道题的具体文案和选项 | A |

---

## 协同规则

1. **B 每完成一个云函数** → 更新 `API_CONTRACT.md` 对应章节 → 通知 A
2. **A 每完成一个页面** → 验证 mock 数据 → 告知 B 可以切真实接口
3. **字段变更** → B 先更新 `API_CONTRACT.md` → A 再改前端
4. **阻塞** → 当天在群内说，不过夜

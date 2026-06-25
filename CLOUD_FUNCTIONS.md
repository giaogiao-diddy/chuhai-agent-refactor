# 云函数全量清单

> 来源：《企业出海测评小程序开发文档》§15 + §4（功能范围）
> 共 17 个云函数，覆盖用户端、顾问端、管理端全部功能

---

## 一、全量列表

| # | 云函数 | 用途 | 权限 | 依赖 | 状态 |
|:--:|------|------|:--:|------|:--:|
| 1 | `login` | 微信登录：获取OPENID→创建/查询用户→返回角色 | 🌐 | 无 | ✅ 已部署 |
| 2 | `getSystemConfig` | 获取全局配置：客服二维码、标签规则、解锁开关 | 🌐 | 无 | ✅ 已部署 |
| 3 | `updateSystemConfig` | 管理员修改全局配置 | 👑 | ADMIN_OPENIDS | ✅ 已部署 |
| 4 | `getAssessmentConfig` | 获取题库：题目+选项+评分规则+分层逻辑 | 👤 | questions集合 | ✅ 已部署 |
| 5 | `createAssessment` | 创建测评：保存企业基础信息→初始化测评记录 | 👤 | basicInfo校验 | ✅ 已部署 |
| 6 | `submitAnswer` | 逐题提交答案：文本/单选/多选→支持覆盖 | 👤 | assessment_id | ✅ 已部署 |
| 7 | `completeAssessment` | 完成测评：算双分→打标签→触发报告生成 | 👤 | 18题答完 | ✅ 已部署 |
| 8 | `generateReports` | AI报告生成：调用DeepSeek→JSON校验→写入reports | — | M4评分+M5Prompt | 🔴 待开发 |
| 9 | `getUserReport` | 用户查报告：未解锁返回摘要，已解锁返回完整 | 👤 | reports集合 | 🔴 待开发 |
| 10 | `unlockReportAfterWechatAdded` | 解锁：用户点击"已添加客服"→is_unlocked=true | 👤 | assessment_id | 🔴 待开发 |
| 11 | `getConsultantDashboard` | 顾问列表：分页+筛选+搜索 | 💼 | role=consultant | 🔴 待开发 |
| 12 | `getConsultantAssessmentDetail` | 顾问查详情：用户全量数据+评分+报告+备注 | 💼 | role=consultant | 🔴 待开发 |
| 13 | `updateFollowUp` | 跟进管理：状态+备注+下次跟进时间 | 💼 | consultant_notes集合 | 🔴 待开发 |
| 14 | `getQuestionFlow` | 内部分层：根据branch返回对应题目组 | 👤 | questions集合 | ✅ 已部署 |
| 15 | `createWecomUnlockSession` | 企微解锁页：生成二维码+轮询配置 | 👤 | assessment_id | ✅ 已部署 |
| 16 | `getWecomUnlockStatus` | 轮询解锁状态 | 👤 | assessment_id | ✅ 已部署 |
| 17 | `mockUnlock` | 开发模拟解锁 | 👤 | 仅开发环境 | ✅ 已部署 |

---

## 二、用途归类

### 用户端（用户能直接调用的——前端页面使用）

| 页面 | 调用的云函数 |
|------|-------------|
| 首页 | `login` |
| 测评说明页 | `getSystemConfig` |
| 企业信息页 | `createAssessment` |
| 答题页 | `getAssessmentConfig` + `submitAnswer` |
| 提交测评 | `completeAssessment` |
| 部分报告页 | `getUserReport` |
| 完整报告预览 | `getUserReport`（未解锁） |
| 完整报告详情 | `getUserReport`（已解锁） |
| 企微解锁页 | `createWecomUnlockSession` + `getWecomUnlockStatus` |

### 顾问端（需 role=consultant 才能调用）

| 页面 | 调用的云函数 |
|------|-------------|
| 用户列表 | `getConsultantDashboard` |
| 用户详情 | `getConsultantAssessmentDetail` |
| 跟进管理 | `updateFollowUp` |

### 管理端（需 role=admin 才能调用）

| 页面 | 调用的云函数 |
|------|-------------|
| 配置管理 | `getSystemConfig` + `updateSystemConfig` |

### 内部/系统（前端不直接调，由其他云函数触发）

| 触发方 | 触发的云函数 |
|--------|------------|
| `completeAssessment` | `generateReports`（异步） |
| `submitAnswer`（可选） | 逐题AI诊断（V2 旧功能，当前未启用） |

---

## 三、状态汇总

```
✅ 已部署:  1-7, 14-17  (11个)
🟡 待改造:  9, 10, 12    (3个，代码已有但需适配)
🔴 待开发:  8, 11, 13    (3个，全新)
```

### 今天能做

| # | 云函数 | 为什么能做 |
|:--:|------|------|
| 11 | `getConsultantDashboard` | 纯查assessments表，不依赖题目/评分/报告 |
| 13 | `updateFollowUp` | 纯写consultant_notes表，不依赖题目/评分/报告 |
| 10 | `unlockReportAfterWechatAdded` | 纯更新is_unlocked字段 |

### 需等M3完成后

| # | 云函数 |
|:--:|------|
| 8 | `generateReports`（依赖完整评分+AI Prompt） |
| 9 | `getUserReport`（依赖报告内容已生成） |
| 12 | `getConsultantAssessmentDetail`（依赖评分+报告） |

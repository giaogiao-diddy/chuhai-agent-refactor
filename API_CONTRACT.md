# API 契约文档 — 前后端唯一真相源

> 开发 B 每完成一个云函数即更新此文件。开发 A 只看此文件即可开始开发。
> 格式：云函数名 → 请求参数 → 返回结构 → 权限 → 注意事项

---

## 统一响应格式（6月17日起）

所有云函数返回以下格式之一：

```js
// 成功 — 业务数据在 data 里
{ success: true, data: { ... } }

// 失败 — errorCode 用于前端判断错误类型
{ success: false, errorCode: "INVALID_PARAMS", errorMessage: "具体错误描述" }
```

前端 `cloudApi.js` 已兼容此格式，`call()` 返回的 `data` 就是 `result.data`。

---

## 云函数列表

| 序号 | 云函数 | 状态 | 说明 |
|:--:|------|:--:|------|
| 1 | `login` | ✅ 已部署 | 微信登录，返回用户信息和角色 |
| 2 | `getAssessmentConfig` | ✅ 已部署 | 从云数据库获取题目+分层规则 |
| 3 | `createAssessment` | ✅ 已部署 | 创建测评+保存企业信息（basicInfo 暂时可选，前端企业信息页做完后改为必填） |
| 4 | `submitAnswer` | ✅ 已部署 | 逐题提交答案（支持覆盖） |
| 5 | `completeAssessment` | ✅ 已部署 | 完成测评 → 算分 |
| 6 | `getSystemConfig` | ✅ 已部署 | 获取客服二维码等全局配置 |
| 7 | `updateSystemConfig` | ✅ 已部署 | 管理员更新系统配置 |
| 8 | `getUserReport` | 🟡 待改造 | 获取用户报告（按解锁状态返回分段） |
| 9 | `unlockReportAfterWechatAdded` | 🟡 待改造 | 用户点击"已添加客服" → 解锁 |
| 10 | `getConsultantDashboard` | 🔴 待开发 | 顾问端用户列表 |
| 11 | `getConsultantAssessmentDetail` | 🟡 待改造 | 顾问查看单个用户详情 |
| 12 | `updateFollowUp` | 🔴 待开发 | 顾问更新跟进状态+备注 |

---

## 通用约定

### 调用方式
```js
const { call } = require("../../utils/cloudApi");
const { data, error } = await call("函数名", { 参数 });
// data  = result.data（成功时）
// error = result.errorMessage（失败时）
```

### 权限标识
- 👤 普通用户可调用
- 💼 顾问可调用
- 👑 管理员可调用
- 🌐 无需登录（云函数自动获取 OPENID）

### 通用错误码
| errorCode | 含义 |
|-----------|------|
| `UNAUTHORIZED` | 未登录或 OPENID 获取失败 |
| `FORBIDDEN` | 当前角色无权访问 |
| `INVALID_PARAMS` | 请求参数校验失败，详见 errorMessage |
| `NOT_FOUND` | 请求的资源不存在 |

---

## 详细接口

### 1. login — 微信登录

> 🌐 | ✅ 已部署

```
请求:
  无（云函数从 wx.cloud 上下文自动获取 OPENID）

成功返回:
{
  success: true,
  data: {
    user: {
      _id: "xxx",
      openid: "oxxx",
      nickName: "",
      avatarUrl: "",
      role: "user"           // "user" | "consultant" | "admin"
    },
    isNewUser: true
  }
}

失败返回:
{
  success: false,
  errorCode: "UNAUTHORIZED",
  errorMessage: "未获取到用户身份"
}
```

---

### 2. getAssessmentConfig — 获取测评配置

> 👤 | ✅ 已部署（从 questions 集合读取）

```
请求:
  无

成功返回:
{
  success: true,
  data: {
    questions: [
      {
        question_id: "q_001",
        type: "text",             // "single_choice" | "multiple_choice" | "text" | "info"
        title: "您所在的行业和主营产品是什么？",
        description: "请尽量写到细分品类...",
        branch: "all",            // "all" | "experienced" | "newbie"
        required: true,
        sort_order: 1,
        options: [                // 仅 single_choice / multiple_choice 有此字段
          {
            id: "factory",
            text: "源头工厂",
            feasibility_score: 4,  // 企业出海评分分值
            lead_score: 3          // 顾问跟进评分分值
          }
        ],
        is_scored: true           // false 时不计分（如说明型题目）
      }
    ]
  }
}
```

---

### 3. createAssessment — 创建测评

> 👤 | ✅ 已部署 | **必须传 basicInfo**

```
请求:
{
  basicInfo: {
    companyName: "某科技有限公司",           // 必填，≤120字符
    industry: "健身器材",                    // 必填
    industryCategory: "力量训练设备",         // 必填
    mainProduct: "杠铃/哑铃/综合训练架",      // 必填
    currentSalesRegions: ["国内", "东南亚"],  // 必填，数组
    targetMarkets: ["北美", "欧洲"],          // 必填，数组
    annualRevenue: "1000万-5000万元",        // 必填
    hasForeignTradeExperience: true          // 必填，布尔值（不是字符串"有"/"没有"）
  }
}

成功返回:
{
  success: true,
  data: {
    assessment_id: "assess_xxx",
    assessmentId: "assess_xxx",
    status: "in_progress"
  }
}

失败返回示例:
{
  success: false,
  errorCode: "INVALID_PARAMS",
  errorMessage: "companyName不能为空"
}
```

---

### 4. submitAnswer — 逐题提交答案

> 👤 | ✅ 已部署 | 支持覆盖（重复提交同一题 = 更新）

```
请求:
{
  assessment_id: "assess_xxx",
  question_id: "q_001",
  value: "健身器材-力量训练设备",            // 文本题/单选题: 字符串
  // 或多选题: value: ["option_a", "option_b"]
}

成功返回:
{
  success: true,
  data: {
    ok: true,
    saved: true
  }
}
```

---

### 5. completeAssessment — 完成测评

> 👤 | ✅ 已部署

```
请求:
{
  assessment_id: "assess_xxx"
}

成功返回:
{
  success: true,
  data: {
    assessment_id: "assess_xxx",
    status: "completed",
    branch: "experienced",               // "experienced" | "newbie"
    feasibility_score: 72,              // 0-100
    feasibility_tag: "高潜力出海企业",
    lead_score: 58,                     // 0-100（仅顾问可见）
    lead_priority: "A类客户"
  }
}
```

---

### 6. getSystemConfig — 获取系统配置

> 🌐 | ✅ 已部署

```
请求:
  {}  // 空或任意

成功返回:
{
  success: true,
  data: {
    config: {
      consultant_wechat_qr: "https://...",
      unlock_enabled: true,
      unlock_message: "添加客服微信后自动解锁完整报告"
    }
  }
}
```

---

### 7. updateSystemConfig — 更新系统配置

> 👑 | ✅ 已部署 | 需配置 ADMIN_OPENIDS 环境变量

```
请求:
{
  key: "consultant_wechat_qr",
  value: "https://xxx.cloud.tencent.com/new-qr.png"
}

成功返回:
{ success: true, data: { updated: true } }

失败返回:
{ success: false, errorCode: "FORBIDDEN", errorMessage: "无权限" }
```

---

### 8. getQuestionFlow — 根据分层返回题流

> 👤 | ✅ 已部署 | 内部使用，前端一般调 getAssessmentConfig

```
请求:
{
  assessment_id: "assess_xxx"
}

成功返回:
{
  success: true,
  data: {
    branch: "experienced",
    questions: [ ... ]     // 按分层筛选后的题目列表
  }
}
```

---

### 9. getUserReport — 获取用户报告

> 👤 | 🟡 待改造

```
请求:
{ assessment_id: "assess_xxx" }

未解锁时只返回 briefReport + fullReportPreview
已解锁时额外返回 fullReport + salesFollowUpReport
（具体结构后续更新）
```

---

### 10. unlockReportAfterWechatAdded — 解锁完整报告

> 👤 | 🟡 待改造

```
请求:
{ assessment_id: "assess_xxx" }

成功返回:
{ success: true, data: { unlocked: true } }
```

---

### 11. getConsultantDashboard — 顾问端用户列表

> 💼 | 🔴 待开发

```
请求:
{ page: 1, pageSize: 20, filter: { ... } }

（具体结构后续更新）
```

---

### 12. updateFollowUp — 更新跟进状态

> 💼 | 🔴 待开发

```
请求:
{
  assessment_id: "assess_xxx",
  follow_up_status: "已沟通需求",
  note: "客户对北美市场感兴趣"
}

（具体结构后续更新）
```

---

## ⚠️ 重要变更（6月17日）

1. **统一响应格式**：所有函数改为 `{ success, data }` / `{ success, errorCode, errorMessage }`
2. **createAssessment 需要 basicInfo**：建议前端企业信息页做完后必传。当前暂时可选。`hasForeignTradeExperience` 是布尔值（`true`/`false`），不是字符串"有"/"没有"
3. **currentSalesRegions 和 targetMarkets 是数组**：`["北美"]` 不是 `"北美"`

---

---

## Agent 智能体接口（新增 Phase 2-3）

### 13. startConversation — 启动对话诊断

> 👤 | 已部署

```
请求:
{ assessment_id: "assess_xxx" }

成功返回:
{
  success: true,
  data: {
    replyText: "你好，我是深度未来的企业出海诊断顾问...",
    conversation_status: "collecting",
    conversation_round: 0
  }
}
```

---

### 14. continueConversation — 继续对话

> 👤 | 已部署

```
请求:
{
  assessment_id: "assess_xxx",
  client_message_id: "uuid-from-client",  // 前端生成，幂等防重
  message: "我们是做健身器材的..."
}

成功返回（正常进行中）:
{
  success: true,
  data: {
    replyText: "健身器材在东南亚确实有机会...",
    conversation_round: 2,
    isEnded: false,
    isVetoed: false
  }
}

成功返回（8轮结束）:
{
  success: true,
  data: {
    replyText: "沟通已经比较充分了，现在为您生成报告...",
    conversation_round: 8,
    isEnded: true,
    isVetoed: false
  }
}

成功返回（一票否决）:
{
  success: true,
  data: {
    replyText: "",
    conversation_round: 3,
    isEnded: true,
    isVetoed: true,
    vetoMessage: "当前业务不适合以短视频作为主成交渠道，建议考虑B2B平台、展会、独立站等替代路径。系统已为您准备风险提示白皮书。"
  }
}
```

**关键规则：**
- `client_message_id` 必须前端生成并携带。同一 ID 重复请求不重复调用 AI，直接返回缓存结果。
- `isEnded === true` 时前端底部切换为"生成报告"按钮。
- `isVetoed === true` 时前端切换为"查看风险提示"按钮。
- 重试请求必须携带相同的 `client_message_id`。

---

### 15. finishConversation — 结算生成报告

> 👤 | 已部署

```
请求:
{ assessment_id: "assess_xxx" }

成功返回:
{
  success: true,
  data: {
    assessment_id: "assess_xxx",
    status: "completed",
    feasibility_score: 72,
    feasibility_tag: "轻量试探型",
    generation_type: "ai"           // "ai" | "template"
  }
}

失败返回:
{
  success: false,
  errorCode: "REPORT_TRANSACTION_FAILED",
  errorMessage: "原因说明"
}
```

**后端行为：**
- 槽位补全 17 道题 → 规则算分 → RAG → AI报告 → reportGuard审计 → 事务写入 reports + lead_reports。
- AI 失败自动走模板兜底。
- reports 文档含 `openid` 字段，兼容现有解锁函数。
- lead_reports 文档含 `sales_followup` 等顾问字段，只有顾问端接口返回。

---

## 变更日志

| 日期 | 变更 |
|------|------|
| 6/17 初始 | 创建契约文档 |
| 6/17 更新 | login / getAssessmentConfig / createAssessment / getSystemConfig / updateSystemConfig / getQuestionFlow 已部署 |
| 6/17 更新 | 统一响应格式改为 `{ success, data/errorCode/errorMessage }` |
| 6/17 更新 | createAssessment 强制要求 basicInfo |
| 6/18 新增 | Agent 智能体接口：startConversation + continueConversation + finishConversation |

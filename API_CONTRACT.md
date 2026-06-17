# API 契约文档 — 前后端唯一真相源

> 开发 B 每完成一个云函数即更新此文件。开发 A 只看此文件即可开始开发，无需反复沟通。
> 格式：云函数名 → 请求参数 → 返回结构 → 权限 → 注意事项

---

## 云函数列表

| 序号 | 云函数 | 状态 | 说明 |
|:--:|------|:--:|------|
| 1 | `login` | 🔴 待开发 | 微信登录，返回用户信息和角色 |
| 2 | `getAssessmentConfig` | 🟡 需改造 | 获取题目+评分规则+分层配置 |
| 3 | `createAssessment` | 🟡 需改造 | 创建测评+保存企业信息 |
| 4 | `submitAssessment` | 🟡 需改造 | 提交完整答题 → 算分 → 生成报告 |
| 5 | `getUserReport` | 🟡 需改造 | 获取用户自己的报告（按解锁状态返回） |
| 6 | `unlockReportAfterWechatAdded` | 🟡 需改造 | 用户点击"已添加客服"解锁 |
| 7 | `getConsultantDashboard` | 🔴 待开发 | 顾问端用户列表 |
| 8 | `getConsultantAssessmentDetail` | 🟡 需改造 | 顾问查看单个用户详情 |
| 9 | `updateFollowUp` | 🔴 待开发 | 顾问更新跟进状态+备注 |
| 10 | `getSystemConfig` | 🔴 待开发 | 获取客服二维码等系统配置 |
| 11 | `updateSystemConfig` | 🔴 待开发 | 管理员更新系统配置 |

---

## 通用约定

### 调用方式
```js
// 前端统一通过 cloudApi.js 调用
const { call } = require("../../utils/cloudApi");
const { data, error } = await call("函数名", { 参数 });
// data: 成功时返回的数据
// error: 失败时返回的错误信息字符串
```

### 权限标识
- 👤 普通用户可调用
- 💼 顾问可调用
- 👑 管理员可调用
- 🌐 无需登录

### 通用错误码
| error 内容 | 含义 |
|-----------|------|
| `"未登录"` | 需要微信授权 |
| `"无权限"` | 当前角色不能访问 |
| `"不存在"` | 请求的资源不存在 |
| `"已提交"` | 不允许重复操作 |

---

## 详细接口

### 1. login — 微信登录

> 🌐 无需登录 | 🔴 待开发

```
请求:
  无（云函数从 wx.cloud 上下文自动获取 OPENID）

返回:
{
  user: {
    _id: "xxx",
    openid: "oxxx",
    nickName: "张三",
    avatarUrl: "https://...",
    role: "user"        // "user" | "consultant" | "admin"
  },
  isNewUser: true       // 首次登录为 true
}
```

---

### 2. getAssessmentConfig — 获取测评配置

> 👤 需登录 | 🟡 待改造

```
请求:
  无

返回:
{
  questions: [
    {
      _id: "q_001",
      code: "industry",
      type: "text",            // "single" | "multiple" | "text" | "info"
      title: "您所在的行业和主营产品是什么？",
      description: "请尽量写到细分品类...",
      required: true,
      order: 1,
      options: [               // single/multiple 时有此字段
        { id: "a", text: "源头工厂", score: { overseas: 4, consultant: 3 } }
      ],
      branch: "all",           // "all" | "experienced" | "newbie"
      scoringRules: {          // 评分规则（顾问端展示用，前端不关心）
        overseas: {},
        consultant: {}
      }
    }
  ],
  tags: {
    overseas: [
      { range: [80, 100], label: "高潜力出海企业" },
      { range: [60, 79], label: "具备出海基础" }
    ],
    consultant: [
      { range: [80, 100], label: "A类客户：强意向" },
      { range: [60, 79], label: "B类客户：可重点培育" }
    ]
  }
}
```

---

### 3. createAssessment — 创建测评

> 👤 需登录 | 🟡 待改造

```
请求:
{
  basicInfo: {
    companyName: "某科技有限公司",
    industry: "健身器材",
    industryCategory: "力量训练设备",
    mainProduct: "杠铃/哑铃/综合训练架",
    currentSalesRegions: "国内为主，少量东南亚",
    targetMarkets: "北美、欧洲",
    annualRevenue: "1000万-5000万元",
    hasForeignTradeExperience: "有"       // "有" | "没有"
  }
}

返回:
{
  assessmentId: "assess_xxx",
  status: "draft"
}
```

---

### 4. submitAssessment — 提交测评

> 👤 需登录 | 🟡 待改造

```
请求:
{
  assessmentId: "assess_xxx",
  answers: [
    { questionCode: "industry", value: "健身器材-力量训练设备" },
    { questionCode: "company_type", value: ["factory"] },  // 多选传数组
    { questionCode: "has_overseas_exp", value: "yes" }
  ]
}

返回:
{
  assessmentId: "assess_xxx",
  status: "completed",
  branch: "experienced",              // "experienced" | "newbie"
  overseasScore: 72,                  // 0-100
  overseasTag: "高潜力出海企业",
  consultantScore: 58,                // 0-100（仅顾问可见，此处返回但前端不展示）
  consultantTag: "A类客户",
  reportId: "rpt_xxx",
  reportStatus: "generating"          // "pending" | "generating" | "completed" | "failed"
}
```

---

### 5. getUserReport — 获取用户报告

> 👤 需登录 | 🟡 待改造

```
请求:
{
  assessmentId: "assess_xxx"
}

返回 (未解锁时):
{
  assessmentId: "assess_xxx",
  unlockedFullReport: false,
  briefReport: {                     // 部分报告（始终可见）
    overseasPotential: "您的企业...",
    industryAnalysis: "...",
    targetMarkets: ["北美", "欧洲"],
    advantages: ["..."],
    disadvantages: ["..."],
    recommendedPath: "短视频出海",
    nextSteps: ["..."]
  },
  fullReportPreview: {               // 完整报告前 1-2 页（始终可见）
    diagnosis: "综合诊断结论...",
    industryOpportunity: "..."
  }
}

返回 (已解锁时):
{
  assessmentId: "assess_xxx",
  unlockedFullReport: true,
  briefReport: { ... },
  fullReportPreview: { ... },
  fullReport: {                      // 完整报告（解锁后可见）
    diagnosis: "...",
    industryOpportunity: "...",
    targetMarketRecommendation: "...",
    customerProfile: "...",
    contentStrategy: "...",
    trafficStrategy: "...",
    conversionPath: "...",
    actionPlan30Days: ["..."],
    actionPlan90Days: ["..."]
  }
}
```

---

### 6. unlockReportAfterWechatAdded — 解锁完整报告

> 👤 需登录 | 🟡 待改造

```
请求:
{
  assessmentId: "assess_xxx"
}

返回:
{
  unlocked: true,
  message: "完整报告已解锁"
}
```

---

### 7. getConsultantDashboard — 顾问端用户列表

> 💼 需顾问权限 | 🔴 待开发

```
请求:
{
  page: 1,
  pageSize: 20,
  filter: {
    overseasTag: "高潜力出海企业",    // 可选
    consultantTag: "A类客户",         // 可选
    unlockedFullReport: true,         // 可选
    followUpStatus: "未联系",         // 可选
    search: "健身"                    // 可选，搜索企业名/行业
  }
}

返回:
{
  total: 156,
  list: [
    {
      assessmentId: "assess_xxx",
      userId: "user_xxx",
      nickName: "张三",
      companyName: "某科技",
      industry: "健身器材",
      overseasScore: 72,
      overseasTag: "高潜力出海企业",
      consultantScore: 58,
      consultantTag: "A类客户",
      unlockedFullReport: true,
      followUpStatus: "未联系",
      completedAt: "2026-06-17T10:00:00Z"
    }
  ]
}
```

---

### 8. getConsultantAssessmentDetail — 顾问查看用户详情

> 💼 需顾问权限 | 🟡 待改造

```
请求:
{
  assessmentId: "assess_xxx"
}

返回:
{
  // ===== 用户基础信息 =====
  user: {
    nickName: "张三",
    avatarUrl: "https://..."
  },
  basicInfo: {
    companyName: "...",
    industry: "...",
    // ... 全部企业信息字段
  },

  // ===== 答题记录 =====
  answers: [
    { questionCode: "industry", questionTitle: "行业", answer: "健身器材" }
  ],

  // ===== 评分 + 标签（顾问可见全部） =====
  overseasScore: 72,
  overseasTag: "高潜力出海企业",
  consultantScore: 58,
  consultantTag: "A类客户",

  // ===== 报告（顾问可见全部） =====
  briefReport: { ... },
  fullReport: { ... },
  salesFollowUpReport: {              // 顾问跟进报告（仅顾问可见）
    priority: "P0-立即跟进",
    willingnessJudgment: "强出海意向，有预算",
    painPoints: ["获客成本高", "不清楚海外市场定位"],
    recommendedApproach: "以北美市场短视频获客为切入点",
    suggestedScript: "张总您好，看了您的测评...",
    resistanceAnalysis: "可能担心短视频投入产出比",
    nextSteps: ["发送行业案例", "预约15分钟电话"]
  },

  // ===== 顾问备注 =====
  consultantNotes: [
    {
      consultantId: "consultant_001",
      followUpStatus: "已加微信",
      note: "客户对短视频出海很有兴趣",
      createdAt: "2026-06-17"
    }
  ]
}
```

---

### 9. updateFollowUp — 更新跟进状态

> 💼 需顾问权限 | 🔴 待开发

```
请求:
{
  assessmentId: "assess_xxx",
  followUpStatus: "已沟通需求",       // "未联系"|"已加微信"|"已发完整报告"|"已沟通需求"|"已预约会议"|"已成交"|"暂不跟进"
  note: "客户对北美市场特别感兴趣，建议下周发案例",
  nextFollowUpAt: "2026-06-24"        // 可选
}

返回:
{
  success: true
}
```

---

### 10. getSystemConfig — 获取系统配置

> 🌐 无需登录 | 🔴 待开发

```
请求:
  {}  // 空

返回:
{
  consultantWechatQR: "https://xxx.cloud.tencent.com/qr.png",  // 客服微信二维码
  unlockConfig: {
    enabled: true,
    message: "添加客服微信后自动解锁完整报告"
  },
  tags: {
    overseas: [...],     // 海外评分标签配置
    consultant: [...]    // 顾问评分标签配置
  }
}
```

---

### 11. updateSystemConfig — 更新系统配置

> 👑 需管理员权限 | 🔴 待开发

```
请求:
{
  key: "consultantWechatQR",
  value: { url: "https://xxx.cloud.tencent.com/new-qr.png" }
}

返回:
{
  success: true
}
```

---

## 变更日志

| 日期 | 变更 | 接口 |
|------|------|------|
| 2026-06-17 | 创建契约文档 | 全部 11 个接口定义 |
| 2026-06-17 | 待逐接口实现并更新状态 | — |

---

> **开发 A 看这里：当前所有接口尚在开发中。可以先用本文档设计的返回格式做 mock 数据开发前端页面。接口就绪后只需切换 `call()` 调用即可。**

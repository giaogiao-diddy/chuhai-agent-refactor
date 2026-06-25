# 企业微信添加解锁完整报告 — 全栈实现提示词

> 交给大模型执行 | 只读参考：PRD.md / TECH_DESIGN.md / CLAUDE.md / CHANGELOG_V2.md | 日期：2026-06-16

---

## 一、业务目标

把当前的"填写姓名/电话/公司/身份 → 解锁完整报告"替换为"扫描企微二维码添加顾问 → 后端检测添加成功 → 自动解锁完整报告"。

**关键原则：**
- 小程序前端无法可靠判断用户是否真的添加了企微，必须依赖后端状态。
- 后端状态来源可以是：企微客户联系回调 / 管理员手动标记 / 开发期模拟接口。
- 留资表单（LeadCreate）保留作为兜底方案，不删除。
- 所有新代码必须兼容现有 118 个测试，不允许破坏性变更。

---

## 二、架构设计

```
┌─────────────┐    ┌──────────────────┐    ┌──────────────┐
│  小程序前端   │    │   FastAPI 后端    │    │  企业微信服务  │
└──────┬──────┘    └────────┬─────────┘    └──────┬───────┘
       │                    │                      │
       │ ① GET unlock-info │                      │
       │──────────────────→│                      │
       │                    │                      │
       │ ② {qr_url,         │                      │
       │    state_token,     │                      │
       │    poll_interval}   │                      │
       │←──────────────────│                      │
       │                    │                      │
       │ ③ 展示企微二维码     │                      │
       │   用户扫码添加       │                      │
       │                    │                      │
       │                    │ ④ 企微回调            │
       │                    │   (客户添加事件)       │
       │                    │←────────────────────│
       │                    │                      │
       │                    │ ⑤ 匹配 state_token   │
       │                    │   更新 is_unlocked    │
       │                    │                      │
       │ ⑥ GET unlock-status│                      │
       │──────────────────→│                      │
       │                    │                      │
       │ ⑦ {unlocked: true} │                      │
       │←──────────────────│                      │
       │                    │                      │
       │ ⑧ 进入完整报告       │                      │
```

---

## 三、数据模型修改

### 3.1 新增表 `wecom_unlock_tokens`

```python
class WecomUnlockToken(Base):
    __tablename__ = "wecom_unlock_tokens"

    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False, unique=True)
    state_token = Column(String(64), unique=True, nullable=False, index=True)  # URL state 参数
    external_userid = Column(String(64), nullable=True)  # 企微回调返回的外部联系人 ID
    status = Column(String(16), default="pending")  # pending / scanned / unlocked / expired
    qr_url = Column(String(512), nullable=True)  # 企微联系我二维码 URL
    created_at = Column(DateTime, server_default=func.now())
    unlocked_at = Column(DateTime, nullable=True)
```

### 3.2 新增表 `wecom_callback_logs`

```python
class WecomCallbackLog(Base):
    __tablename__ = "wecom_callback_logs"

    id = Column(Integer, primary_key=True)
    raw_body = Column(Text, nullable=True)  # 企微回调原始 XML/JSON
    event_type = Column(String(64), nullable=True)  # 回调事件类型
    external_userid = Column(String(64), nullable=True, index=True)
    state = Column(String(64), nullable=True, index=True)  # 从回调中提取的 state
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
```

### 3.3 现有表修改

- `Lead` 表不删除，保留作为留资表单兜底。
- `Report.is_unlocked` 已有，直接复用。

---

## 四、配置新增

修改 `backend/config.py`，新增企微配置：

```python
# ── 企业微信 ───────────────────────────────────────────
wecom_corp_id: str = ""           # 企业 ID
wecom_corp_secret: str = ""       # 应用 Secret
wecom_token: str = ""             # 回调 Token（企微后台配置）
wecom_encoding_aes_key: str = ""  # 回调加密 Key
wecom_qr_url_template: str = ""   # 联系我二维码 URL 模板（含 {state} 占位）
wecom_callback_enabled: bool = False  # 是否启用企微回调（开发环境可关）
```

---

## 五、API 接口实现

### 5.1 `GET /api/wecom/unlock-info/{assessment_id}`

**用途**：前端进入解锁页时调用，获取企微二维码和轮询配置。

**JWT**：需要

**校验**：
- assessment 属于当前用户
- assessment 已完成
- 如果已经 unlocked，直接返回 `{already_unlocked: true}`

**业务逻辑**：
1. 查 `WecomUnlockToken` 表，如果已有未过期的 token 则复用。
2. 如果没有，生成新 `state_token`（UUID4）。
3. 拼装二维码 URL：用 `wecom_qr_url_template` 中的 `{state}` 替换为 `state_token`。如果未配置模板，使用开发模式占位 URL。
4. 存入 `WecomUnlockToken` 表。
5. 返回 `{state_token, qr_url, poll_interval_ms: 3000, already_unlocked: false}`。

**如果 `wecom_callback_enabled = false`（开发/本地模式）**：直接返回 mock 二维码 URL 和 state_token，前端展示假二维码。同时额外返回 `dev_mode: true`，前端可以在开发模式下显示一个「模拟添加成功」按钮。

### 5.2 `GET /api/wecom/unlock-status/{state_token}`

**用途**：前端轮询此接口，检测用户是否已添加企微。

**JWT**：需要（校验 state_token 属于当前用户的测评）

**响应**：
```json
// 未添加
{"status": "pending", "unlocked": false}

// 已添加
{"status": "unlocked", "unlocked": true}

// 已过期（超过 30 分钟）
{"status": "expired", "unlocked": false}
```

### 5.3 `POST /api/wecom/callback`

**用途**：企业微信回调接收端点。企微服务器在客户添加时会 POST 到此 URL。

**JWT**：不需要（企微回调有自己的签名验证）

**关键实现步骤**：
1. 接收企微回调 POST body（XML 格式）。
2. 验证回调签名（使用 `wecom_token` + `wecom_encoding_aes_key`）。
3. 解密回调消息体。
4. 提取 `Event` 类型、`ExternalUserID`、`State`（来自联系我二维码的 state 参数）。
5. 如果是 `change_external_contact` 事件且为 `add_external_contact`：
   - 查 `WecomUnlockToken` 表中匹配的 `state_token`。
   - 更新 `external_userid`、`status = "unlocked"`、`unlocked_at = now`。
   - 更新对应 `Report.is_unlocked = True`。
6. 所有回调写入 `WecomCallbackLog`（包括非添加事件，方便排查）。
7. 返回企微要求的 `"success"` 或 echostr（用于 URL 验证）。

**企微回调 XML 解析参考**：
```python
import xml.etree.ElementTree as ET
root = ET.fromstring(xml_body)
event = root.find(".//Event")
change_type = root.find(".//ChangeType")
external_userid = root.find(".//ExternalUserID")
state = root.find(".//State")
```

### 5.4 `POST /api/wecom/dev-unlock`（仅开发模式）

**用途**：开发/本地环境下的模拟解锁端点，绕过真实企微回调。

**JWT**：需要

**校验**：仅在 `wecom_callback_enabled = false` 时可用，否则返回 403。

**请求体**：
```json
{"assessment_id": 1}
```

**业务逻辑**：
1. 查 `WecomUnlockToken` 表，设置 `external_userid = f"dev_user_{current_user['user_id']}"`、`status = "unlocked"`。
2. 更新 `Report.is_unlocked = True`。
3. 返回 `{unlocked: true}`。

---

## 六、前端实现

### 6.1 新页面 `pages/wecom-unlock/wecom-unlock`

**路由**：从 `report-partial` 点"解锁完整报告"时跳转过来，URL 带 `assessment_id`。

**功能**：
1. `onLoad` 调 `GET /api/wecom/unlock-info/{assessment_id}`。
2. 拿到 `qr_url` 后渲染企微二维码图片（`<image src="{{qrUrl}}">`）。
3. 开始轮询 `GET /api/wecom/unlock-status/{state_token}`，每 3 秒一次。
4. 轮询到 `unlocked: true` → 自动跳转完整报告页。
5. 开发模式下（`dev_mode: true`），显示「模拟添加成功」按钮，点后调 `POST /api/wecom/dev-unlock`。
6. 超时（30 分钟未解锁）→ 提示用户重新扫码。
7. 页面底部保留兜底入口：「不方便添加？填写信息解锁」，点后跳转原有留资页 `lead.js`。

**状态 UX**：
```
扫码添加顾问
    ↓
   [企微二维码]
    ↓
等待添加中...（轮询动画）
    ↓
添加成功！正在解锁... → 自动跳转
```

### 6.2 `report-partial` 修改

`goToLead()` 改为跳转到新解锁页：
```js
goToUnlock() {
    const id = this.data.assessmentId;
    wx.navigateTo({ url: `/pages/wecom-unlock/wecom-unlock?assessment_id=${id}` });
}
```

先检查是否已解锁：如果 `GET /api/reports/{id}/full` 返回 200（已解锁），直接进完整报告；否则进解锁页。

### 6.3 WXML 结构参考

```xml
<view class="page">
  <view class="qrcode-section">
    <image class="qrcode-img" src="{{qrUrl}}" mode="widthFix" />
    <view class="qrcode-hint">长按识别二维码，添加顾问企业微信</view>
  </view>

  <view class="status-section">
    <view wx:if="{{status === 'pending'}}" class="status-waiting">
      <loading /> 等待添加...
    </view>
    <view wx:if="{{status === 'unlocked'}}" class="status-success">
      ✅ 添加成功，正在解锁报告...
    </view>
    <view wx:if="{{status === 'expired'}}" class="status-expired">
      二维码已过期，请刷新重试
      <button bindtap="refreshQR">刷新二维码</button>
    </view>
  </view>

  <view class="fallback-section">
    <view class="divider">或</view>
    <button bindtap="goToLeadForm">填写信息解锁</button>
  </view>

  <!-- 仅开发模式 -->
  <view wx:if="{{devMode}}" class="dev-tools">
    <button bindtap="devUnlock">🔧 模拟添加成功</button>
  </view>
</view>
```

---

## 七、企微后台配置（给运营/运维）

以下需要在企业微信管理后台完成：

1. **创建自建应用**：企业微信管理后台 → 应用管理 → 自建 → 创建应用。
2. **获取 Corp ID / Secret**：应用详情页。
3. **配置接收消息回调 URL**：
   - URL：`https://<你的域名>/api/wecom/callback`
   - Token：随机字符串（与 `wecom_token` 一致）
   - EncodingAESKey：随机 43 位（与 `wecom_encoding_aes_key` 一致）
4. **配置可信 IP**：将云托管出口 IP 加入白名单。
5. **配置联系我二维码**：客户联系 → 联系我 → 新建 → 选择"可获取客户信息" → 在 URL 中附加 `?state={state}` → 复制二维码 URL 模板。

---

## 八、实施顺序

```
1. 数据模型: WecomUnlockToken + WecomCallbackLog + config 企微配置
2. 服务层: wecom_service.py (生成 token / 处理回调 / 验证签名 / 解密消息)
3. API: GET unlock-info + GET unlock-status + POST callback + POST dev-unlock
4. 前端: pages/wecom-unlock/ 新页面 (WXML/JS/WXSS)
5. 前端: report-partial 修改跳转逻辑
6. 测试: 单元测试 (mock 企微回调) + 集成测试 (dev-unlock)
7. 企微后台配置 (运营侧)
8. 端到端验证: 真实扫码 → 回调 → 解锁 → 完整报告
```

---

## 九、开发模式降级路径

| 环境 | wecom_callback_enabled | 行为 |
|------|:--:|------|
| 本地开发 | false | 前端显示假二维码 +「模拟添加」按钮 |
| 测试环境 | false | 同上 |
| 生产环境 | true | 真实企微二维码 + 回调解锁 |
| 生产降级 | true→false | 紧急关闭企微，回退到留资表单模式 |

回退开关：如果企微回调异常，运维将 `LB_WECOM_CALLBACK_ENABLED=false` 后重启，前端检测到 `GET /reports/{id}/full` 返回 403 时，自动走留资表单页兜底。

---

## 十、安全红线

1. **回调签名验证**：`POST /api/wecom/callback` 必须验证企微签名，不接受裸请求。
2. **state_token 归属**：轮询 `unlock-status` 时校验 state_token 属于当前 JWT 用户。
3. **state_token 一次性**：一个 assessment 只能有一个有效 state_token，重复生成时旧 token 失效。
4. **不存储敏感信息**：回调日志不存用户手机号、微信昵称，只存 external_userid 和 state。
5. **开发解锁接口**：`POST /api/wecom/dev-unlock` 仅在不启用回调时可用，生产环境严格禁止。

---

## 十一、验收标准

- [ ] 开发模式下：点"模拟添加成功" → 自动解锁 → 进入完整报告
- [ ] 生产模式下：扫码添加企微 → 企微回调触发 → 轮询检测到解锁 → 进入完整报告
- [ ] 已有留资兜底：点"填写信息解锁" → 原留资表单可用
- [ ] 已解锁用户回到解锁页：直接提示"已解锁"并跳转
- [ ] 二维码过期：提示刷新
- [ ] 全量测试通过（不破坏现有 118 个测试）
- [ ] 新增测试 >= 6 个（覆盖 mock 解锁、回调处理、权限校验）

---

## 十二、参考提示词（给大模型的第一句话）

```text
请严格按照 WECOM_UNLOCK_PROMPT.md 实施企业微信添加解锁功能。
先读取 AGENTS.md、CLAUDE.md、PRD.md、TECH_DESIGN.md、CHANGELOG_V2.md。
按实施顺序逐步修改，每步完成后运行 pytest 确认不破坏现有 118 个测试。
遵守 Karpathy 四原则：先推理、简洁优先、精准修改、目标驱动。
```

---

**结束。**

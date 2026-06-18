"use strict";

const app = getApp();
const { call } = require("../../utils/cloudApi");

Page({
  data: {
    assessmentId: null,
    messageList: [],
    inputText: "",
    isSending: false,
    isTyping: false,
    isEnded: false,
    isVetoed: false,
    vetoMessage: "",
    scrollToId: "bottom-anchor",
    conversationRound: 0,
  },

  // 当前正在打字机动画中的消息 ID 和定时器
  _typingMessageId: null,
  _typingTimer: null,
  // 待发送的消息（失败重试用）
  _pendingMessage: null,

  /* ── 生命周期 ──────────────────────────────── */

  onLoad(options) {
    const assessmentId = options.assessment_id || app.globalData.assessmentId || null;
    if (!assessmentId) {
      wx.showToast({ title: "参数错误，请返回重试", icon: "none" });
      return;
    }
    this.setData({ assessmentId });

    // 初始化：调用 startConversation 获取开场白
    this.initConversation();
  },

  onUnload() {
    this.stopTyping();
  },

  /* ── 初始化对话 ────────────────────────────── */

  async initConversation() {
    const { assessmentId } = this.data;
    const { data, error } = await call("startConversation", {
      assessment_id: assessmentId,
    });

    if (error || !data) {
      wx.showToast({ title: "启动对话失败，请重试", icon: "none" });
      return;
    }

    // 将开场白以打字机效果展示
    this.startTyping(data.replyText, "ai-opening");
  },

  /* ── 发送消息 ──────────────────────────────── */

  onInputChange(e) {
    this.setData({ inputText: e.detail.value || "" });
  },

  async onSend() {
    const { inputText, isSending, isTyping, assessmentId, conversationRound } = this.data;
    if (isSending || isTyping || !inputText.trim()) return;

    const content = inputText.trim();

    // 生成幂等 client_message_id
    const clientMessageId = this.generateClientMessageId();

    // 乐观更新：立刻展示用户消息
    const userMsg = {
      id: clientMessageId,
      role: "user",
      content: content,
      createdAt: Date.now(),
    };
    this.pushMessage(userMsg);
    this.setData({ inputText: "", isSending: true, scrollToId: "bottom-anchor" });

    // 保存待发送消息（失败重试用）
    this._pendingMessage = { assessmentId, clientMessageId, content, round: conversationRound };

    // 调用云函数
    const { data, error } = await call("continueConversation", {
      assessment_id: assessmentId,
      client_message_id: clientMessageId,
      message: content,
    });

    if (error || !data) {
      // 失败：标记用户消息为发送失败，允许重试
      this.markMessageFailed(clientMessageId);
      this.setData({ isSending: false });
      wx.showToast({ title: "发送失败，请点击重试", icon: "none" });
      return;
    }

    // 成功：清除待发送
    this._pendingMessage = null;
    this.setData({ isSending: false });

    // 检查一票否决
    if (data.isVetoed) {
      this.setData({ isEnded: true, isVetoed: true });
      const vetoText = data.vetoMessage || "根据当前信息，您的核心业务暂不适合以短视频作为主成交渠道。系统已为您准备了风险提示和替代路径建议。";
      const aiMsgId = "ai-" + clientMessageId;
      this.startTyping(vetoText, aiMsgId);
      return;
    }

    // 检查是否对话结束
    if (data.isEnded) {
      this.setData({ isEnded: true });
    }
    if (data.conversation_round !== undefined) {
      this.setData({ conversationRound: data.conversation_round });
    }

    // 打字机展示 AI 回复
    const replyText = data.replyText || "明白了，让我继续了解一些关键信息。";
    const aiMsgId = "ai-" + clientMessageId;
    this.startTyping(replyText, aiMsgId);
  },

  /* ── 重试发送 ──────────────────────────────── */

  onRetryMessage(e) {
    const msgId = e.currentTarget.dataset.id;
    const pending = this._pendingMessage;
    if (!pending || pending.clientMessageId !== msgId) return;

    // 移除失败标记，重新发送（携带相同 client_message_id）
    this.setData({ isSending: true });
    this.retrySend(pending);
  },

  async retrySend(pending) {
    const { data, error } = await call("continueConversation", {
      assessment_id: pending.assessmentId,
      client_message_id: pending.clientMessageId,
      message: pending.content,
    });

    this.setData({ isSending: false });

    if (error || !data) {
      wx.showToast({ title: "重试失败，请稍后再试", icon: "none" });
      return;
    }

    this._pendingMessage = null;
    this.markMessageSent(pending.clientMessageId);

    if (data.isVetoed) {
      this.setData({ isEnded: true, isVetoed: true });
      const vetoText = data.vetoMessage || "根据当前信息，您的核心业务暂不适合以短视频作为主成交渠道。";
      this.startTyping(vetoText, "ai-" + pending.clientMessageId);
      return;
    }

    if (data.isEnded) {
      this.setData({ isEnded: true });
    }

    const replyText = data.replyText || "";
    this.startTyping(replyText, "ai-" + pending.clientMessageId);
  },

  /* ── 生成报告 ──────────────────────────────── */

  async onGenerateReport() {
    const { assessmentId } = this.data;
    wx.showLoading({ title: "报告正在精细生成中...", mask: true });

    const { data, error } = await call("finishConversation", {
      assessment_id: assessmentId,
    });

    wx.hideLoading();

    if (error || !data) {
      wx.showToast({ title: "报告生成失败，请重试", icon: "none" });
      return;
    }

    // 跳转到报告展示页
    app.globalData.assessmentId = assessmentId;
    wx.redirectTo({
      url: `/pages/report-partial/report-partial?assessment_id=${assessmentId}&score=${data.feasibility_score || 0}&tag=${encodeURIComponent(data.feasibility_tag || "")}`,
    });
  },

  /* ── 打字机效果 ────────────────────────────── */

  startTyping(fullText, msgId) {
    this.stopTyping();

    // 先在 messageList 中插入一条空消息
    const aiMsg = {
      id: msgId,
      role: "assistant",
      content: fullText,
      displayText: "",
      typing: true,
    };
    this.pushMessage(aiMsg);
    this.setData({ isTyping: true });

    const chars = fullText.split("");
    let index = 0;
    this._typingMessageId = msgId;

    this._typingTimer = setInterval(() => {
      if (index >= chars.length) {
        this.finishTyping(msgId);
        return;
      }
      // 每次取 1-3 个字符，模拟非匀速
      const chunk = chars.slice(index, index + Math.ceil(Math.random() * 2) + 1).join("");
      index += chunk.length;

      const list = this.data.messageList.map((m) => {
        if (m.id === msgId) {
          return { ...m, displayText: (m.displayText || "") + chunk };
        }
        return m;
      });
      this.setData({ messageList: list, scrollToId: "bottom-anchor" });
    }, 30);
  },

  finishTyping(msgId) {
    this.stopTyping();
    const list = this.data.messageList.map((m) => {
      if (m.id === msgId) {
        return { ...m, displayText: m.content, typing: false };
      }
      return m;
    });
    this.setData({ messageList: list, isTyping: false, scrollToId: "bottom-anchor" });
  },

  stopTyping() {
    if (this._typingTimer) {
      clearInterval(this._typingTimer);
      this._typingTimer = null;
    }
    this._typingMessageId = null;
  },

  /* ── 消息列表操作 ──────────────────────────── */

  pushMessage(msg) {
    const list = [...this.data.messageList, msg];
    this.setData({ messageList: list, scrollToId: "bottom-anchor" });
  },

  markMessageFailed(msgId) {
    const list = this.data.messageList.map((m) => {
      if (m.id === msgId) {
        return { ...m, failed: true };
      }
      return m;
    });
    this.setData({ messageList: list });
  },

  markMessageSent(msgId) {
    const list = this.data.messageList.map((m) => {
      if (m.id === msgId) {
        return { ...m, failed: false };
      }
      return m;
    });
    this.setData({ messageList: list });
  },

  /* ── 工具 ──────────────────────────────────── */

  generateClientMessageId() {
    const ts = Date.now().toString(36);
    const rnd = Math.random().toString(36).substring(2, 8);
    return `${ts}-${rnd}`;
  },
});

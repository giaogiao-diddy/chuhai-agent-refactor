"use strict";

const app = getApp();
const { get, post } = require("../../utils/api");

Page({
  data: {
    questions: [],          // 18 道题
    currentIndex: 0,        // 当前题号 (0-based)
    answers: {},            // { questionId: { optionId, answerText, score } }
    selectedOptionId: null, // 当前题目已选选项
    textAnswer: "",         // 当前文本题答案
    totalQuestions: 18,
    submittingText: false
  },

  async onLoad() {
    wx.showLoading({ title: "加载题目" });

    const { data, error } = await get("/api/questions");

    wx.hideLoading();

    if (error) {
      wx.showToast({ title: "加载失败: " + error, icon: "none" });
      return;
    }

    const questions = data.questions || [];

    // 恢复已有答案（回退修改场景）
    const answers = this.restoreAnswers();

    this.setData({
      questions: questions,
      totalQuestions: questions.length,
      answers: answers,
      selectedOptionId: answers[questions[0]?.id]?.optionId || null,
      textAnswer: answers[questions[0]?.id]?.answerText || ""
    });
  },

  /** 从本地存储恢复答案 */
  restoreAnswers() {
    const assessmentId = app.globalData.assessmentId;
    if (!assessmentId) return {};

    try {
      const key = `answers_${assessmentId}`;
      const saved = wx.getStorageSync(key);
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  },

  /** 文本题输入 */
  onTextInput(e) {
    this.setData({ textAnswer: e.detail.value || "" });
  },

  /** 提交文本题并前进 */
  async submitTextAnswer() {
    const question = this.data.questions[this.data.currentIndex];
    const assessmentId = app.globalData.assessmentId;
    const answerText = (this.data.textAnswer || "").trim();

    if (!assessmentId) {
      wx.showToast({ title: "测评信息丢失，请返回重试", icon: "none" });
      return;
    }

    if (!answerText) {
      wx.showToast({ title: "请输入行业信息", icon: "none" });
      return;
    }

    this.setData({ submittingText: true });

    const { error } = await post(`/api/assessments/${assessmentId}/answers`, {
      question_id: question.id,
      answer_text: answerText
    });

    this.setData({ submittingText: false });

    if (error) {
      wx.showToast({ title: "提交失败: " + error, icon: "none" });
      return;
    }

    const answers = { ...this.data.answers };
    answers[question.id] = { answerText, score: 0 };
    this.setData({ answers });
    this.saveAnswers(answers);
    this.goNext();
  },

  /** 保存答案到本地存储 */
  saveAnswers(answers) {
    const assessmentId = app.globalData.assessmentId;
    if (!assessmentId) return;

    try {
      const key = `answers_${assessmentId}`;
      wx.setStorageSync(key, JSON.stringify(answers));
    } catch {
      // 静默失败
    }
  },

  /** 点击选项 → 提交答案并前进 */
  async selectOption(e) {
    const optionId = e.currentTarget.dataset.optionId;
    const question = this.data.questions[this.data.currentIndex];
    const assessmentId = app.globalData.assessmentId;

    if (!assessmentId) {
      wx.showToast({ title: "测评信息丢失，请返回重试", icon: "none" });
      return;
    }

    if (!question.is_scored) {
      return;
    }

    // 找到对应选项的分数
    const option = question.options.find(o => o.id === optionId);
    if (!option) return;

    // 乐观更新 UI
    this.setData({ selectedOptionId: optionId });

    // 提交答案到后端（逐题保存）
    const { error } = await post(`/api/assessments/${assessmentId}/answers`, {
      question_id: question.id,
      option_id: optionId
    });

    if (error) {
      wx.showToast({ title: "提交失败: " + error, icon: "none" });
      return;
    }

    // 记录答案
    const answers = { ...this.data.answers };
    answers[question.id] = { optionId, score: option.score };
    this.setData({ answers });
    this.saveAnswers(answers);

    // 延迟跳转，让用户看到选中状态
    setTimeout(() => {
      this.goNext();
    }, 300);
  },

  /** 前进到下一题 */
  goNext() {
    const { currentIndex, totalQuestions } = this.data;

    if (currentIndex >= totalQuestions - 1) {
      // 最后一题 → 提交完成
      this.completeAssessment();
      return;
    }

    const nextIndex = currentIndex + 1;
    const nextQuestion = this.data.questions[nextIndex];
    const savedAnswer = this.data.answers[nextQuestion.id] || {};
    this.setData({
      currentIndex: nextIndex,
      selectedOptionId: savedAnswer.optionId || null,
      textAnswer: savedAnswer.answerText || ""
    });
  },

  /** 返回上一题 */
  goPrev() {
    if (this.data.currentIndex <= 0) return;

    const prevIndex = this.data.currentIndex - 1;
    const prevQuestion = this.data.questions[prevIndex];
    const savedAnswer = this.data.answers[prevQuestion.id] || {};
    this.setData({
      currentIndex: prevIndex,
      selectedOptionId: savedAnswer.optionId || null,
      textAnswer: savedAnswer.answerText || ""
    });
  },

  /** 完成测评 */
  async completeAssessment() {
    const assessmentId = app.globalData.assessmentId;

    wx.showLoading({ title: "提交测评", mask: true });

    const { data, error } = await post(`/api/assessments/${assessmentId}/complete`, {});

    wx.hideLoading();

    if (error) {
      wx.showToast({ title: "提交失败: " + error, icon: "none" });
      return;
    }

    // 清理本地答案缓存
    try {
      wx.removeStorageSync(`answers_${assessmentId}`);
    } catch {
      // 静默
    }

    // 跳转到报告生成中页面
    wx.redirectTo({
      url: `/pages/report-generating/report-generating?assessment_id=${assessmentId}&score=${data.display_score || data.total_score || 0}&tag=${encodeURIComponent(data.tag || "")}`
    });
  }
});

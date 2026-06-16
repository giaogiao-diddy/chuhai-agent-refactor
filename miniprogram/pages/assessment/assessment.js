"use strict";

const app = getApp();
const { get, post } = require("../../utils/api");

Page({
  data: {
    questions: [],
    questionNavItems: [],
    currentIndex: 0,
    answers: {},
    selectedOptionId: null,
    textAnswer: "",
    totalQuestions: 0,
    submittingText: false,
    submittingOption: false,
    completing: false
  },

  async onLoad(options) {
    // 优先从 URL 参数读 assessmentId，回退到 globalData
    const assessmentId = Number(options.assessment_id) || app.globalData.assessmentId || null;
    if (assessmentId) {
      app.globalData.assessmentId = assessmentId;
    }

    wx.showLoading({ title: "加载题目" });

    const { data, error } = await get("/api/questions");

    wx.hideLoading();

    if (error) {
      wx.showToast({ title: "加载失败: " + error, icon: "none" });
      return;
    }

    const questions = data.questions || [];
    const answers = this.restoreAnswers();

    this.setData({
      questions: questions,
      questionNavItems: this.buildQuestionNavItems(questions, answers),
      totalQuestions: questions.length,
      answers: answers,
      selectedOptionId: answers[questions[0]?.id]?.optionId || null,
      textAnswer: answers[questions[0]?.id]?.answerText || ""
    });
  },

  /* ── 答案持久化 ──────────────────────────────── */

  restoreAnswers() {
    const id = app.globalData.assessmentId;
    if (!id) return {};
    try {
      const saved = wx.getStorageSync(`answers_${id}`);
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  },

  saveAnswers(answers) {
    const id = app.globalData.assessmentId;
    if (!id) return;
    try {
      wx.setStorageSync(`answers_${id}`, JSON.stringify(answers));
    } catch { /* 静默 */ }
  },

  /* ── 题号导航 ────────────────────────────────── */

  buildQuestionNavItems(questions, answers) {
    return questions.map((q, i) => ({
      index: i,
      number: i + 1,
      answered: q.is_scored === false
        ? !!(answers[q.id]?.answerText || "").trim()
        : !!answers[q.id]?.optionId
    }));
  },

  refreshNav(answers) {
    this.setData({
      questionNavItems: this.buildQuestionNavItems(this.data.questions, answers)
    });
  },

  /* ── 题目跳转 ────────────────────────────────── */

  goToIndex(index) {
    const q = this.data.questions[index];
    const a = this.data.answers[q.id] || {};
    this.setData({
      currentIndex: index,
      selectedOptionId: a.optionId || null,
      textAnswer: a.answerText || ""
    });
  },

  jumpToQuestion(e) {
    if (this.data.submittingText || this.data.submittingOption) return;
    const index = Number(e.currentTarget.dataset.index);
    if (Number.isNaN(index) || index < 0 || index >= this.data.questions.length) return;
    this.goToIndex(index);
  },

  /* ── 上一题 ──────────────────────────────────── */

  goPrev() {
    if (this.data.currentIndex <= 0) return;
    this.goToIndex(this.data.currentIndex - 1);
  },

  /* ── 文本题 ──────────────────────────────────── */

  onTextInput(e) {
    this.setData({ textAnswer: e.detail.value || "" });
  },

  async submitTextAnswer() {
    const q = this.data.questions[this.data.currentIndex];
    const assessmentId = app.globalData.assessmentId;
    const text = (this.data.textAnswer || "").trim();

    if (!assessmentId) {
      wx.showToast({ title: "测评信息丢失，请返回重试", icon: "none" });
      return;
    }
    if (!text) {
      wx.showToast({ title: "请输入行业信息", icon: "none" });
      return;
    }
    if (this.data.submittingText) return;

    this.setData({ submittingText: true });

    const { error } = await post(`/api/assessments/${assessmentId}/answers`, {
      question_id: q.id,
      answer_text: text
    });

    this.setData({ submittingText: false });

    if (error) {
      wx.showToast({ title: "提交失败: " + error, icon: "none" });
      return;
    }

    const answers = { ...this.data.answers };
    answers[q.id] = { answerText: text, score: 0 };
    this.setData({ answers });
    this.refreshNav(answers);
    this.saveAnswers(answers);
    this.goNextUnansweredOrNext();
  },

  /* ── 计分题选项 ──────────────────────────────── */

  async selectOption(e) {
    if (this.data.submittingOption) return;

    const optionId = e.currentTarget.dataset.optionId;
    const q = this.data.questions[this.data.currentIndex];
    const assessmentId = app.globalData.assessmentId;

    if (!assessmentId) {
      wx.showToast({ title: "测评信息丢失，请返回重试", icon: "none" });
      return;
    }
    if (q.is_scored === false) return;

    const option = q.options.find(o => o.id === optionId);
    if (!option) return;

    this.setData({ selectedOptionId: optionId, submittingOption: true });

    const { error } = await post(`/api/assessments/${assessmentId}/answers`, {
      question_id: q.id,
      option_id: optionId
    });

    this.setData({ submittingOption: false });

    if (error) {
      wx.showToast({ title: "提交失败: " + error, icon: "none" });
      return;
    }

    const answers = { ...this.data.answers };
    answers[q.id] = { optionId, score: option.score };
    this.setData({ answers });
    this.refreshNav(answers);
    this.saveAnswers(answers);

    setTimeout(() => this.goNextUnansweredOrNext(), 300);
  },

  /* ── 自动跳转逻辑 ────────────────────────────── */

  isAnswered(question) {
    if (!question) return false;
    const a = this.data.answers[question.id];
    if (!a) return false;
    return question.is_scored === false
      ? !!(a.answerText || "").trim()
      : !!a.optionId;
  },

  findNextUnansweredIndex() {
    const { questions, currentIndex } = this.data;
    for (let i = currentIndex + 1; i < questions.length; i += 1) {
      if (!this.isAnswered(questions[i])) return i;
    }
    return -1;
  },

  findAnyUnansweredIndex() {
    const { questions } = this.data;
    for (let i = 0; i < questions.length; i += 1) {
      if (!this.isAnswered(questions[i])) return i;
    }
    return -1;
  },

  goNextUnansweredOrNext() {
    const next = this.findNextUnansweredIndex();
    if (next >= 0) {
      this.goToIndex(next);
      return;
    }
    const any = this.findAnyUnansweredIndex();
    if (any >= 0) {
      this.goToIndex(any);
      return;
    }
    this.completeAssessment();
  },

  /* ── 完成测评 ────────────────────────────────── */

  async completeAssessment() {
    if (this.data.completing) return;
    const assessmentId = app.globalData.assessmentId;

    this.setData({ completing: true });
    wx.showLoading({ title: "提交测评", mask: true });

    const { data, error } = await post(`/api/assessments/${assessmentId}/complete`, {});

    wx.hideLoading();

    if (error) {
      this.setData({ completing: false });
      wx.showToast({ title: "提交失败: " + error, icon: "none" });
      return;
    }

    try { wx.removeStorageSync(`answers_${assessmentId}`); } catch { /* 静默 */ }

    wx.redirectTo({
      url: `/pages/report-generating/report-generating?assessment_id=${assessmentId}&score=${data.display_score || data.total_score || 0}&tag=${encodeURIComponent(data.tag || "")}`
    });
  }
});

"use strict";

const app = getApp();
const { call } = require("../../utils/cloudApi");

Page({
  data: {
    questions: [],
    questionNavItems: [],
    currentIndex: 0,
    answers: {},
    selectedOptionId: null,
    selectedOptionIds: [],
    currentOptions: [],
    textAnswer: "",
    totalQuestions: 0,
    branch: null,
    submittingText: false,
    submittingOption: false,
    completing: false
  },

  async onLoad(options) {
    const assessmentId = options.assessment_id || app.globalData.assessmentId || null;
    if (assessmentId) {
      app.globalData.assessmentId = assessmentId;
    }
    await this.loadQuestionFlow();
  },

  async loadQuestionFlow(branch) {
    const assessmentId = app.globalData.assessmentId;
    wx.showLoading({ title: "加载题目" });

    const { data, error } = await call("getQuestionFlow", {
      assessment_id: assessmentId,
      branch: branch || this.data.branch
    });

    wx.hideLoading();

    if (error || !data || !data.ok) {
      wx.showToast({ title: "加载失败", icon: "none" });
      return;
    }

    const questions = data.questions || [];
    const answers = this.filterAnswersForQuestions(this.restoreAnswers(), questions);
    this.setData({
      questions,
      questionNavItems: this.buildQuestionNavItems(questions, answers),
      totalQuestions: questions.length,
      answers,
      branch: data.branch || branch || this.data.branch || null,
      currentIndex: Math.min(this.data.currentIndex, Math.max(questions.length - 1, 0))
    });
    this.syncCurrentAnswerState();
  },

  filterAnswersForQuestions(answers, questions) {
    const validIds = new Set(questions.map((item) => item.id));
    return Object.keys(answers || {}).reduce((result, key) => {
      if (validIds.has(key)) {
        result[key] = answers[key];
      }
      return result;
    }, {});
  },

  restoreAnswers() {
    const id = app.globalData.assessmentId;
    if (!id) return {};
    try {
      const saved = wx.getStorageSync(`answers_${id}`);
      return saved ? JSON.parse(saved) : {};
    } catch (err) {
      return {};
    }
  },

  saveAnswers(answers) {
    const id = app.globalData.assessmentId;
    if (!id) return;
    try {
      wx.setStorageSync(`answers_${id}`, JSON.stringify(answers));
    } catch (err) {
      // ignore storage failures
    }
  },

  buildQuestionNavItems(questions, answers) {
    return questions.map((question, index) => ({
      index,
      number: index + 1,
      answered: this.isAnswerComplete(question, answers[question.id])
    }));
  },

  refreshNav(answers) {
    this.setData({
      questionNavItems: this.buildQuestionNavItems(this.data.questions, answers)
    });
  },

  syncCurrentAnswerState() {
    const question = this.data.questions[this.data.currentIndex];
    const answer = question ? this.data.answers[question.id] || {} : {};
    const selectedIds = answer.optionIds || [];
    const currentOptions = (question && question.options ? question.options : []).map((option) => ({
      ...option,
      checked: selectedIds.indexOf(option.id) >= 0
    }));
    this.setData({
      selectedOptionId: answer.optionId || null,
      selectedOptionIds: selectedIds,
      textAnswer: answer.answerText || "",
      currentOptions
    });
  },

  goToIndex(index) {
    if (index < 0 || index >= this.data.questions.length) return;
    this.setData({ currentIndex: index }, () => this.syncCurrentAnswerState());
  },

  jumpToQuestion(e) {
    if (this.data.submittingText || this.data.submittingOption) return;
    const index = Number(e.currentTarget.dataset.index);
    if (Number.isNaN(index)) return;
    this.goToIndex(index);
  },

  goPrev() {
    if (this.data.currentIndex <= 0) return;
    this.goToIndex(this.data.currentIndex - 1);
  },

  onTextInput(e) {
    this.setData({ textAnswer: e.detail.value || "" });
  },

  async submitTextAnswer() {
    const question = this.data.questions[this.data.currentIndex];
    const text = (this.data.textAnswer || "").trim();
    if (!text) {
      wx.showToast({ title: "请先填写内容", icon: "none" });
      return;
    }
    await this.submitAnswer({
      question_id: question.id,
      answer_text: text
    }, {
      answerText: text
    });
  },

  async selectOption(e) {
    if (this.data.submittingOption) return;
    const optionId = e.currentTarget.dataset.optionId;
    const question = this.data.questions[this.data.currentIndex];
    if (!question || question.type !== "single_choice") return;

    const option = question.options.find((item) => item.id === optionId);
    if (!option) return;

    this.setData({ selectedOptionId: optionId });
    await this.submitAnswer({
      question_id: question.id,
      option_id: optionId
    }, {
      optionId,
      score: option.feasibility_score || 0
    });
  },

  toggleMultiOption(e) {
    const optionId = e.currentTarget.dataset.optionId;
    const selected = this.data.selectedOptionIds.slice();
    const index = selected.indexOf(optionId);
    if (index >= 0) {
      selected.splice(index, 1);
    } else {
      selected.push(optionId);
    }
    this.setData({ selectedOptionIds: selected });
    const currentOptions = this.data.currentOptions.map((option) => ({
      ...option,
      checked: selected.indexOf(option.id) >= 0
    }));
    this.setData({ currentOptions });
  },

  async submitMultiAnswer() {
    const question = this.data.questions[this.data.currentIndex];
    const optionIds = this.data.selectedOptionIds;
    if (!optionIds.length) {
      wx.showToast({ title: "请至少选择一项", icon: "none" });
      return;
    }
    const score = (question.options || [])
      .filter((item) => optionIds.includes(item.id))
      .reduce((sum, item) => sum + (item.feasibility_score || 0), 0);
    await this.submitAnswer({
      question_id: question.id,
      option_ids: optionIds
    }, {
      optionIds,
      score
    });
  },

  async submitAnswer(payload, localAnswer) {
    const assessmentId = app.globalData.assessmentId;
    const question = this.data.questions[this.data.currentIndex];
    if (!assessmentId || !question) {
      wx.showToast({ title: "测评信息丢失，请返回重试", icon: "none" });
      return;
    }
    if (this.data.submittingOption || this.data.submittingText) return;

    const loadingKey = question.type === "text" ? "submittingText" : "submittingOption";
    this.setData({ [loadingKey]: true });

    const { data, error } = await call("submitAnswer", {
      assessment_id: assessmentId,
      ...payload
    });

    this.setData({ [loadingKey]: false });

    if (error || !data || !data.ok) {
      wx.showToast({ title: error || "提交失败", icon: "none" });
      return;
    }

    const answers = { ...this.data.answers };
    answers[question.id] = localAnswer;
    this.setData({ answers });
    this.refreshNav(answers);
    this.saveAnswers(answers);

    if (data.branch && data.branch !== this.data.branch) {
      this.setData({ branch: data.branch, currentIndex: this.data.currentIndex + 1 });
      await this.loadQuestionFlow(data.branch);
      this.goNextUnansweredOrNext();
      return;
    }

    setTimeout(() => this.goNextUnansweredOrNext(), 250);
  },

  isAnswerComplete(question, answer) {
    if (!question || !answer) return false;
    if (question.type === "text" || question.type === "url") {
      return !!(answer.answerText || "").trim();
    }
    if (question.type === "multiple_choice") {
      return Array.isArray(answer.optionIds) && answer.optionIds.length > 0;
    }
    if (question.type === "single_choice") {
      return !!answer.optionId;
    }
    return false;
  },

  isAnswered(question) {
    return this.isAnswerComplete(question, this.data.answers[question.id]);
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

  async completeAssessment() {
    if (this.data.completing) return;
    const assessmentId = app.globalData.assessmentId;
    this.setData({ completing: true });
    wx.showLoading({ title: "生成报告", mask: true });

    const { data, error } = await call("completeAssessment", {
      assessment_id: assessmentId
    });

    wx.hideLoading();

    if (error || !data || !data.ok) {
      this.setData({ completing: false });
      const missing = data && Array.isArray(data.missing_question_ids) ? data.missing_question_ids.length : 0;
      wx.showToast({ title: missing ? `还有${missing}题未完成` : (error || "提交失败"), icon: "none" });
      return;
    }

    try {
      wx.removeStorageSync(`answers_${assessmentId}`);
    } catch (err) {
      // ignore storage failures
    }

    wx.redirectTo({
      url: `/pages/report-partial/report-partial?assessment_id=${assessmentId}&score=${data.feasibility_score || 0}&tag=${encodeURIComponent(data.feasibility_tag || "")}`
    });
  }
});

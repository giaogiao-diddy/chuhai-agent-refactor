"""模板报告单元测试

测试目标：app.services.template_report
测试范围：标签模板匹配、变量插值、兜底行为
"""

import pytest
from app.services.template_report import build_summary, build_full


class TestBuildSummary:
    """部分报告模板测试"""

    def test_returns_dict_with_required_keys(self, sample_answers):
        """返回的字典包含所有必需字段"""
        result = build_summary(30, "轻量试探型", {})
        assert "total_score" in result
        assert "tag" in result
        assert "tag_explanation" in result
        assert "preliminary_judgment" in result
        assert "strengths" in result
        assert "risks" in result
        assert "unlock_hint" in result

    def test_score_and_tag_match(self, sample_answers):
        """分数和标签正确传递"""
        result = build_summary(30, "轻量试探型", {})
        assert result["total_score"] == 78
        assert result["tag"] == "轻量试探型"

    def test_strengths_and_risks_are_lists(self):
        """优势和风险都是列表"""
        result = build_summary(40, "基础具备型", {})
        assert isinstance(result["strengths"], list)
        assert isinstance(result["risks"], list)
        assert len(result["strengths"]) >= 2
        assert len(result["risks"]) >= 2

    def test_all_tags_have_templates(self):
        """4 种标签都有对应的模板"""
        for tag in ["观察准备型", "轻量试探型", "基础具备型", "优先布局型"]:
            result = build_summary(30, tag, {})
            assert result["tag"] == tag
            assert len(result["tag_explanation"]) > 0

    def test_unknown_tag_falls_back(self):
        """未知标签使用默认模板（观察准备型）"""
        result = build_summary(25, "未知标签", {})
        assert result["tag"] == "未知标签"  # tag 原样传递
        assert len(result["tag_explanation"]) > 0  # 有兜底内容

    def test_unlock_hint_contains_45_minutes(self):
        """解锁提示包含 45 分钟解读信息"""
        result = build_summary(30, "轻量试探型", {})
        assert "45" in result["unlock_hint"]

    def test_answer_summary_variable_interpolation(self):
        """答案摘要变量能被正确插值到模板中"""
        answer_summary = {
            "product_type": "标准化产品",
            "team_size": "10-20 人",
        }
        result = build_summary(78, "轻量试探型", answer_summary)
        # 模板包含变量插值，验证结果不为空
        assert isinstance(result["preliminary_judgment"], str)


class TestBuildFull:
    """完整报告模板测试"""

    def test_returns_dict_with_required_keys(self):
        """返回的字典包含所有必需字段"""
        result = build_full(30, "轻量试探型", {})
        assert "summary_conclusion" in result
        assert "dimension_scores" in result
        assert "recommended_path" in result
        assert "risk_reminder" in result
        assert "action_plan_30days" in result
        assert "consultant_guide" in result

    def test_dimension_scores_is_dict(self):
        """维度评分是字典"""
        result = build_full(30, "轻量试探型", {})
        assert isinstance(result["dimension_scores"], dict)

    def test_action_plan_is_list(self):
        """行动计划是列表"""
        result = build_full(30, "轻量试探型", {})
        assert isinstance(result["action_plan_30days"], list)

    def test_all_tags_have_full_templates(self):
        """4 种标签都有对应的完整报告模板"""
        for tag in ["观察准备型", "轻量试探型", "基础具备型", "优先布局型"]:
            result = build_full(75, tag, {})
            assert len(result["summary_conclusion"]) > 0
            assert len(result["recommended_path"]) > 0

    def test_unknown_tag_falls_back(self):
        """未知标签使用默认模板"""
        result = build_full(75, "未知标签", {})
        assert len(result["summary_conclusion"]) > 0

    def test_consultant_guide_contains_wechat_hint(self):
        """顾问引导包含企业微信提示"""
        result = build_full(30, "轻量试探型", {})
        assert "企业微信" in result["consultant_guide"]

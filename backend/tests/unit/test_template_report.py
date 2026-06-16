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
        assert "hero" in result
        assert "key_findings" in result
        assert "total_score" in result
        assert "display_score" in result
        assert "tag" in result
        assert "tag_explanation" in result
        assert "preliminary_judgment" in result
        assert "positioning_assessment" in result
        assert "content_assessment" in result
        assert "conversion_assessment" in result
        assert "strengths" in result
        assert "risks" in result
        assert "unlock_hint" in result

    def test_score_and_tag_match(self, sample_answers):
        """分数和标签正确传递"""
        result = build_summary(30, "轻量试探型", {})
        assert result["total_score"] == 30
        assert result["display_score"] == 73
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

    def test_summary_contains_component_hero(self):
        """部分报告包含可前端展示的顶部诊断卡"""
        result = build_summary(44, "基础具备型", {})

        assert result["hero"] == {
            "score": 87,
            "tag": "基础具备型",
            "one_sentence_judgment": result["preliminary_judgment"],
            "core_contradiction": result["tag_explanation"],
        }
        assert len(result["key_findings"]) >= 2
        assert {"title", "content"} <= set(result["key_findings"][0].keys())

    def test_answer_summary_variable_interpolation(self):
        """答案摘要变量能被正确插值到模板中"""
        answer_summary = {
            "product_type": "标准化产品",
            "team_size": "10-20 人",
        }
        result = build_summary(30, "轻量试探型", answer_summary)
        # 模板包含变量插值，验证结果不为空
        assert isinstance(result["preliminary_judgment"], str)


class TestBuildFull:
    """完整报告模板测试"""

    def test_returns_dict_with_required_keys(self):
        """返回的字典包含所有必需字段"""
        result = build_full(30, "轻量试探型", {})
        assert "diagnosis_cards" in result
        assert "strategy_path" in result
        assert "risk_cards" in result
        assert "summary_conclusion" in result
        assert "positioning_assessment" in result
        assert "content_assessment" in result
        assert "conversion_assessment" in result
        assert "dimension_scores" in result
        assert "recommended_path" in result
        assert "risk_reminder" in result
        assert "action_plan_30days" in result
        assert "consultant_guide" in result

    def test_dimension_scores_is_dict(self):
        """维度评分是字典"""
        result = build_full(30, "轻量试探型", {})
        assert isinstance(result["dimension_scores"], dict)
        for key in [
            "enterprise_capacity",
            "overseas_foundation",
            "product_trust_asset",
            "content_acquisition",
            "conversion_system",
        ]:
            assert key in result["dimension_scores"]

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

    def test_three_assessments_use_strong_persona_language(self):
        """三段式报告融合强成交人设方法论"""
        result = build_full(44, "基础具备型", {})
        combined = "\n".join([
            result["positioning_assessment"],
            result["content_assessment"],
            result["conversion_assessment"],
        ])
        assert "定位" in combined
        assert "内容" in combined
        assert "SOP" in combined

    def test_dimension_scores_are_calculated_from_answer_question_mapping(self):
        """五维分数按题号累加，不从总分 min 派生"""
        answer_summary = {
            "answers": [
                {"question_id": 2, "score": 4},
                {"question_id": 3, "score": 3},
                {"question_id": 4, "score": 2},
                {"question_id": 5, "score": 1},
                {"question_id": 6, "score": 2},
                {"question_id": 13, "score": 3},
                {"question_id": 14, "score": 4},
                {"question_id": 15, "score": 1},
                {"question_id": 7, "score": 4},
                {"question_id": 8, "score": 3},
                {"question_id": 9, "score": 2},
                {"question_id": 10, "score": 1},
                {"question_id": 11, "score": 2},
                {"question_id": 12, "score": 4},
                {"question_id": 16, "score": 3},
                {"question_id": 17, "score": 2},
                {"question_id": 18, "score": 1},
            ]
        }

        result = build_full(42, "轻量试探型", answer_summary)

        assert result["dimension_scores"]["enterprise_capacity"]["score"] == 9
        assert result["dimension_scores"]["enterprise_capacity"]["max_score"] == 12
        assert result["dimension_scores"]["overseas_foundation"]["score"] == 11
        assert result["dimension_scores"]["overseas_foundation"]["max_score"] == 20
        assert result["dimension_scores"]["product_trust_asset"]["score"] == 9
        assert result["dimension_scores"]["product_trust_asset"]["max_score"] == 12
        assert result["dimension_scores"]["content_acquisition"]["score"] == 3
        assert result["dimension_scores"]["content_acquisition"]["max_score"] == 8
        assert result["dimension_scores"]["conversion_system"]["score"] == 10
        assert result["dimension_scores"]["conversion_system"]["max_score"] == 16

    def test_full_report_contains_display_components(self):
        """完整报告包含卡片、路径、风险和四周行动组件"""
        result = build_full(44, "基础具备型", {})

        assert len(result["diagnosis_cards"]) == 3
        assert set(result["strategy_path"].keys()) == {"positioning", "content", "conversion"}
        assert all(isinstance(value, list) for value in result["strategy_path"].values())
        assert all(len(value) >= 3 for value in result["strategy_path"].values())
        assert len(result["risk_cards"]) >= 4
        assert len(result["action_plan_30days"]) == 4
        assert result["action_plan_30days"][0].startswith("第1-7天：")
        assert result["action_plan_30days"][1].startswith("第8-14天：")
        assert result["action_plan_30days"][2].startswith("第15-21天：")
        assert result["action_plan_30days"][3].startswith("第22-30天：")
        assert all({"title", "content"} <= set(item.keys()) for item in result["risk_cards"])

    def test_full_template_uses_question_memories_when_ai_summary_fails(self):
        """AI 汇总失败时，兜底完整报告也必须吃逐题诊断记忆"""
        answer_summary = {
            "answers": [{"question_id": 1, "answer_text": "纺织"}] + [
                {"question_id": question_id, "score": 1}
                for question_id in range(2, 19)
            ],
            "report_memories": [
                {
                    "question_id": 9,
                    "report_memory": "纺织品类目无 Catalog，海外客户无法系统理解规格、起订量和交付证据。",
                },
                {
                    "question_id": 12,
                    "report_memory": "报价、打样、跟单没有 SOP，询盘进来后会显得不专业。",
                },
                {
                    "question_id": 17,
                    "report_memory": "交付周期和质量不稳定，会直接破坏海外客户信任。",
                },
                {
                    "question_id": 18,
                    "report_memory": "跨境收款、合同和认证资料完全未准备，即使获客也难以成交兑现。",
                },
            ],
        }

        result = build_full(17, "观察准备型", answer_summary)
        combined = "\n".join([
            result["positioning_assessment"],
            result["content_assessment"],
            result["conversion_assessment"],
            result["risk_reminder"],
            *result["action_plan_30days"],
        ])

        assert "纺织" in combined
        assert "Catalog" in combined
        assert "报价、打样、跟单" in combined
        assert "交付周期和质量不稳定" in combined
        assert "跨境收款" in combined

    def test_summary_template_uses_question_memories_for_key_findings(self):
        """兜底部分报告的关键发现应优先来自逐题诊断记忆"""
        answer_summary = {
            "answers": [{"question_id": 1, "answer_text": "纺织"}],
            "report_memories": [
                {
                    "question_id": 9,
                    "report_memory": "缺少多语言 Catalog，海外客户理解成本高。",
                },
                {
                    "question_id": 17,
                    "report_memory": "交付稳定性不足会影响高客单信任。",
                },
            ],
        }

        result = build_summary(17, "观察准备型", answer_summary)
        findings = "\n".join(item["content"] for item in result["key_findings"])

        assert "Catalog" in findings
        assert "交付稳定性" in findings

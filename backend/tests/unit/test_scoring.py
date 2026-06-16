"""评分规则单元测试 v2.0

测试目标：app.services.scoring_service
测试范围：分数计算（原始分 17-68，17 题计分）、标签映射（4 档）、边界条件
"""

import pytest
from app.services.scoring_service import calculate_score_and_tag, calculate_total, score_to_tag


class TestCalculateTotal:
    """分数计算测试 — 17 题计分（第 1 题行业不计分）"""

    def test_all_score_2_returns_34(self, sample_answers):
        """17 题每题 2 分，总分应为 34"""
        total = calculate_total(sample_answers)
        assert total == 34

    def test_all_score_1_returns_17(self, answers_all_min):
        """17 题每题 1 分，总分应为 17（最小）"""
        total = calculate_total(answers_all_min)
        assert total == 17

    def test_all_score_4_returns_68(self, answers_all_max):
        """17 题每题 4 分，总分应为 68（最大）"""
        total = calculate_total(answers_all_max)
        assert total == 68

    def test_empty_answers_returns_0(self):
        """空列表返回 0"""
        assert calculate_total([]) == 0

    def test_mixed_scores(self):
        """混合分数累加，score=0 的行业题不参与计分"""
        answers = [
            {"question_id": 1, "option_id": None, "answer_text": "智能硬件", "score": 0},
            {"question_id": 2, "option_id": 2, "score": 4},
            {"question_id": 3, "option_id": 3, "score": 2},
        ]
        assert calculate_total(answers) == 6


class TestScoreToTag:
    """标签映射测试 — 4 档标签（v2.0：17 题计分）

    原始分 → 展示分 → 标签：
      17-30 → 60-73 → 观察准备型
      31-43 → 74-86 → 轻量试探型
      44-56 → 87-99 → 基础具备型
      57-68 → 100-111 → 优先布局型
    """

    @pytest.mark.parametrize("raw_score,expected_tag", [
        (17, "观察准备型"), (25, "观察准备型"), (30, "观察准备型"),
        (31, "轻量试探型"), (38, "轻量试探型"), (43, "轻量试探型"),
        (44, "基础具备型"), (50, "基础具备型"), (56, "基础具备型"),
        (57, "优先布局型"), (62, "优先布局型"), (68, "优先布局型"),
    ])
    def test_tag_mapping(self, raw_score, expected_tag):
        """分数到标签的映射正确"""
        tag, _ = score_to_tag(raw_score)
        assert tag == expected_tag

    def test_tag_has_description(self):
        for score in [25, 38, 50, 62]:
            _, desc = score_to_tag(score)
            assert isinstance(desc, str) and len(desc) > 5

    def test_boundary_17(self): assert score_to_tag(17)[0] == "观察准备型"
    def test_boundary_30(self): assert score_to_tag(30)[0] == "观察准备型"
    def test_boundary_31(self): assert score_to_tag(31)[0] == "轻量试探型"
    def test_boundary_43(self): assert score_to_tag(43)[0] == "轻量试探型"
    def test_boundary_44(self): assert score_to_tag(44)[0] == "基础具备型"
    def test_boundary_56(self): assert score_to_tag(56)[0] == "基础具备型"
    def test_boundary_57(self): assert score_to_tag(57)[0] == "优先布局型"
    def test_boundary_68(self): assert score_to_tag(68)[0] == "优先布局型"


class TestDisplayMapping:
    """展示分映射测试 v2.0"""

    def test_display_score_mapping(self):
        """display = raw + 43"""
        assert 17 + 43 == 60   # 最小展示分
        assert 68 + 43 == 111  # 最大展示分

    def test_tag_display_ranges(self):
        display_map = {
            "观察准备型": range(60, 74),
            "轻量试探型": range(74, 87),
            "基础具备型": range(87, 100),
            "优先布局型": range(100, 112),
        }
        for tag_name, display_range in display_map.items():
            assert display_range.start in range(60, 112)


class TestCalculateScoreAndTag:
    """总分、展示分、标签一体计算测试"""

    def test_min_score_maps_to_display_60(self, answers_all_min):
        result = calculate_score_and_tag(answers_all_min)
        assert result["raw_score"] == 17
        assert result["display_score"] == 60
        assert result["tag"] == "观察准备型"

    def test_max_score_maps_to_display_111(self, answers_all_max):
        result = calculate_score_and_tag(answers_all_max)
        assert result["raw_score"] == 68
        assert result["display_score"] == 111
        assert result["tag"] == "优先布局型"

    def test_boundary_30_and_31(self):
        answers_30 = [{"question_id": i, "score": 2} for i in range(2, 15)]
        answers_30.extend({"question_id": i, "score": 1} for i in range(15, 19))
        result_30 = calculate_score_and_tag(answers_30)
        assert result_30["raw_score"] == 30
        assert result_30["tag"] == "观察准备型"

        answers_31 = [{"question_id": i, "score": 2} for i in range(2, 16)]
        answers_31.extend({"question_id": i, "score": 1} for i in range(16, 19))
        result_31 = calculate_score_and_tag(answers_31)
        assert result_31["raw_score"] == 31
        assert result_31["tag"] == "轻量试探型"

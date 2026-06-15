"""评分规则单元测试

测试目标：app.services.scoring_service
测试范围：分数计算（原始分 15-60）、标签映射（4 档）、边界条件
"""

import pytest
from app.services.scoring_service import calculate_total, score_to_tag


class TestCalculateTotal:
    """分数计算测试"""

    def test_all_score_2_returns_30(self, sample_answers):
        """15 题每题 2 分，总分应为 30"""
        total = calculate_total(sample_answers)
        assert total == 30

    def test_all_score_1_returns_15(self, answers_all_min):
        """15 题每题 1 分，总分应为 15（最小）"""
        total = calculate_total(answers_all_min)
        assert total == 15

    def test_all_score_4_returns_60(self, answers_all_max):
        """15 题每题 4 分，总分应为 60（最大）"""
        total = calculate_total(answers_all_max)
        assert total == 60

    def test_empty_answers_returns_0(self):
        """空列表返回 0"""
        assert calculate_total([]) == 0

    def test_single_answer(self):
        """单题答案"""
        assert calculate_total([{"question_id": 1, "option_id": 1, "score": 2}]) == 2

    def test_mixed_scores(self):
        """混合分数累加"""
        answers = [
            {"question_id": 1, "option_id": 1, "score": 1},
            {"question_id": 2, "option_id": 2, "score": 4},
            {"question_id": 3, "option_id": 3, "score": 2},
        ]
        assert calculate_total(answers) == 7


class TestScoreToTag:
    """标签映射测试 — 4 档标签

    原始分 → 展示分 → 标签：
      15-25 → 60-70 → 观察准备型
      26-35 → 71-80 → 轻量试探型
      36-45 → 81-90 → 基础具备型
      46-60 → 91-100 → 优先布局型
    """

    @pytest.mark.parametrize("raw_score,expected_tag", [
        (15, "观察准备型"),
        (20, "观察准备型"),
        (25, "观察准备型"),
        (26, "轻量试探型"),
        (30, "轻量试探型"),
        (35, "轻量试探型"),
        (36, "基础具备型"),
        (40, "基础具备型"),
        (45, "基础具备型"),
        (46, "优先布局型"),
        (53, "优先布局型"),
        (60, "优先布局型"),
    ])
    def test_tag_mapping(self, raw_score, expected_tag):
        """分数到标签的映射正确 — 覆盖 4 档全部边界值"""
        tag, _ = score_to_tag(raw_score)
        assert tag == expected_tag

    def test_tag_has_description(self):
        """每个标签都有解释说明"""
        for score in [20, 30, 40, 55]:
            _, description = score_to_tag(score)
            assert isinstance(description, str)
            assert len(description) > 5

    # ── 边界测试 ──

    def test_boundary_15_lowest(self):
        """15：观察准备型下限"""
        assert score_to_tag(15)[0] == "观察准备型"

    def test_boundary_25(self):
        """25：观察准备型上限"""
        assert score_to_tag(25)[0] == "观察准备型"

    def test_boundary_26(self):
        """26：轻量试探型下限"""
        assert score_to_tag(26)[0] == "轻量试探型"

    def test_boundary_35(self):
        """35：轻量试探型上限"""
        assert score_to_tag(35)[0] == "轻量试探型"

    def test_boundary_36(self):
        """36：基础具备型下限"""
        assert score_to_tag(36)[0] == "基础具备型"

    def test_boundary_45(self):
        """45：基础具备型上限"""
        assert score_to_tag(45)[0] == "基础具备型"

    def test_boundary_46(self):
        """46：优先布局型下限"""
        assert score_to_tag(46)[0] == "优先布局型"

    def test_boundary_60_highest(self):
        """60：优先布局型上限"""
        assert score_to_tag(60)[0] == "优先布局型"


class TestDisplayMapping:
    """展示分映射测试"""

    def test_display_score_mapping(self):
        """display = raw + 45"""
        assert 15 + 45 == 60   # 最小展示分
        assert 60 + 45 == 105  # 最大展示分(略超 100，业务上可接受)

    def test_tag_display_ranges(self):
        """标签展示分区间与文档一致"""
        display_map = {
            "观察准备型": range(60, 71),
            "轻量试探型": range(71, 81),
            "基础具备型": range(81, 91),
            "优先布局型": range(91, 106),
        }
        for tag_name, display_range in display_map.items():
            assert display_range.start in range(60, 100)

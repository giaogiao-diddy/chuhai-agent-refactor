import pytest

from app.scoring.questionnaire import (
    ALL_QUESTIONS,
    EXPERIENCED_BRANCH,
    INEXPERIENCED_BRANCH,
    SCORED_QUESTIONS,
    UNALLOCATED_WEIGHT,
    Q1,
    Q5,
    Q8,
    Q26,
    Q27,
)


def test_q5_routes_abc_to_experienced_branch():
    for opt in Q5.options:
        if opt.id in ("A", "B", "C"):
            assert opt.next_branch == "experienced"


def test_q5_routes_d_to_inexperienced_branch():
    opt_d = next(o for o in Q5.options if o.id == "D")
    assert opt_d.next_branch == "inexperienced"


def test_experienced_branch_contains_q1_to_q31():
    ids = {q.id for q in EXPERIENCED_BRANCH.questions}
    assert "Q1" in ids
    assert "Q5" in ids
    assert "Q6" in ids
    assert "Q31" in ids


def test_inexperienced_branch_is_placeholder():
    assert len(INEXPERIENCED_BRANCH.questions) < len(EXPERIENCED_BRANCH.questions)
    inex_ids = {q.id for q in INEXPERIENCED_BRANCH.questions}
    assert "Q1" in inex_ids
    assert "Q5" in inex_ids
    assert "Q6" not in inex_ids


def test_q1_is_open_text_and_now_scored():
    assert Q1.kind == "open_text"
    assert Q1.is_scored is True
    assert Q1.options == []
    assert Q1.branch == "common"
    # Q1 信息完整度评分：F=2/L=3
    assert Q1.max_feasibility_score == 2
    assert Q1.max_lead_score == 3


def test_non_scored_questions_do_not_contribute_score():
    non_scored = [q for q in ALL_QUESTIONS if not q.is_scored]
    for q in non_scored:
        assert q.max_feasibility_score == 0
        assert q.max_lead_score == 0


def test_option_scores_do_not_exceed_question_max():
    for q in SCORED_QUESTIONS:
        for opt in q.options:
            assert opt.feasibility_score <= q.max_feasibility_score, (
                f"{q.id} {opt.id} F={opt.feasibility_score} > max={q.max_feasibility_score}"
            )
            assert opt.lead_score <= q.max_lead_score, (
                f"{q.id} {opt.id} L={opt.lead_score} > max={q.max_lead_score}"
            )


def test_scored_total_plus_unallocated_weight_is_100():
    f_scored = sum(q.max_feasibility_score for q in SCORED_QUESTIONS)
    l_scored = sum(q.max_lead_score for q in SCORED_QUESTIONS)

    assert f_scored + UNALLOCATED_WEIGHT["feasibility"]["delta"] == 100
    assert l_scored + UNALLOCATED_WEIGHT["lead"]["delta"] == 100


def test_scored_questions_have_options():
    for q in SCORED_QUESTIONS:
        if q.kind == "open_text":
            continue  # Q1 开放题，通过槽位信息完整度计分
        assert len(q.options) > 0, f"{q.id} 缺少选项"


def test_q5_d_scores_zero_and_marks_inexperienced():
    opt_d = next(o for o in Q5.options if o.id == "D")
    assert opt_d.feasibility_score == 0
    assert opt_d.lead_score == 0
    assert Q5.notes is not None


def test_q24_option_a_no_duplicate_platform():
    """Q24 A 不应出现「快手」重复录入（typo 防御）"""
    from app.scoring.questionnaire import ALL_QUESTIONS

    q24 = next(q for q in ALL_QUESTIONS if q.id == "Q24")
    opt_a = next(o for o in q24.options if o.id == "A")
    platforms = opt_a.text
    assert platforms.count("快手") == 1, (
        f"Q24 A 中「快手」出现了 {platforms.count('快手')} 次，疑似重复录入: {platforms}"
    )


def test_conflict_notes_include_missing_inexperienced_branch():
    assert Q5.conflict_note is not None
    assert Q8.conflict_note is not None
    assert Q27.conflict_note is not None
    assert Q26.conflict_note is not None


def test_question_ids_are_canonical():
    """最终题号集合对齐 scoring-design.md: Q1, Q2a-Q2c, Q3a-Q3c, Q4, Q5, Q6-Q31"""
    expected = {
        "Q1", "Q2a", "Q2b", "Q2c", "Q3a", "Q3b", "Q3c", "Q4", "Q5",
        "Q6", "Q7", "Q8", "Q9", "Q10a", "Q10b", "Q10c",
        "Q11", "Q12", "Q13", "Q14", "Q15", "Q16",
        "Q17", "Q18", "Q19", "Q20", "Q21",
        "Q22", "Q23", "Q24", "Q25", "Q26",
        "Q27", "Q28", "Q29",
        "Q30", "Q31",
    }
    actual = {q.id for q in ALL_QUESTIONS}
    missing = expected - actual
    extra = actual - expected
    assert not missing, f"缺少题号: {missing}"
    assert not extra, f"多余题号: {extra}"


def test_q26_uses_nine_options_by_current_decision():
    """已裁决：Q26 当前采用 9 项，不补「海外订单」"""
    assert len(Q26.options) == 9
    all_text = " ".join(o.text for o in Q26.options)
    assert "海外订单" not in all_text
    assert Q26.conflict_note is not None
    assert "9 项" in Q26.conflict_note or "裁决" in Q26.conflict_note


def test_q27_d_is_no_reception_channel():
    """Q27 D 是「暂无承接路径」，不是 K"""
    opt_d = next(o for o in Q27.options if o.id == "D")
    assert "承接路径" in opt_d.text or "暂时没有" in opt_d.text
    assert opt_d.feasibility_score == 0
    assert opt_d.lead_score == 0


def test_no_lowercase_option_ids():
    """所有 option_id 不包含小写字母"""
    for q in ALL_QUESTIONS:
        for opt in q.options:
            assert opt.id == opt.id.upper(), (
                f"{q.id} option {opt.id} 包含小写字母"
            )


def test_inexperienced_branch_only_contains_common_and_q5():
    """无出海经验分支只含 Q1-Q4 + Q5"""
    inex_ids = {q.id for q in INEXPERIENCED_BRANCH.questions}
    expected = {"Q1", "Q2a", "Q2b", "Q2c", "Q3a", "Q3b", "Q3c", "Q4", "Q5"}
    assert inex_ids == expected, f"无出海经验分支题号: {sorted(inex_ids)}"


def test_question_ids_are_unique():
    """ALL_QUESTIONS 中不得有重复题号（重复会静默覆盖 q_map）"""
    ids = [q.id for q in ALL_QUESTIONS]
    duplicates = sorted({qid for qid in ids if ids.count(qid) > 1})
    assert not duplicates, f"重复题号: {duplicates}"
    assert len(ids) == len(set(ids))


def test_option_ids_are_unique_within_each_question():
    """每道题的 options 中不得有重复 option_id（重复会导致多选题重复累加）"""
    for q in ALL_QUESTIONS:
        option_ids = [opt.id for opt in q.options]
        duplicates = sorted({oid for oid in option_ids if option_ids.count(oid) > 1})
        assert not duplicates, f"{q.id} 存在重复 option_id: {duplicates}"


# ── display mapping ──

def test_question_requires_display_fields():
    from pydantic import ValidationError
    from app.schemas.questionnaire import Question

    with pytest.raises(ValidationError):
        Question(
            id="QX", text="x", dimension="enterprise_base",
            kind="single_choice", options=[],
            max_feasibility_score=0, max_lead_score=0,
        )

    q = Question(
        id="QX", text="x", dimension="enterprise_base",
        kind="single_choice", options=[],
        max_feasibility_score=0, max_lead_score=0,
        display_id="QX", display_order=99,
    )
    assert q.sub_order == 1




def test_question_display_ids_cover_q1_to_q31():
    display_ids = {q.display_id for q in ALL_QUESTIONS}
    expected = {f"Q{n}" for n in range(1, 32)}
    assert display_ids == expected, f"display_id 应覆盖 Q1-Q31, 实际: {sorted(display_ids ^ expected)}"
    assert len(set(q.display_id for q in ALL_QUESTIONS)) == 31


def test_subquestions_share_display_id():
    q_map = {q.id: q for q in ALL_QUESTIONS}
    for qid in ("Q2a", "Q2b", "Q2c"):
        assert q_map[qid].display_id == "Q2"
        assert q_map[qid].display_order == 2
    assert q_map["Q2a"].sub_order == 1
    assert q_map["Q2b"].sub_order == 2
    assert q_map["Q2c"].sub_order == 3

    for qid in ("Q3a", "Q3b", "Q3c"):
        assert q_map[qid].display_id == "Q3"
        assert q_map[qid].display_order == 3
    assert q_map["Q3a"].sub_order == 1
    assert q_map["Q3b"].sub_order == 2
    assert q_map["Q3c"].sub_order == 3

    for qid in ("Q10a", "Q10b", "Q10c"):
        assert q_map[qid].display_id == "Q10"
        assert q_map[qid].display_order == 10
    assert q_map["Q10a"].sub_order == 1
    assert q_map["Q10b"].sub_order == 2
    assert q_map["Q10c"].sub_order == 3


def test_regular_questions_have_matching_display_id():
    sub_ids = {"Q2a","Q2b","Q2c","Q3a","Q3b","Q3c","Q10a","Q10b","Q10c"}
    for q in ALL_QUESTIONS:
        if q.id in sub_ids:
            continue
        assert q.display_id == q.id, f"{q.id} display_id 应为 {q.id}"
        assert q.sub_order == 1, f"{q.id} sub_order 应为 1"
        # display_order 应为题号数字
        num = int(q.id[1:])
        assert q.display_order == num, f"{q.id} display_order 应为 {num}"


def test_questions_sorted_by_display_order_then_sub_order():
    sorted_qs = sorted(ALL_QUESTIONS, key=lambda q: (q.display_order, q.sub_order))
    actual_order = [q.id for q in ALL_QUESTIONS]
    expected_order = [q.id for q in sorted_qs]
    assert actual_order == expected_order, (
        f"题目顺序应与 (display_order, sub_order) 一致\n"
        f"期望: {expected_order}\n实际: {actual_order}"
    )

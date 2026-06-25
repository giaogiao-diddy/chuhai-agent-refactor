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


def test_conflict_notes_include_missing_inexperienced_branch():
    assert Q5.conflict_note is not None
    assert Q8.conflict_note is not None
    assert Q27.conflict_note is not None
    assert Q26.conflict_note is not None

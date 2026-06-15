"""测评主链路集成测试

测试目标：测评创建 → 逐题提交 → 完成 → 报告生成的完整流程
"""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _seed_questions():
    """向数据库种子 15 道题"""
    from app.core.database import SessionLocal
    from app.models.question import Question, QuestionOption

    db = SessionLocal()
    path = FIXTURES_DIR / "sample_questions.json"
    with open(path, encoding="utf-8") as f:
        fixture = json.load(f)
    for q_data in fixture["questions"]:
        q = Question(
            id=q_data["id"], title=q_data["title"],
            description=q_data.get("description", ""),
            dimension=q_data["dimension"], sort_order=q_data["sort_order"],
            is_active=True,
        )
        db.add(q)
        for opt in q_data["options"]:
            db.add(QuestionOption(
                id=opt["id"], question_id=q.id, option_text=opt["text"],
                score=opt["score"], sort_order=opt["sort_order"],
            ))
    db.commit()
    db.close()


class TestAssessmentFlow:
    """测评主链路测试"""

    def test_create_assessment(self, client):
        """创建测评记录"""
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        resp = client.post("/api/assessments", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] > 0
        assert data["status"] == "in_progress"

    def test_submit_single_answer(self, client):
        """提交单题答案"""
        _seed_questions()
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        create_resp = client.post("/api/assessments", headers=headers)
        assessment_id = create_resp.json()["id"]

        resp = client.post(
            f"/api/assessments/{assessment_id}/answers",
            json={"question_id": 1, "option_id": 2},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["question_id"] == 1
        assert data["option_id"] == 2
        assert data["score"] > 0

    def test_submit_all_15_answers(self, client, sample_answers):
        """提交全部 15 题答案"""
        assert len(sample_answers) == 15
        _seed_questions()
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        create_resp = client.post("/api/assessments", headers=headers)
        assessment_id = create_resp.json()["id"]

        for ans in sample_answers:
            resp = client.post(
                f"/api/assessments/{assessment_id}/answers",
                json={"question_id": ans["question_id"], "option_id": ans["option_id"]},
                headers=headers,
            )
            assert resp.status_code == 200

    def test_complete_assessment_returns_score_and_tag(self, client, sample_answers):
        """完成测评后返回分数和标签"""
        _seed_questions()
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        create_resp = client.post("/api/assessments", headers=headers)
        assessment_id = create_resp.json()["id"]

        for ans in sample_answers:
            client.post(
                f"/api/assessments/{assessment_id}/answers",
                json={"question_id": ans["question_id"], "option_id": ans["option_id"]},
                headers=headers,
            )

        complete_resp = client.post(f"/api/assessments/{assessment_id}/complete", headers=headers)
        assert complete_resp.status_code == 200
        data = complete_resp.json()
        assert data["total_score"] > 0
        assert len(data["tag"]) > 0
        assert data["status"] == "generating"

    def test_complete_assessment_with_missing_answers_fails(self, client):
        """完成测评时答案不足 15 题应返回错误"""
        _seed_questions()
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        create_resp = client.post("/api/assessments", headers=headers)
        assessment_id = create_resp.json()["id"]

        # 只提交 3 题
        for qid in [1, 2, 3]:
            client.post(
                f"/api/assessments/{assessment_id}/answers",
                json={"question_id": qid, "option_id": qid},
                headers=headers,
            )

        complete_resp = client.post(f"/api/assessments/{assessment_id}/complete", headers=headers)
        assert complete_resp.status_code == 400

    def test_report_generation_success(self, client, sample_answers):
        """完成测评后报告生成状态为 success（模板兜底路径，无 AI Key）"""
        _seed_questions()
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        create_resp = client.post("/api/assessments", headers=headers)
        assessment_id = create_resp.json()["id"]

        for ans in sample_answers:
            client.post(
                f"/api/assessments/{assessment_id}/answers",
                json={"question_id": ans["question_id"], "option_id": ans["option_id"]},
                headers=headers,
            )

        client.post(f"/api/assessments/{assessment_id}/complete", headers=headers)

        # 后台任务同步等待（BackgroundTasks 在 TestClient 中是同步的）
        import time
        timeout = 5
        for _ in range(timeout * 2):
            status_resp = client.get(f"/api/assessments/{assessment_id}/report-status")
            status_data = status_resp.json()
            if status_data["status"] == "success":
                break
            time.sleep(0.5)

        assert status_data["status"] == "success"
        assert status_data["has_summary"] is True

    def test_report_generation_fallback_to_template(self, client, sample_answers):
        """AI 失败/未配置时自动切模板，前端无感知"""
        _seed_questions()
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        create_resp = client.post("/api/assessments", headers=headers)
        assessment_id = create_resp.json()["id"]

        for ans in sample_answers:
            client.post(
                f"/api/assessments/{assessment_id}/answers",
                json={"question_id": ans["question_id"], "option_id": ans["option_id"]},
                headers=headers,
            )

        client.post(f"/api/assessments/{assessment_id}/complete", headers=headers)

        import time
        for _ in range(10):
            status_resp = client.get(f"/api/assessments/{assessment_id}/report-status")
            status_data = status_resp.json()
            if status_data["status"] == "success":
                break
            time.sleep(0.5)

        assert status_data["status"] == "success"

        # 验证 summary 报告可访问
        summary_resp = client.get(f"/api/reports/{assessment_id}/summary")
        assert summary_resp.status_code == 200
        summary = summary_resp.json()
        assert "total_score" in summary
        assert "tag" in summary

    def test_report_status_polling_success(self, client, sample_answers):
        """轮询报告状态最终返回 success"""
        _seed_questions()
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        create_resp = client.post("/api/assessments", headers=headers)
        assessment_id = create_resp.json()["id"]

        for ans in sample_answers:
            client.post(
                f"/api/assessments/{assessment_id}/answers",
                json={"question_id": ans["question_id"], "option_id": ans["option_id"]},
                headers=headers,
            )

        # 完成前轮询 → pending
        status_resp = client.get(f"/api/assessments/{assessment_id}/report-status")
        assert status_resp.status_code == 200

        client.post(f"/api/assessments/{assessment_id}/complete", headers=headers)

        import time
        for _ in range(10):
            status_resp = client.get(f"/api/assessments/{assessment_id}/report-status")
            status_data = status_resp.json()
            if status_data["status"] == "success":
                break
            time.sleep(0.5)

        assert status_data["status"] == "success"

    def test_lead_creation_unlocks_full_report(self, client, sample_answers):
        """留资成功后完整报告可访问"""
        _seed_questions()
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        create_resp = client.post("/api/assessments", headers=headers)
        assessment_id = create_resp.json()["id"]

        for ans in sample_answers:
            client.post(
                f"/api/assessments/{assessment_id}/answers",
                json={"question_id": ans["question_id"], "option_id": ans["option_id"]},
                headers=headers,
            )

        client.post(f"/api/assessments/{assessment_id}/complete", headers=headers)

        import time
        for _ in range(10):
            status_resp = client.get(f"/api/assessments/{assessment_id}/report-status")
            if status_resp.json()["status"] == "success":
                break
            time.sleep(0.5)

        # 留资前 full 应 403
        full_resp_before = client.get(f"/api/reports/{assessment_id}/full", headers=headers)
        assert full_resp_before.status_code == 403

        # 留资
        client.post(
            "/api/leads",
            json={"name": "张三", "contact": "13800138000", "company": "某公司", "role": "创始人"},
            headers=headers,
        )

        # 留资后 full 应 200
        full_resp_after = client.get(f"/api/reports/{assessment_id}/full", headers=headers)
        assert full_resp_after.status_code == 200
        full = full_resp_after.json()
        assert "summary_conclusion" in full


class TestAssessmentEdgeCases:
    """测评边界场景测试"""

    def test_submit_duplicate_answer_updates(self, client):
        """重复提交同一题答案应覆盖而不是报错"""
        _seed_questions()
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        create_resp = client.post("/api/assessments", headers=headers)
        assessment_id = create_resp.json()["id"]

        # 第一次提交
        r1 = client.post(
            f"/api/assessments/{assessment_id}/answers",
            json={"question_id": 1, "option_id": 1},
            headers=headers,
        )
        assert r1.status_code == 200

        # 重复提交 — 应覆盖
        r2 = client.post(
            f"/api/assessments/{assessment_id}/answers",
            json={"question_id": 1, "option_id": 4},
            headers=headers,
        )
        assert r2.status_code == 200
        assert r2.json()["option_id"] == 4

    def test_submit_answer_after_complete_fails(self, client, sample_answers):
        """已完成测评后不能再提交答案"""
        _seed_questions()
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        create_resp = client.post("/api/assessments", headers=headers)
        assessment_id = create_resp.json()["id"]

        for ans in sample_answers:
            client.post(
                f"/api/assessments/{assessment_id}/answers",
                json={"question_id": ans["question_id"], "option_id": ans["option_id"]},
                headers=headers,
            )

        client.post(f"/api/assessments/{assessment_id}/complete", headers=headers)

        # 完成后提交 → 400
        resp = client.post(
            f"/api/assessments/{assessment_id}/answers",
            json={"question_id": 1, "option_id": 1},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_concurrent_assessments(self, client):
        """同一用户可以同时进行多个测评"""
        _seed_questions()
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        r1 = client.post("/api/assessments", headers=headers)
        r2 = client.post("/api/assessments", headers=headers)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["id"] != r2.json()["id"]

    def test_user_can_return_to_previous_question(self, client):
        """返回上一题修改答案"""
        _seed_questions()
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        create_resp = client.post("/api/assessments", headers=headers)
        assessment_id = create_resp.json()["id"]

        # 提交第 1 题
        client.post(
            f"/api/assessments/{assessment_id}/answers",
            json={"question_id": 1, "option_id": 1},
            headers=headers,
        )
        # 提交第 2 题
        client.post(
            f"/api/assessments/{assessment_id}/answers",
            json={"question_id": 2, "option_id": 5},
            headers=headers,
        )
        # 返回修改第 1 题
        r3 = client.post(
            f"/api/assessments/{assessment_id}/answers",
            json={"question_id": 1, "option_id": 3},
            headers=headers,
        )
        assert r3.status_code == 200
        assert r3.json()["option_id"] == 3
        assert r3.json()["question_id"] == 1

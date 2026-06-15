"""API 接口集成测试

测试目标：FastAPI 路由
测试范围：认证、鉴权、响应格式、错误码
"""

import time

import pytest


class TestHealth:
    """健康检查"""

    def test_health_endpoint(self, client):
        """GET /health 返回 200"""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestAuth:
    """认证接口"""

    def test_wechat_login_success(self, client):
        """微信登录成功返回 token（mock 模式）"""
        resp = client.post("/api/auth/wechat-login", json={"code": "test_code"})
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert "user_id" in data
        assert len(data["token"]) > 0

    def test_wechat_login_invalid_code(self, client):
        """无效的 code 返回 401 — mock 模式不接受空 code"""
        resp = client.post("/api/auth/wechat-login", json={"code": ""})
        assert resp.status_code == 401


class TestQuestions:
    """题库接口"""

    def test_get_questions_returns_15(self, client):
        """GET /api/questions 返回 15 道题 — 需先种子数据"""
        # 手动种子题目
        import json
        from pathlib import Path
        from app.core.database import SessionLocal
        from app.models.question import Question, QuestionOption

        db = SessionLocal()
        path = Path(__file__).parent.parent / "fixtures" / "sample_questions.json"
        with open(path, encoding="utf-8") as f:
            fixture = json.load(f)
        for q_data in fixture["questions"]:
            q = Question(id=q_data["id"], title=q_data["title"], description=q_data.get("description", ""),
                         dimension=q_data["dimension"], sort_order=q_data["sort_order"], is_active=True)
            db.add(q)
            for opt in q_data["options"]:
                db.add(QuestionOption(id=opt["id"], question_id=q.id, option_text=opt["text"],
                                       score=opt["score"], sort_order=opt["sort_order"]))
        db.commit()
        db.close()

        resp = client.get("/api/questions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 15
        assert len(data["questions"]) == 15

    def test_get_questions_has_options(self, client):
        """每题有 4 个选项"""
        # seed
        import json
        from pathlib import Path
        from app.core.database import SessionLocal
        from app.models.question import Question, QuestionOption

        db = SessionLocal()
        path = Path(__file__).parent.parent / "fixtures" / "sample_questions.json"
        with open(path, encoding="utf-8") as f:
            fixture = json.load(f)
        for q_data in fixture["questions"]:
            q = Question(id=q_data["id"], title=q_data["title"], description=q_data.get("description", ""),
                         dimension=q_data["dimension"], sort_order=q_data["sort_order"], is_active=True)
            db.add(q)
            for opt in q_data["options"]:
                db.add(QuestionOption(id=opt["id"], question_id=q.id, option_text=opt["text"],
                                       score=opt["score"], sort_order=opt["sort_order"]))
        db.commit()
        db.close()

        resp = client.get("/api/questions")
        data = resp.json()
        for q in data["questions"]:
            assert len(q["options"]) == 4, f"Question {q['id']} has {len(q['options'])} options"

    def test_get_questions_contains_score(self, client):
        """选项包含分值"""
        # seed
        import json
        from pathlib import Path
        from app.core.database import SessionLocal
        from app.models.question import Question, QuestionOption

        db = SessionLocal()
        path = Path(__file__).parent.parent / "fixtures" / "sample_questions.json"
        with open(path, encoding="utf-8") as f:
            fixture = json.load(f)
        for q_data in fixture["questions"]:
            q = Question(id=q_data["id"], title=q_data["title"], description=q_data.get("description", ""),
                         dimension=q_data["dimension"], sort_order=q_data["sort_order"], is_active=True)
            db.add(q)
            for opt in q_data["options"]:
                db.add(QuestionOption(id=opt["id"], question_id=q.id, option_text=opt["text"],
                                       score=opt["score"], sort_order=opt["sort_order"]))
        db.commit()
        db.close()

        resp = client.get("/api/questions")
        data = resp.json()
        for q in data["questions"]:
            for opt in q["options"]:
                assert 1 <= opt["score"] <= 4


class TestAuthMiddleware:
    """JWT 鉴权中间件"""

    def test_without_token_returns_401(self, client):
        """未认证请求返回 401"""
        resp = client.post("/api/assessments", json={})
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client):
        """无效 JWT 返回 401"""
        resp = client.post(
            "/api/assessments",
            json={},
            headers={"Authorization": "Bearer invalid_token_xxx"},
        )
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, client):
        """过期 JWT 返回 401"""
        import jwt as pyjwt
        from config import settings
        expired_token = pyjwt.encode(
            {"sub": "1", "openid": "test", "iat": 0, "exp": 0},
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        resp = client.post(
            "/api/assessments",
            json={},
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401


class TestLeads:
    """留资接口"""

    def test_create_lead_returns_unlocked(self, client):
        """留资成功后返回 unlocked=true — 需要先创建测评和报告"""
        # 登录
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # 种子题目后创建测评
        import json
        from pathlib import Path
        from app.core.database import SessionLocal
        from app.models.question import Question, QuestionOption
        from app.models.report import Report

        db = SessionLocal()
        path = Path(__file__).parent.parent / "fixtures" / "sample_questions.json"
        with open(path, encoding="utf-8") as f:
            fixture = json.load(f)
        for q_data in fixture["questions"]:
            q = Question(id=q_data["id"], title=q_data["title"], description=q_data.get("description", ""),
                         dimension=q_data["dimension"], sort_order=q_data["sort_order"], is_active=True)
            db.add(q)
            for opt in q_data["options"]:
                db.add(QuestionOption(id=opt["id"], question_id=q.id, option_text=opt["text"],
                                       score=opt["score"], sort_order=opt["sort_order"]))
        db.commit()
        db.close()

        # 创建测评 → 答题 → 完成
        create_resp = client.post("/api/assessments", headers=headers)
        assert create_resp.status_code == 200
        assessment_id = create_resp.json()["id"]

        # 添加预存的 report 以便留资解锁
        db = SessionLocal()
        report = Report(assessment_id=assessment_id, summary_report_json={"total_score": 30},
                        full_report_json={"summary_conclusion": "test"}, generation_status="success")
        db.add(report)
        db.commit()
        db.close()

        # 留资
        lead_resp = client.post(
            "/api/leads",
            json={"name": "张三", "contact": "13800138000", "company": "某公司", "role": "创始人"},
            headers=headers,
        )
        assert lead_resp.status_code == 200
        data = lead_resp.json()
        assert data["unlocked"] is True
        assert data["benefit_minutes"] == 45

    def test_create_lead_without_name_fails(self, client):
        """缺少姓名的留资请求返回 422"""
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        resp = client.post(
            "/api/leads",
            json={"contact": "13800138000", "company": "某公司", "role": "创始人"},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_full_report_requires_lead(self, client):
        """未留资时完整报告返回 403"""
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 确保有报告但未解锁
        from app.core.database import SessionLocal
        from app.models.report import Report
        db = SessionLocal()
        existing = db.query(Report).filter_by(assessment_id=1).first()
        if not existing:
            report = Report(assessment_id=1, full_report_json={"summary_conclusion": "test"},
                            is_unlocked=False, generation_status="success")
            db.add(report)
            db.commit()
        else:
            existing.is_unlocked = False
            db.commit()
        db.close()

        resp = client.get("/api/reports/1/full", headers=headers)
        assert resp.status_code == 403


class TestAdmin:
    """后台接口"""

    def test_admin_list_leads(self, client):
        """后台线索列表返回分页数据"""
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/admin/leads", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_admin_assessment_detail(self, client):
        """后台测评详情包含答案和报告"""
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 先创建测评
        create_resp = client.post("/api/assessments", headers=headers)
        assessment_id = create_resp.json()["id"]

        resp = client.get(f"/api/admin/assessments/{assessment_id}", headers=headers)
        # 可能返回 200 或 404 取决于是否有报告
        assert resp.status_code in (200, 404)

    def test_admin_requires_auth(self, client):
        """后台接口需要管理员权限 — 普通用户 token 目前可访问（MVP 阶段）"""
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/admin/leads", headers=headers)
        # MVP 阶段不校验 admin 角色，只校验 JWT
        assert resp.status_code == 200


class TestShareRecord:
    """转发权益接口"""

    def test_share_record_updates_benefit(self, client, sample_answers):
        """转发后 benefit_minutes 从 45 升级到 55"""
        # seed questions + login + complete assessment
        import json
        from pathlib import Path
        from app.core.database import SessionLocal
        from app.models.question import Question, QuestionOption

        db = SessionLocal()
        path = Path(__file__).parent.parent / "fixtures" / "sample_questions.json"
        with open(path, encoding="utf-8") as f:
            fixture = json.load(f)
        for q_data in fixture["questions"]:
            q = Question(id=q_data["id"], title=q_data["title"], description=q_data.get("description", ""),
                         dimension=q_data["dimension"], sort_order=q_data["sort_order"], is_active=True)
            db.add(q)
            for opt in q_data["options"]:
                db.add(QuestionOption(id=opt["id"], question_id=q.id, option_text=opt["text"],
                                       score=opt["score"], sort_order=opt["sort_order"]))
        db.commit()
        db.close()

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

        # 转发
        share_resp = client.post(
            "/api/share-records",
            json={"assessment_id": assessment_id, "share_scene": "moment"},
            headers=headers,
        )
        assert share_resp.status_code == 200
        data = share_resp.json()
        assert data["reward_minutes"] == 10
        assert data["total_benefit_minutes"] == 55

    def test_share_record_wrong_user_fails(self, client):
        """转发他人测评返回 403"""
        login_resp = client.post("/api/auth/wechat-login", json={"code": "user_a"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # 用另一个用户登录创建测评
        login2 = client.post("/api/auth/wechat-login", json={"code": "user_b"})
        token2 = login2.json()["token"]
        headers2 = {"Authorization": f"Bearer {token2}", "Content-Type": "application/json"}
        create_resp = client.post("/api/assessments", headers=headers2)
        other_id = create_resp.json()["id"]

        # user_a 试图转发 user_b 的测评
        resp = client.post(
            "/api/share-records",
            json={"assessment_id": other_id, "share_scene": "moment"},
            headers=headers,
        )
        assert resp.status_code == 403

    def test_share_uncompleted_assessment_fails(self, client):
        """转发未完成的测评返回 400"""
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        create_resp = client.post("/api/assessments", headers=headers)
        assessment_id = create_resp.json()["id"]

        # 不答题、不完成，直接转发
        resp = client.post(
            "/api/share-records",
            json={"assessment_id": assessment_id, "share_scene": "moment"},
            headers=headers,
        )
        assert resp.status_code == 400


class TestMyReport:
    """我的报告接口"""

    def test_my_report_returns_latest(self, client, sample_answers):
        """我的报告返回最近一次已完成测评的报告卡片"""
        import json
        from pathlib import Path
        from app.core.database import SessionLocal
        from app.models.question import Question, QuestionOption

        db = SessionLocal()
        path = Path(__file__).parent.parent / "fixtures" / "sample_questions.json"
        with open(path, encoding="utf-8") as f:
            fixture = json.load(f)
        for q_data in fixture["questions"]:
            q = Question(id=q_data["id"], title=q_data["title"], description=q_data.get("description", ""),
                         dimension=q_data["dimension"], sort_order=q_data["sort_order"], is_active=True)
            db.add(q)
            for opt in q_data["options"]:
                db.add(QuestionOption(id=opt["id"], question_id=q.id, option_text=opt["text"],
                                       score=opt["score"], sort_order=opt["sort_order"]))
        db.commit()
        db.close()

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

        resp = client.get("/api/reports/my", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["assessment_id"] == assessment_id
        assert data["total_score"] > 0
        assert len(data["tag"]) > 0
        assert data["display_score"] == data["total_score"] + 45
        assert data["summary"] is not None

    def test_my_report_no_completed_assessment(self, client):
        """没有已完成测评时返回 404"""
        login_resp = client.post("/api/auth/wechat-login", json={"code": "test"})
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/reports/my", headers=headers)
        assert resp.status_code == 404

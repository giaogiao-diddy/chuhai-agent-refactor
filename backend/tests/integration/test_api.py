"""API 接口集成测试

测试目标：FastAPI 路由
测试范围：认证、鉴权、响应格式、错误码
"""

import pytest


class TestHealth:
    """健康检查"""

    def test_health_endpoint(self):
        """GET /api/health 返回 200"""
        pytest.skip("需要先实现 main.py 和路由")


class TestAuth:
    """认证接口"""

    def test_wechat_login_success(self):
        """微信登录成功返回 token"""
        pytest.skip("需要先实现 auth 路由")

    def test_wechat_login_invalid_code(self):
        """无效的 code 返回 401"""
        pytest.skip("需要先实现 auth 路由")


class TestQuestions:
    """题库接口"""

    def test_get_questions_returns_15(self):
        """GET /api/questions 返回 15 道题"""
        pytest.skip("需要先实现 questions 路由")

    def test_get_questions_has_options(self):
        """每题有 4 个选项"""
        pytest.skip("需要先实现 questions 路由")

    def test_get_questions_contains_score(self):
        """选项包含分值"""
        pytest.skip("需要先实现 questions 路由")


class TestAuthMiddleware:
    """JWT 鉴权中间件"""

    def test_without_token_returns_401(self):
        """未认证请求返回 401"""
        pytest.skip("需要先实现 JWT 中间件")

    def test_invalid_token_returns_401(self):
        """无效 JWT 返回 401"""
        pytest.skip("需要先实现 JWT 校验")

    def test_expired_token_returns_401(self):
        """过期 JWT 返回 401"""
        pytest.skip("需要先实现 JWT 校验")


class TestLeads:
    """留资接口"""

    def test_create_lead_returns_unlocked(self, sample_assessment):
        """留资成功后返回 unlocked=true"""
        pytest.skip("需要先实现 lead 路由")

    def test_create_lead_without_name_fails(self):
        """缺少姓名的留资请求返回 422"""
        pytest.skip("需要先实现 Pydantic 校验")

    def test_full_report_requires_lead(self):
        """未留资时完整报告返回 403"""
        pytest.skip("需要先实现后端解锁校验")


class TestAdmin:
    """后台接口"""

    def test_admin_list_leads(self):
        """后台线索列表返回分页数据"""
        pytest.skip("需要先实现 admin 路由")

    def test_admin_assessment_detail(self):
        """后台测评详情包含答案和报告"""
        pytest.skip("需要先实现 admin 路由")

    def test_admin_requires_auth(self):
        """后台接口需要管理员权限"""
        pytest.skip("需要先实现 admin 路由")

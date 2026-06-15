"""测试公共 Fixture"""

import json
import os
from pathlib import Path

# ── 必须在 import app 模块之前设置 ──
TEST_DATABASE_URL = "sqlite:///./test.db"
os.environ["LB_DATABASE_URL"] = TEST_DATABASE_URL

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from config import settings

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="function")
def db():
    """每个测试独立 SQLite — 自动建表，结束后拆表"""
    test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db):
    """FastAPI TestClient — 依赖注入重定向到测试 SQLite"""
    from main import app

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    """通过微信登录获取 JWT Header"""
    resp = client.post("/api/auth/wechat-login", json={"code": "test_code"})
    data = resp.json()
    token = data.get("token", "")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ── 原单元测试 fixtures ──────────────────────────────────────────

@pytest.fixture
def sample_questions() -> list[dict]:
    """加载模拟题库"""
    path = FIXTURES_DIR / "sample_questions.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["questions"]


@pytest.fixture
def sample_tags() -> list[dict]:
    """加载标签配置"""
    path = FIXTURES_DIR / "sample_questions.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["tags"]


@pytest.fixture
def sample_answers() -> list[dict]:
    """15 题每题 2 分，total=30 → 轻量试探型 (26-35)"""
    return [
        {"question_id": i, "option_id": (i - 1) * 4 + 2, "score": 2}
        for i in range(1, 16)
    ]


@pytest.fixture
def answers_all_min() -> list[dict]:
    """15 题每题 1 分，total=15 → 观察准备型 (15-25)"""
    return [
        {"question_id": i, "option_id": (i - 1) * 4 + 1, "score": 1}
        for i in range(1, 16)
    ]


@pytest.fixture
def answers_all_max() -> list[dict]:
    """15 题每题 4 分，total=60 → 优先布局型 (46-60)"""
    return [
        {"question_id": i, "option_id": i * 4, "score": 4}
        for i in range(1, 16)
    ]


@pytest.fixture
def sample_assessment() -> dict:
    """加载模拟测评结果（含报告）"""
    path = FIXTURES_DIR / "sample_assessment.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_ai_response() -> dict:
    """模拟 DeepSeek 成功返回的 JSON"""
    return {
        "summary_report": {
            "preliminary_judgment": "您的企业具备基本出海条件，建议从轻量测试开始。",
            "strengths": ["产品标准化程度较高", "对目标市场有初步了解"],
            "risks": ["团队配置需要加强", "供应链稳定性有待验证"],
            "tag_explanation": "已具备部分条件，但关键能力尚未完整，适合小预算、轻渠道测试。",
        },
        "full_report": {
            "summary_conclusion": "综合来看，您的企业具备出海基本条件。",
            "dimension_scores": {"公司实力": 22, "业务准备": 18, "市场认知": 20, "执行能力": 18},
            "recommended_path": "建议优先选择东南亚市场进行小规模测试。",
            "risk_reminder": "需注意供应链交付稳定性和品牌本地化准备。",
            "action_plan_30days": ["完成产品出海版本准备", "注册目标国家商标", "选择轻量渠道测试"],
            "consultant_guide": "请联系企业微信顾问获得1对1解读。",
        },
    }


@pytest.fixture
def mock_ai_response_missing_fields() -> dict:
    """模拟 AI 返回缺少必填字段的 JSON"""
    return {
        "summary_report": {
            "preliminary_judgment": "测试判断",
        },
        "full_report": {
            "summary_conclusion": "测试结论",
        },
    }


@pytest.fixture
def mock_ai_response_invalid_json() -> str:
    """模拟 AI 返回非法 JSON 字符串"""
    return "这不是 JSON 格式的响应"

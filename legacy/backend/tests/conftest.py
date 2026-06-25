"""测试公共 Fixture"""

import json
import os
from pathlib import Path

# ── 必须在 import app 模块之前设置 ──
TEST_DATABASE_URL = "sqlite:///./test.db"
os.environ["LB_DATABASE_URL"] = TEST_DATABASE_URL
os.environ["LB_AI_REPORT_ENABLED"] = "false"
os.environ["LB_LLM_API_KEY"] = ""

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
    """17 计分题每题 2 分，total=34 → 轻量试探型 (31-43)"""
    return [
        {"question_id": question_id, "option_id": (question_id - 2) * 4 + 2, "score": 2}
        for question_id in range(2, 19)  # Q2-Q18 计分
    ]


@pytest.fixture
def answers_all_min() -> list[dict]:
    """17 计分题每题 1 分，total=17 → 观察准备型 (17-30)"""
    return [
        {"question_id": question_id, "option_id": (question_id - 2) * 4 + 1, "score": 1}
        for question_id in range(2, 19)
    ]


@pytest.fixture
def answers_all_max() -> list[dict]:
    """17 计分题每题 4 分，total=68 → 优先布局型 (57-68)"""
    return [
        {"question_id": question_id, "option_id": (question_id - 2) * 4 + 4, "score": 4}
        for question_id in range(2, 19)
    ]


@pytest.fixture
def sample_assessment() -> dict:
    """加载模拟测评结果（含报告）"""
    path = FIXTURES_DIR / "sample_assessment.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_ai_response() -> dict:
    """模拟 DeepSeek 成功返回的 V2 报告 JSON"""
    return {
        "summary_report": {
            "hero": {
                "score": 77,
                "tag": "轻量试探型",
                "one_sentence_judgment": "您的企业具备基本出海条件，建议从轻量内容验证开始。",
                "core_contradiction": "当前最大的成交阻力可能来自内容信任资产不足。",
            },
            "key_findings": [
                {"title": "最大优势", "content": "产品标准化程度较高"},
                {"title": "最大短板", "content": "内容资产不足"},
            ],
            "total_score": 34,
            "display_score": 77,
            "tag": "轻量试探型",
            "tag_explanation": "已具备部分条件，可启动强成交人设内容矩阵进行低成本验证。",
            "preliminary_judgment": "您的企业具备基本出海条件，建议从轻量内容验证开始。",
            "positioning_assessment": "定位基础初步具备，但目标用户和市场切口仍需聚焦。",
            "content_assessment": "内容资产不足，需要围绕产品信任建立表达体系。",
            "conversion_assessment": "转化承接需要补齐报价、样品和跟进 SOP。",
            "strengths": ["产品标准化程度较高", "对目标市场有初步了解"],
            "risks": ["团队配置需要加强", "供应链稳定性有待验证"],
            "unlock_hint": "提交信息后解锁完整报告，并领取 45 分钟 1 对 1 免费解读。",
        },
        "full_report": {
            "diagnosis_cards": [
                {"title": "定位", "content": "定位定生死：先明确目标客户、市场区域和信任切口。"},
                {"title": "内容", "content": "内容定江山：用流量内容、营销内容、故事内容建立海外信任。"},
                {"title": "转化", "content": "SOP 定天下：补齐线索筛选、QA、跟进和客户管理 SOP。"},
            ],
            "summary_conclusion": "综合来看，您的企业具备出海基本条件。",
            "positioning_assessment": "定位定生死：先明确目标客户、市场区域和信任切口。",
            "content_assessment": "内容定江山：用流量内容、营销内容、故事内容建立海外信任。",
            "conversion_assessment": "SOP 定天下：补齐线索筛选、QA、跟进和客户管理 SOP。",
            "dimension_scores": {
                "enterprise_capacity": {"title": "企业承载力", "score": 6, "max_score": 12, "diagnosis": "企业承载力处于初步可验证状态。", "weak_points": ["团队承接仍需确认"], "next_action": "确认测试预算和负责人。"},
                "overseas_foundation": {"title": "出海基础", "score": 8, "max_score": 20, "diagnosis": "海外基础需要继续积累。", "weak_points": ["目标市场仍需聚焦"], "next_action": "选择一个市场做内容测试。"},
                "product_trust_asset": {"title": "信任资产", "score": 8, "max_score": 12, "diagnosis": "产品具备内容化表达空间。", "weak_points": ["Catalog 仍需完善"], "next_action": "整理多语言目录。"},
                "content_acquisition": {"title": "内容获客", "score": 4, "max_score": 8, "diagnosis": "内容获客能力需要加强。", "weak_points": ["选题 SOP 不稳定"], "next_action": "建立三类内容选题库。"},
                "conversion_system": {"title": "转化交付系统", "score": 2, "max_score": 16, "diagnosis": "转化 SOP 仍需搭建。", "weak_points": ["跟进节奏不稳定"], "next_action": "搭建火眼金睛筛选表。"},
            },
            "strategy_path": {
                "positioning": "先明确卖给谁、去哪里、卖什么价值。",
                "content": "用信任三位一体建立海外客户理解。",
                "conversion": "用 SOP 承接询盘和交付。",
            },
            "recommended_path": "建议优先选择一个目标市场，用强成交人设内容矩阵做小规模验证。",
            "risk_cards": [
                {"title": "交付风险", "content": "供应链交付稳定性需要验证。"},
                {"title": "Catalog 风险", "content": "产品目录需要完善。"},
                {"title": "内容断档风险", "content": "内容生产节奏需要稳定。"},
                {"title": "合规准备风险", "content": "跨境资料需要补齐。"},
            ],
            "risk_reminder": "需注意供应链交付稳定性和品牌本地化准备。",
            "action_plan_30days": ["完成产品出海版本准备", "注册目标国家商标", "选择轻量渠道测试"],
            "consultant_guide": "请联系企业微信顾问获得1对1解读。",
        },
        "sales_followup": {
            "lead_temperature": "B",
            "followup_focus": ["目标市场", "内容素材", "转化 SOP"],
            "opening_script": "可以先从您当前海外客户来源聊起。",
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

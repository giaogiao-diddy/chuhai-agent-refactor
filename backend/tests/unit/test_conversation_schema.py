from app.schemas.agent_state import AgentState
from app.schemas.conversation import ConversationClientState
from app.schemas.slots import SlotValue


def test_slots_roundtrip():
    state = AgentState()
    state.slots.industry = SlotValue(value="健身器材", confidence=0.9)
    state.slots.main_product = SlotValue(value="力量训练设备", confidence=0.85)

    client = ConversationClientState.from_agent_state(state)
    assert client.slots.industry.value == "健身器材"
    assert client.slots.industry.confidence == 0.9
    assert client.slots.main_product.value == "力量训练设备"

    restored = client.to_agent_state()
    assert restored.slots.industry.value == "健身器材"
    assert restored.slots.industry.confidence == 0.9
    assert restored.slots.main_product.value == "力量训练设备"


def test_branch_type_is_literal():
    client = ConversationClientState(messages=[], branch="experienced")
    assert client.branch == "experienced"
    client_dict = client.model_dump()
    assert client_dict["branch"] == "experienced"


def test_slots_serialize_to_json():
    state = AgentState()
    state.slots.industry = SlotValue(value="健身器材", confidence=0.9)
    client = ConversationClientState.from_agent_state(state)
    d = client.model_dump()
    assert d["slots"]["industry"]["value"] == "健身器材"
    # roundtrip from dict
    restored = ConversationClientState(**d)
    assert restored.slots.industry.value == "健身器材"


def test_client_state_excludes_internal_errors():
    """scoring_error / report_error 不暴露给客户端"""
    fields = set(ConversationClientState.model_fields.keys())
    assert "scoring_error" not in fields
    assert "report_error" not in fields
    assert "lead_score" not in fields
    assert "lead_priority" not in fields
    assert "public_error" in fields


def test_public_error_sanitizes_report_error():
    state = AgentState(report_error="UserReport 包含禁止词: 销售话术 lead_score")
    client = ConversationClientState.from_agent_state(state)
    assert client.public_error == "报告生成过程已自动处理，请查看报告结果"
    text = client.model_dump_json()
    assert "销售话术" not in text
    assert "lead_score" not in text


def test_public_error_sanitizes_scoring_error():
    state = AgentState(scoring_error="内部 scoring error lead_priority")
    client = ConversationClientState.from_agent_state(state)
    assert client.public_error == "当前信息不足，系统已生成保守诊断"
    text = client.model_dump_json()
    assert "lead_priority" not in text


def test_invalid_branch_rejected():
    import pytest
    with pytest.raises(Exception):
        ConversationClientState(messages=[], branch="bad")


def test_client_state_sanitizes_validation_errors_without_echoing_raw_values():
    state = AgentState(validation_errors=[
        "未知题号: sales_followup",
        "无效选项: 顾问备注",
        "continue_stream: 模拟内部异常",
        "Traceback: database password 123456",
    ])
    client = ConversationClientState.from_agent_state(state)
    payload = client.model_dump_json()
    assert "存在未知题号，已忽略" in payload
    assert "存在无效选项，已忽略" in payload
    assert "部分内部验证信息已过滤" in payload
    assert "sales_followup" not in payload
    assert "顾问备注" not in payload
    assert "模拟内部异常" not in payload
    assert "Traceback" not in payload
    assert "123456" not in payload


def test_client_state_does_not_restore_validation_errors_to_agent_state():
    client = ConversationClientState(
        messages=[],
        validation_errors=["部分内部验证信息已过滤"],
    )
    restored = client.to_agent_state()
    assert restored.validation_errors == []


# ── anonymous_user_id 校验 ─────────────────────────────────────────

def test_anonymous_user_id_accepts_valid_ids():
    from app.schemas.anonymous import validate_anonymous_user_id
    assert validate_anonymous_user_id("abcDEF_123-xyz") == "abcDEF_123-xyz"
    assert validate_anonymous_user_id("12345678") == "12345678"
    assert validate_anonymous_user_id(None) is None


def test_anonymous_user_id_rejects_spaces():
    from app.schemas.anonymous import validate_anonymous_user_id
    import pytest
    with pytest.raises(ValueError):
        validate_anonymous_user_id("abc def 1234")


def test_anonymous_user_id_rejects_colons():
    from app.schemas.anonymous import validate_anonymous_user_id
    import pytest
    with pytest.raises(ValueError):
        validate_anonymous_user_id("bad:id:here")


def test_anonymous_user_id_rejects_chinese():
    from app.schemas.anonymous import validate_anonymous_user_id
    import pytest
    with pytest.raises(ValueError):
        validate_anonymous_user_id("中文测试1234")


def test_anonymous_user_id_rejects_too_short():
    from app.schemas.anonymous import validate_anonymous_user_id
    import pytest
    with pytest.raises(ValueError):
        validate_anonymous_user_id("short")


def test_anonymous_user_id_rejects_slashes():
    from app.schemas.anonymous import validate_anonymous_user_id
    import pytest
    with pytest.raises(ValueError):
        validate_anonymous_user_id("bad/slash")


def test_anonymous_user_id_conversation_finish_request_validates():
    from app.schemas.conversation import ConversationFinishRequest
    from app.schemas.agent_state import AgentState
    from app.schemas.conversation import ConversationClientState
    # 有效 ID 通过
    state = AgentState()
    client = ConversationClientState.from_agent_state(state)
    req = ConversationFinishRequest(state=client, anonymous_user_id="validID_123-test")
    assert req.anonymous_user_id == "validID_123-test"


def test_anonymous_user_id_conversation_finish_request_rejects_bad():
    from app.schemas.conversation import ConversationFinishRequest
    from app.schemas.agent_state import AgentState
    from app.schemas.conversation import ConversationClientState
    import pytest
    state = AgentState()
    client = ConversationClientState.from_agent_state(state)
    with pytest.raises(Exception):
        ConversationFinishRequest(state=client, anonymous_user_id="bad:id")

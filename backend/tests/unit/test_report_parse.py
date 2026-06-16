"""AI 输出 JSON 解析校验单元测试

测试目标：app.services.report_service 中的 JSON 解析函数
测试范围：完整 JSON 解析、缺失字段检测、非法 JSON 处理
"""

import json
import pytest
from app.services.prompts import SYSTEM_DIAGNOSE_SINGLE_QUESTION, SYSTEM_GENERATE_FULL_REPORT
from app.services.report_service import (
    _extract_user_industry,
    _render_prompt,
    _sanitize_diagnosis_tags,
    parse_ai_response,
    validate_report_fields,
)


class TestParseAIResponse:
    """AI 响应解析测试"""

    def test_parse_valid_json_dict(self, mock_ai_response):
        """有效的 JSON dict 能正确解析"""
        result = parse_ai_response(mock_ai_response)
        assert result is not None
        assert "summary_report" in result
        assert "full_report" in result

    def test_parse_valid_json_string(self, mock_ai_response):
        """有效的 JSON 字符串能正确解析"""
        json_str = json.dumps(mock_ai_response, ensure_ascii=False)
        result = parse_ai_response(json_str)
        assert result is not None
        assert "summary_report" in result

    def test_parse_invalid_json_string(self, mock_ai_response_invalid_json):
        """非法 JSON 字符串返回 None"""
        result = parse_ai_response(mock_ai_response_invalid_json)
        assert result is None

    def test_parse_empty_string(self):
        """空字符串返回 None"""
        result = parse_ai_response("")
        assert result is None

    def test_parse_none(self):
        """None 返回 None"""
        result = parse_ai_response(None)
        assert result is None

    def test_parse_empty_dict(self):
        """空 dict 返回空 dict"""
        result = parse_ai_response({})
        assert result == {}

    def test_parse_missing_report_keys(self, mock_ai_response_missing_fields):
        """缺少 report 层的 key 仍能解析但校验会失败"""
        result = parse_ai_response(mock_ai_response_missing_fields)
        assert result is not None
        assert "summary_report" in result


class TestValidateReportFields:
    """报告字段校验测试"""

    def test_valid_full_report_passes(self, mock_ai_response):
        """完整的报告结构通过校验"""
        data = mock_ai_response
        assert validate_report_fields(data) is True

    def test_missing_full_report_key(self, mock_ai_response):
        """缺少 full_report 键"""
        data = {"summary_report": mock_ai_response["summary_report"]}
        assert validate_report_fields(data) is False

    def test_missing_summary_report_key(self, mock_ai_response):
        """缺少 summary_report 键"""
        data = {"full_report": mock_ai_response["full_report"]}
        assert validate_report_fields(data) is False

    def test_empty_data_fails(self):
        """空数据校验失败"""
        assert validate_report_fields({}) is False

    def test_summary_missing_fields(self, mock_ai_response_missing_fields):
        """部分报告缺少必填字段"""
        assert validate_report_fields(mock_ai_response_missing_fields) is False

    def test_summary_strengths_not_list(self, mock_ai_response):
        """strengths 不是列表"""
        data = mock_ai_response.copy()
        data["summary_report"]["strengths"] = "字符串而不是列表"
        assert validate_report_fields(data) is False

    def test_full_dimension_scores_not_dict(self, mock_ai_response):
        """dimension_scores 不是字典"""
        data = json.loads(json.dumps(mock_ai_response, ensure_ascii=False))
        data["full_report"]["dimension_scores"] = [1, 2, 3]
        assert validate_report_fields(data) is False

    def test_full_action_plan_not_list(self, mock_ai_response):
        """action_plan_30days 不是列表"""
        data = json.loads(json.dumps(mock_ai_response, ensure_ascii=False))
        data["full_report"]["action_plan_30days"] = "字符串"
        assert validate_report_fields(data) is False

    def test_null_fields_fails(self, mock_ai_response):
        """包含 None 值的字段"""
        data = json.loads(json.dumps(mock_ai_response, ensure_ascii=False))
        data["full_report"]["summary_conclusion"] = None
        assert validate_report_fields(data) is False

    def test_summary_report_field_types(self, mock_ai_response):
        """部分报告各字段类型正确"""
        result = parse_ai_response(mock_ai_response)
        assert result is not None
        summary = result["summary_report"]
        assert isinstance(summary["preliminary_judgment"], str)
        assert isinstance(summary["positioning_assessment"], str)
        assert isinstance(summary["content_assessment"], str)
        assert isinstance(summary["conversion_assessment"], str)
        assert isinstance(summary["strengths"], list)
        assert isinstance(summary["risks"], list)

    def test_full_report_field_types(self, mock_ai_response):
        """完整报告各字段类型正确"""
        result = parse_ai_response(mock_ai_response)
        assert result is not None
        full = result["full_report"]
        assert isinstance(full["summary_conclusion"], str)
        assert isinstance(full["positioning_assessment"], str)
        assert isinstance(full["content_assessment"], str)
        assert isinstance(full["conversion_assessment"], str)
        assert isinstance(full["dimension_scores"], dict)
        assert isinstance(full["action_plan_30days"], list)


class TestPromptContextHelpers:
    """Prompt 上下文辅助函数测试"""

    def test_extract_user_industry_from_q1_answer(self):
        """从 Q1 文本答案中提取用户行业"""
        answer_summary = [
            {"question_id": 1, "answer_text": "五金配件"},
            {"question_id": 2, "answer_text": "20人及以下"},
        ]

        assert _extract_user_industry(answer_summary) == "五金配件"

    def test_extract_user_industry_falls_back_when_missing(self):
        """Q1 缺失时使用兜底行业描述"""
        assert _extract_user_industry([]) == "未填写行业"

    def test_sanitize_diagnosis_tags_keeps_only_standard_tags(self):
        """逐题诊断标签只能保留标准标签库中的标签，且最多 2 个"""
        tags = ["画像模糊", "AI自创标签", "合规防线薄弱", "无铂金跟进"]

        assert _sanitize_diagnosis_tags(tags) == ["画像模糊", "合规防线薄弱"]

    def test_prompt_render_replaces_user_industry(self):
        """两套 Prompt 渲染后不应残留 user_industry 占位符"""
        diagnose_prompt = _render_prompt(SYSTEM_DIAGNOSE_SINGLE_QUESTION, {
            "user_industry": "五金配件",
            "question_text": "是否具备外语产品目录？",
            "question_dimension": "product_trust_asset",
            "answer_text": "暂时没有",
            "score": 1,
            "previous_answer_summary": "[]",
        })
        full_prompt = _render_prompt(SYSTEM_GENERATE_FULL_REPORT, {
            "user_industry": "五金配件",
            "total_score": 34,
            "display_score": 77,
            "tag": "轻量试探型",
            "answers_json": "[]",
            "dimension_summary": "{}",
            "report_memories": "[]",
        })

        assert "{user_industry}" not in diagnose_prompt
        assert "{user_industry}" not in full_prompt
        assert "五金配件" in diagnose_prompt
        assert "五金配件" in full_prompt

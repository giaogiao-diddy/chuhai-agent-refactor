"""AI 输出 JSON 解析校验单元测试

测试目标：app.services.report_service 中的 JSON 解析函数
测试范围：完整 JSON 解析、缺失字段检测、非法 JSON 处理
"""

import json
import pytest
from app.services.report_service import parse_ai_response, validate_report_fields


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

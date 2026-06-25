"""输入校验单元测试

测试目标：app.api 路由中的输入校验逻辑
测试范围：留资表单校验、答案提交校验、测评完成校验
"""

import pytest
from pydantic import ValidationError
from app.schemas.lead import LeadCreate
from app.schemas.assessment import AnswerSubmit


class TestLeadValidation:
    """留资表单校验测试"""

    def test_valid_lead_passes(self):
        """有效留资通过校验"""
        lead = LeadCreate(assessment_id=1, 
            name="张三",
            contact="13800138000",
            company="某贸易有限公司",
            role="创始人",
        )
        assert lead.name == "张三"
        assert lead.contact == "13800138000"

    def test_empty_name_fails(self):
        """姓名不能为空"""
        with pytest.raises(ValidationError):
            LeadCreate(assessment_id=1, 
                name="",
                contact="13800138000",
                company="某公司",
                role="创始人",
            )

    def test_empty_contact_fails(self):
        """联系方式不能为空"""
        with pytest.raises(ValidationError):
            LeadCreate(assessment_id=1, 
                name="张三",
                contact="",
                company="某公司",
                role="创始人",
            )

    def test_empty_company_fails(self):
        """公司不能为空"""
        with pytest.raises(ValidationError):
            LeadCreate(assessment_id=1, 
                name="张三",
                contact="13800138000",
                company="",
                role="创始人",
            )

    def test_empty_role_fails(self):
        """身份不能为空"""
        with pytest.raises(ValidationError):
            LeadCreate(assessment_id=1, 
                name="张三",
                contact="13800138000",
                company="某公司",
                role="",
            )

    def test_contact_min_length(self):
        """联系方式至少 2 个字符"""
        with pytest.raises(ValidationError):
            LeadCreate(assessment_id=1, 
                name="张三",
                contact="1",
                company="某公司",
                role="创始人",
            )

    def test_name_max_length(self):
        """姓名不超过 32 字符"""
        LeadCreate(assessment_id=1, 
            name="阿" * 32,
            contact="13800138000",
            company="某公司",
            role="创始人",
        )
        with pytest.raises(ValidationError):
            LeadCreate(assessment_id=1, 
                name="阿" * 33,
                contact="13800138000",
                company="某公司",
                role="创始人",
            )


class TestAnswerSubmitValidation:
    """答案提交校验测试"""

    def test_valid_answer_passes(self):
        """有效答案通过校验"""
        answer = AnswerSubmit(question_id=1, option_id=3)
        assert answer.question_id == 1
        assert answer.option_id == 3

    def test_negative_question_id_fails(self):
        """question_id 不能为负数"""
        with pytest.raises(ValidationError):
            AnswerSubmit(question_id=-1, option_id=3)

    def test_zero_option_id_fails(self):
        """option_id 不能为 0"""
        with pytest.raises(ValidationError):
            AnswerSubmit(question_id=1, option_id=0)

    def test_negative_option_id_fails(self):
        """option_id 不能为负数"""
        with pytest.raises(ValidationError):
            AnswerSubmit(question_id=1, option_id=-1)

    def test_question_id_as_string_fails(self):
        """question_id 不能是字符串"""
        with pytest.raises(ValidationError):
            AnswerSubmit(question_id="1", option_id=3)

    def test_missing_question_id_fails(self):
        """缺少 question_id"""
        with pytest.raises(ValidationError):
            AnswerSubmit(option_id=3)

    def test_missing_option_id_allowed_for_text_question(self):
        """V2 中 Q1 文本题允许缺少 option_id，API 层按题型做进一步校验"""
        answer = AnswerSubmit(question_id=1, answer_text="智能硬件")
        assert answer.question_id == 1
        assert answer.option_id is None
        assert answer.answer_text == "智能硬件"

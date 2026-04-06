"""
ConversationEndingService 单元测试

测试配置驱动的收尾服务功能
"""

import pytest
from pathlib import Path
from src.modules.conversation.domain.conversation_ending_service import ConversationEndingService
from src.models.user_profile import UserProfile


class TestConversationEndingService:
    """对话收尾服务测试"""

    def setup_method(self):
        """每个测试前重置"""
        config_path = Path(__file__).resolve().parents[2] / "src" / "config" / "ending_config.yaml"
        self.service = ConversationEndingService(str(config_path))

    # ==================== 配置加载测试 ====================

    def test_load_config_success(self):
        """配置加载成功"""
        assert self.service.config is not None
        assert 'endings' in self.service.config

    def test_get_all_scenarios(self):
        """获取所有场景名称"""
        scenarios = self.service.get_all_scenarios()
        assert 'separation' in scenarios
        assert 'age_under_limit' in scenarios
        assert 'normal_complete' in scenarios
        assert 'both_rejected' in scenarios

    # ==================== 关键词检测测试 ====================

    def test_check_ending_separation_keywords(self):
        """检测分居场景 - 关键词"""
        profile = UserProfile(account_id="test")
        result = self.service.check_ending_reason("我正在分居中", profile)
        assert result == "separation"

    def test_check_ending_lgbt_keywords(self):
        """检测LGBT场景 - 关键词"""
        profile = UserProfile(account_id="test")
        result = self.service.check_ending_reason("我喜欢男生", profile)
        assert result == "lgbt_user"

    def test_check_ending_spam_keywords(self):
        """检测骚扰/广告场景 - 关键词"""
        profile = UserProfile(account_id="test")
        result = self.service.check_ending_reason("加我v聊聊", profile)
        assert result == "spam_user"

    def test_check_ending_proxy_keywords(self):
        """检测代相亲场景 - 关键词"""
        profile = UserProfile(account_id="test")
        result = self.service.check_ending_reason("帮我朋友问问", profile)
        assert result == "proxy_user"

    def test_check_ending_divorce_incomplete_extended_keywords(self):
        """检测离异手续未办妥 - 扩展关键词"""
        profile = UserProfile(account_id="test")
        result = self.service.check_ending_reason("我离异，手续还在办", profile)
        assert result == "divorce_incomplete"

    def test_check_ending_no_match(self):
        """检测无匹配场景"""
        profile = UserProfile(account_id="test")
        result = self.service.check_ending_reason("你好，我是单身", profile)
        assert result is None

    # ==================== 字段检测测试 ====================

    def test_check_ending_age_under_limit(self):
        """检测年龄限制 - 字段检测"""
        profile = UserProfile(account_id="test")
        collection_result = {"under_limit": True}
        result = self.service.check_ending_reason("", profile, collection_result)
        assert result == "age_under_limit"

    def test_check_ending_age_not_under_limit(self):
        """检测年龄不限制"""
        profile = UserProfile(account_id="test")
        collection_result = {"under_limit": False}
        result = self.service.check_ending_reason("", profile, collection_result)
        assert result is None

    # ==================== 档案检测测试 ====================

    def test_check_ending_already_ended(self):
        """检测对话已结束 - 档案检测"""
        profile = UserProfile(account_id="test")
        profile.conversation_ended = True
        result = self.service.check_ending_reason("你好", profile)
        assert result == "already_ended"

    # ==================== 模式检测测试 ====================

    def test_check_ending_fake_info_age(self):
        """检测虚假信息 - 年龄异常"""
        profile = UserProfile(account_id="test")
        profile.age = 999
        result = self.service.check_ending_reason("", profile)
        assert result == "fake_info"

    def test_check_ending_fake_info_height(self):
        """检测虚假信息 - 身高异常"""
        profile = UserProfile(account_id="test")
        profile.height = 500
        result = self.service.check_ending_reason("", profile)
        assert result == "fake_info"

    # ==================== 手动触发场景测试 ====================

    def test_check_manual_scenario_normal_complete(self):
        """检测信息收集完成场景"""
        profile = UserProfile(account_id="test")
        profile.sex = "男"
        profile.age = 30
        profile.location = "北京"
        profile.education = "本科"
        profile.occupation = "IT"
        profile.marital_status = "单身"
        profile.partner_requirement = "温柔"
        profile.monthly_income = "2万"
        profile.phone = "13812345678"
        profile.phone_collected = True
        profile.rejected_wechat = True
        profile.collection_progress.update(
            {
                "sex": True,
                "age": True,
                "location": True,
                "education": True,
                "occupation": True,
                "marital_status": True,
                "partner_requirement": True,
                "monthly_income": True,
                "contact": True,
            }
        )
        result = self.service.check_manual_scenario('normal_complete', profile)
        assert result == True

    def test_check_manual_scenario_normal_complete_incomplete(self):
        """检测信息收集未完成"""
        profile = UserProfile(account_id="test")
        profile.sex = "男"
        profile.age = 30
        profile.phone = "13812345678"
        profile.phone_collected = True
        profile.collection_progress["contact"] = True
        # 缺少其他字段
        result = self.service.check_manual_scenario('normal_complete', profile)
        assert result == False

    def test_check_manual_scenario_normal_complete_requires_contact_flow_complete(self):
        """仅拿到电话但微信流程未走完时，不能提前 normal_complete。"""
        profile = UserProfile(account_id="test")
        profile.sex = "男"
        profile.age = 30
        profile.location = "北京"
        profile.education = "本科"
        profile.occupation = "IT"
        profile.marital_status = "单身"
        profile.partner_requirement = "温柔"
        profile.monthly_income = "2万"
        profile.phone = "13812345678"
        profile.phone_collected = True
        profile.collection_progress.update(
            {
                "sex": True,
                "age": True,
                "location": True,
                "education": True,
                "occupation": True,
                "marital_status": True,
                "partner_requirement": True,
                "monthly_income": True,
                "contact": True,
            }
        )

        result = self.service.check_manual_scenario('normal_complete', profile)
        assert result is False

    def test_check_manual_scenario_normal_complete_requires_profile_fields_collected_or_ask_exhausted(self):
        """拿到双联系方式后，核心/中等字段未收完且未问尽，仍不能 normal_complete。"""
        profile = UserProfile(account_id="test")
        profile.phone = "13812345678"
        profile.phone_collected = True
        profile.wechat = "wx12345678"
        profile.wechat_collected = True
        profile.collection_progress["contact"] = True
        profile.sex = "男"
        profile.collection_progress["sex"] = True
        profile.field_ask_count["age"] = 1
        profile.field_ask_count["education"] = 1
        profile.field_ask_count["occupation"] = 1
        profile.field_ask_count["location"] = 1
        profile.field_ask_count["marital_status"] = 0
        profile.field_ask_count["partner_requirement"] = 0
        profile.field_ask_count["monthly_income"] = 0

        result = self.service.check_manual_scenario('normal_complete', profile)
        assert result is False

    def test_check_manual_scenario_both_rejected(self):
        """检测双方都被拒绝场景"""
        profile = UserProfile(account_id="test")
        profile.rejected_phone = True
        profile.rejected_wechat = True
        result = self.service.check_manual_scenario('both_rejected', profile)
        assert result == True

    def test_check_manual_scenario_both_rejected_partial(self):
        """检测只有一方被拒绝"""
        profile = UserProfile(account_id="test")
        profile.rejected_phone = True
        result = self.service.check_manual_scenario('both_rejected', profile)
        assert result == False

    # ==================== AI 生成判断测试 ====================

    def test_should_use_ai_ending_normal_complete(self):
        """AI生成 - 正常完成"""
        assert self.service.should_use_ai_ending('normal_complete') == True

    def test_should_use_ai_ending_both_rejected(self):
        """AI生成 - 双方被拒绝"""
        assert self.service.should_use_ai_ending('both_rejected') == False

    def test_should_use_ai_ending_separation(self):
        """预设话术 - 分居"""
        assert self.service.should_use_ai_ending('separation') == False

    def test_should_use_ai_ending_spam(self):
        """预设话术 - 骚扰"""
        assert self.service.should_use_ai_ending('spam_user') == False

    # ==================== 话术获取测试 ====================

    def test_get_ending_response_preset(self):
        """获取预设话术"""
        response = self.service.get_ending_response('separation')
        assert response is not None
        assert response.strip() != ""

    def test_get_ending_response_ai(self):
        """获取AI生成话术 - 返回None"""
        response = self.service.get_ending_response('normal_complete')
        assert response is None

    def test_get_ending_response_empty_template(self):
        """获取空模板话术 - 骚扰静默处理"""
        response = self.service.get_ending_response('spam_user')
        assert response == ""

    def test_get_ai_extra_instructions(self):
        """获取AI附加指令"""
        instructions = self.service.get_ai_extra_instructions('normal_complete')
        assert "信息收集已完成" in instructions

    def test_get_ai_extra_instructions_empty(self):
        """获取AI附加指令 - 预设话术场景"""
        instructions = self.service.get_ai_extra_instructions('separation')
        assert instructions == ""

    # ==================== 用户状态更新测试 ====================

    def test_update_profile_for_ending(self):
        """更新用户状态 - 普通收尾"""
        profile = UserProfile(account_id="test")
        self.service.update_profile_for_ending('normal_complete', profile)
        assert profile.conversation_ended == True

    def test_update_profile_for_ending_spam(self):
        """更新用户状态 - 骚扰用户"""
        profile = UserProfile(account_id="test")
        self.service.update_profile_for_ending('spam_user', profile)
        assert profile.conversation_ended == True
        assert profile.spam_user == True

    def test_update_profile_for_ending_already_married(self):
        """更新用户状态 - 已婚用户"""
        profile = UserProfile(account_id="test")
        self.service.update_profile_for_ending('already_married', profile)
        assert profile.conversation_ended == True
        assert profile.already_married == True

    def test_update_profile_for_ending_proxy_user(self):
        """更新用户状态 - 代相亲用户"""
        profile = UserProfile(account_id="test")
        self.service.update_profile_for_ending('proxy_user', profile)
        assert profile.conversation_ended == True
        assert profile.proxy_user == True

    # ==================== 一站式检测测试 ====================

    def test_check_and_get_ending_keyword_scenario(self):
        """一站式检测 - 关键词场景"""
        profile = UserProfile(account_id="test")
        result = self.service.check_and_get_ending("我正在分居中", profile)
        assert result is not None
        assert result['scenario'] == 'separation'
        assert result['use_ai'] == False
        assert 'response' in result
        assert profile.conversation_ended == True

    def test_check_and_get_ending_manual_scenario(self):
        """一站式检测 - 手动场景（双方被拒绝）"""
        profile = UserProfile(account_id="test")
        profile.rejected_phone = True
        profile.rejected_wechat = True
        result = self.service.check_and_get_ending("好的", profile)
        assert result is not None
        assert result['scenario'] == 'both_rejected'
        assert result['use_ai'] == False
        assert 'response' in result

    def test_check_and_get_ending_no_ending(self):
        """一站式检测 - 无收尾"""
        profile = UserProfile(account_id="test")
        result = self.service.check_and_get_ending("你好", profile)
        assert result is None

    def test_build_ending_info_for_ai_scenario(self):
        """直接构建收尾信息 - AI 场景"""
        profile = UserProfile(account_id="test")
        result = self.service.build_ending_info("normal_complete", profile)
        assert result["scenario"] == "normal_complete"
        assert result["use_ai"] == True
        assert "extra_instructions" in result
        assert "response" not in result
        assert profile.conversation_ended == True

    def test_build_ending_info_for_preset_scenario(self):
        """直接构建收尾信息 - 预设场景"""
        profile = UserProfile(account_id="test")
        result = self.service.build_ending_info("separation", profile)
        assert result["scenario"] == "separation"
        assert result["use_ai"] == False
        assert "response" in result
        assert result["response"]
        assert profile.conversation_ended == True

    # ==================== 场景描述测试 ====================

    def test_get_scenario_description(self):
        """获取场景描述"""
        desc = self.service.get_scenario_description('separation')
        assert "分居" in desc

    def test_get_scenario_description_not_found(self):
        """获取不存在的场景描述"""
        desc = self.service.get_scenario_description('not_exist')
        assert desc == ""

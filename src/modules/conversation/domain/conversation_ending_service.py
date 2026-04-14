"""
对话收尾服务 - 统一管理所有收尾场景

基于配置驱动设计，支持:
1. 场景配置：ending_config.yaml
2. 场景检测：ConversationEndingService.check_ending_reason()
3. AI 场景附加指令：ConversationEndingService.get_ai_extra_instructions()
4. 用户状态更新:ConversationEndingService.update_profile_for_ending()

新增收尾场景只需要修改 ending_config.yaml 配置文件即可，无需修改代码。
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import random
import yaml
from src.models.user_profile import UserProfile
from src.modules.conversation.domain.expectation_service import ExpectationService
from src.modules.profile_collection.domain.profile_collection_policy import ProfileCollectionPolicy
from src.services.collection.contact_collection_service import ContactCollectionService

logger = logging.getLogger(__name__)


class ConversationEndingService:
    """
    对话收尾服务

    统一管理所有收尾场景，提供：
    1. 场景检测（基于配置动态检测）
    2. AI 收尾附加指令
    3. 用户状态更新
    """

    def __init__(self, config_path: Optional[str] = None):
        """初始化服务"""
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Preferred location is src/config/ending_config.yaml.
            # Keep backward compatibility with legacy src/modules/config path.
            project_src = Path(__file__).resolve().parents[3]
            primary = project_src / "config" / "ending_config.yaml"
            legacy = project_src / "modules" / "config" / "ending_config.yaml"
            self.config_path = primary if primary.exists() else legacy
        self.config: dict = {}
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        if not self.config_path.exists():
            logger.warning(f"[收尾服务] 配置文件不存在: {self.config_path}")
            return

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        logger.info(f"[收尾服务] 加载配置完成，共 {len(self.config.get('endings', {}))} 个场景")

    def get_all_scenarios(self) -> List[str]:
        """获取所有收尾场景名称"""
        return list(self.config.get('endings', {}).keys())

    def check_ending_reason(
        self,
        user_message: str,
        profile: UserProfile,
        collection_result: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        检测是否需要收尾，返回收尾场景名称

        Args:
            user_message: 用户消息
            profile: 用户档案
            collection_result: 信息收集结果

        Returns:
            收尾场景名称，如果不需要收尾则返回 None
        """
        endings = self.config.get('endings', {})

        for scenario_name, scenario_config in endings.items():
            detection = scenario_config.get('detection', {})
            detection_type = detection.get('type', 'manual')

            # 跳过手动触发的场景（由代码逻辑决定）
            if detection_type == 'manual':
                continue

            # 关键词检测
            if detection_type == 'keywords':
                keywords = detection.get('keywords', [])
                if any(kw in user_message for kw in keywords):
                    logger.info(f"[收尾检测] 命中关键词场景: {scenario_name}")
                    return scenario_name

            # 字段检测（检查 collection_result）
            elif detection_type == 'field_check':
                field = detection.get('field')
                if field and collection_result:
                    if collection_result.get(field):
                        logger.info(f"[收尾检测] 命中字段检测场景: {scenario_name}")
                        return scenario_name

            # 用户档案检测
            elif detection_type == 'profile_check':
                field = detection.get('field')
                expected_value = detection.get('value')
                if field and hasattr(profile, field):
                    actual_value = getattr(profile, field, None)
                    if actual_value == expected_value:
                        logger.info(f"[收尾检测] 命中档案检测场景: {scenario_name}")
                        return scenario_name

            # 模式检测（检查多个字段）
            elif detection_type == 'pattern_check':
                patterns = detection.get('patterns', [])
                for pattern in patterns:
                    field = pattern.get('field')
                    values = pattern.get('values', [])
                    if field and hasattr(profile, field):
                        actual_value = getattr(profile, field, None)
                        if actual_value in values:
                            logger.info(f"[收尾检测] 命中模式检测场景: {scenario_name}")
                            return scenario_name

        return None

    def check_manual_scenario(
        self,
        scenario_name: str,
        profile: UserProfile,
        collection_result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        检查手动触发场景的条件是否满足

        Args:
            scenario_name: 场景名称
            profile: 用户档案

        Returns:
            是否满足该场景的触发条件
        """
        endings = self.config.get('endings', {})
        scenario_config = endings.get(scenario_name, {})
        detection = scenario_config.get('detection', {})

        # 只处理手动触发的场景
        if detection.get('type') != 'manual':
            return False

        # 特殊场景的条件检查
        if scenario_name == 'normal_complete':
            # 正常收尾：
            # 1. 至少已拿到一个真实联系方式
            # 2. 联系方式流程本身已经走完，避免“刚拿到电话就提前收尾”
            # 3. 资料主线（核心+中等字段）已经完成或问尽
            # 4. 当前轮确实有收集进展，避免在“拒绝联系方式”这类空提取轮误收尾
            policy = ProfileCollectionPolicy()
            contact_service = ContactCollectionService()
            has_contact = bool(
                profile.collection_progress.get("contact", False)
                or (profile.phone and profile.phone_collected)
                or (profile.wechat and profile.wechat_collected)
            )
            contact_flow_complete = contact_service.is_contact_complete(profile)
            profile_complete_or_exhausted = policy.is_coverage_complete(profile)
            collected_this_turn = True if collection_result is None else bool(collection_result.get("collected"))
            finalized_single_contact_path = bool(
                (profile.rejected_phone and (profile.wechat and profile.wechat_collected) and not (profile.phone and profile.phone_collected))
                or (profile.rejected_wechat and (profile.phone and profile.phone_collected) and not (profile.wechat and profile.wechat_collected))
            )
            return (
                has_contact
                and contact_flow_complete
                and profile_complete_or_exhausted
                and (collected_this_turn or finalized_single_contact_path)
            )

        elif scenario_name == 'both_rejected':
            # 双方都被拒绝，且没有任何真实联系方式留存
            has_real_contact = bool(
                (profile.phone and profile.phone_collected)
                or (profile.wechat and profile.wechat_collected)
            )
            return profile.rejected_phone and profile.rejected_wechat and not has_real_contact

        return False

    def get_ai_extra_instructions(self, scenario_name: str) -> str:
        """
        获取 AI 生成的附加指令

        Args:
            scenario_name: 场景名称

        Returns:
            附加指令
        """
        endings = self.config.get('endings', {})
        scenario_config = endings.get(scenario_name, {})
        return scenario_config.get('extraInstructions', '')

    def compose_ai_extra_instructions(self, scenario_name: str, profile: UserProfile) -> str:
        """为 AI 收尾场景组合动态附加指令。"""
        base = str(self.get_ai_extra_instructions(scenario_name) or "").strip()
        if scenario_name != "normal_complete":
            return base

        has_any_contact = bool(
            (getattr(profile, "phone_collected", False) and getattr(profile, "phone", None))
            or (getattr(profile, "wechat_collected", False) and getattr(profile, "wechat", None))
        )
        if not has_any_contact:
            return base

        expectation_service = ExpectationService()
        contact_instruction = expectation_service.build_contact_completion_generation_instruction(profile)
        if not base:
            return contact_instruction
        return f"{base} {contact_instruction}".strip()

    def should_use_ai_ending(self, scenario_name: str) -> bool:
        """按配置判断该收尾场景是否应走 AI 生成。"""
        endings = self.config.get('endings', {})
        scenario_config = endings.get(scenario_name, {})
        return bool(scenario_config.get('useAiEnding', False))

    def get_ending_response(self, scenario_name: str) -> Optional[str]:
        """按配置获取预设收尾话术；AI 场景返回 None。"""
        if self.should_use_ai_ending(scenario_name):
            return None

        endings = self.config.get('endings', {})
        scenario_config = endings.get(scenario_name, {})
        templates = list(scenario_config.get('templates', []) or [])
        if not templates:
            return ""
        return random.choice(templates)

    def update_profile_for_ending(self, scenario_name: str, profile: UserProfile) -> None:
        """
        收尾时更新用户状态

        Args:
            scenario_name: 场景名称
            profile: 用户档案
        """
        endings = self.config.get('endings', {})
        scenario_config = endings.get(scenario_name, {})
        profile_updates = scenario_config.get('profileUpdates', {})

        for field, value in profile_updates.items():
            if hasattr(profile, field):
                setattr(profile, field, value)
                logger.info(f"[收尾更新] 更新用户状态: {field} = {value}")

    def get_scenario_description(self, scenario_name: str) -> str:
        """
        获取场景描述

        Args:
            scenario_name: 场景名称

        Returns:
            场景描述
        """
        endings = self.config.get('endings', {})
        scenario_config = endings.get(scenario_name, {})
        return scenario_config.get('description', '')

    def check_and_get_ending(
        self,
        user_message: str,
        profile: UserProfile,
        collection_result: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        一站式检测收尾并返回完整信息

        Args:
            user_message: 用户消息
            profile: 用户档案
            collection_result: 信息收集结果

        Returns:
            收尾信息字典，包含：
            - scenario: 场景名称
            - use_ai: 是否使用 AI（固定 True）
            - extra_instructions: AI 附加指令
            如果不需要收尾则返回 None
        """
        # 1. 检测关键词/字段触发场景
        scenario = self.check_ending_reason(user_message, profile, collection_result)

        # 2. 检测手动触发场景
        if not scenario:
            for manual_scenario in ['normal_complete', 'both_rejected']:
                if self.check_manual_scenario(manual_scenario, profile, collection_result):
                    scenario = manual_scenario
                    break

        if not scenario:
            return None

        # 3. 获取收尾信息（拟人化优先：统一走 AI 收尾）
        use_ai = self.should_use_ai_ending(scenario)
        result = {
            'scenario': scenario,
            'use_ai': use_ai,
            'description': self.get_scenario_description(scenario),
            'extra_instructions': self.compose_ai_extra_instructions(scenario, profile),
        }
        if not use_ai:
            result['response'] = self.get_ending_response(scenario)

        # 4. 更新用户状态
        self.update_profile_for_ending(scenario, profile)

        logger.info(f"[收尾服务] 触发收尾场景: {scenario}, AI生成: {use_ai}")
        return result

    def build_ending_info(self, scenario_name: str, profile: UserProfile) -> Dict[str, Any]:
        """直接为已知场景构建 ending_info，并更新用户状态。"""
        use_ai = self.should_use_ai_ending(scenario_name)
        result = {
            'scenario': scenario_name,
            'use_ai': use_ai,
            'description': self.get_scenario_description(scenario_name),
            'extra_instructions': self.compose_ai_extra_instructions(scenario_name, profile),
        }
        if not use_ai:
            result['response'] = self.get_ending_response(scenario_name)

        self.update_profile_for_ending(scenario_name, profile)
        logger.info(f"[收尾服务] 直接构建收尾场景: {scenario_name}, AI生成: {use_ai}")
        return result

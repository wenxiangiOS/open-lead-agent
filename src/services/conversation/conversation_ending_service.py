"""
对话收尾服务 - 统一管理所有收尾场景

基于配置驱动设计，支持:
1. 场景配置：ending_config.yaml
2. 场景检测：ConversationEndingService.check_ending_reason()
3. 场景话术：ConversationEndingService.get_ending_response()
4. AI 场景判断：ConversationEndingService.should_use_ai_ending()
5. 用户状态更新:ConversationEndingService.update_profile_for_ending()

新增收尾场景只需要修改 ending_config.yaml 配置文件即可，无需修改代码。
"""

import random
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import yaml
from src.models.user_profile import UserProfile

logger = logging.getLogger(__name__)


class ConversationEndingService:
    """
    对话收尾服务

    统一管理所有收尾场景，提供：
    1. 场景检测（基于配置动态检测）
    2. 话术生成（预设模板或 AI 生成）
    3. 用户状态更新
    """

    def __init__(self, config_path: Optional[str] = None):
        """初始化服务"""
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = Path(__file__).resolve().parents[2] / "config" / "ending_config.yaml"
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
            # 信息收集完成：
            # 1. 满足可服务资料
            # 2. 当前轮确实收集到了信息（避免在“拒绝联系方式”这种空提取轮误收尾）
            # 3. 联系方式流程没有待推进的下一步
            has_contact = bool(
                profile.collection_progress.get("contact", False)
                or (profile.phone and profile.phone_collected)
                or (profile.wechat and profile.wechat_collected)
            )
            has_core = all([
                bool(getattr(profile, "sex", None)),
                bool(getattr(profile, "age", None)),
                bool(getattr(profile, "location", None)),
                bool(getattr(profile, "marital_status", None)),
                bool(getattr(profile, "education", None) or getattr(profile, "occupation", None)),
            ])
            collected_this_turn = True if collection_result is None else bool(collection_result.get("collected"))
            has_pending_contact_step = False if collection_result is None else (
                (profile.phone and profile.phone_collected and not profile.wechat_collected and not profile.rejected_wechat)
                or (profile.wechat and profile.wechat_collected and not profile.phone_collected and not profile.rejected_phone)
            )
            return has_contact and has_core and collected_this_turn and not has_pending_contact_step

        elif scenario_name == 'both_rejected':
            # 双方都被拒绝，且没有任何真实联系方式留存
            has_real_contact = bool(
                (profile.phone and profile.phone_collected)
                or (profile.wechat and profile.wechat_collected)
            )
            return profile.rejected_phone and profile.rejected_wechat and not has_real_contact

        return False

    def should_use_ai_ending(self, scenario_name: str) -> bool:
        """
        判断是否使用 AI 生成话术

        Args:
            scenario_name: 场景名称

        Returns:
            是否使用 AI 生成
        """
        endings = self.config.get('endings', {})
        scenario_config = endings.get(scenario_name, {})
        return scenario_config.get('useAiEnding', False)

    def get_ending_response(self, scenario_name: str) -> Optional[str]:
        """
        获取收尾话术

        Args:
            scenario_name: 场景名称

        Returns:
            收尾话术，如果是 AI 生成场景则返回 None
        """
        endings = self.config.get('endings', {})
        scenario_config = endings.get(scenario_name, {})

        if scenario_config.get('useAiEnding', False):
            return None

        templates = scenario_config.get('templates', [])
        if not templates:
            return ""

        return random.choice(templates)

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
            - use_ai: 是否使用 AI
            - response: 预设话术（如果 use_ai=False）
            - extra_instructions: AI 附加指令（如果 use_ai=True）
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

        # 3. 获取收尾信息
        use_ai = self.should_use_ai_ending(scenario)
        result = {
            'scenario': scenario,
            'use_ai': use_ai,
            'description': self.get_scenario_description(scenario),
        }

        if use_ai:
            result['extra_instructions'] = self.get_ai_extra_instructions(scenario)
        else:
            result['response'] = self.get_ending_response(scenario)

        # 4. 更新用户状态
        self.update_profile_for_ending(scenario, profile)

        logger.info(f"[收尾服务] 触发收尾场景: {scenario}, AI生成: {use_ai}")
        return result

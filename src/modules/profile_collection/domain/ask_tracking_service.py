"""
追问跟踪服务

负责识别 AI 主动询问了哪些字段，并维护字段追问次数与自动跳过逻辑。
"""

import logging
import os

from src.services.data.user_service import UserService

logger = logging.getLogger(__name__)


class AskTrackingService:
    """管理智能追问字段计数。"""

    PARTNER_REQUIREMENT_CONTEXT_KEYWORDS = [
        '找什么样的', '有什么要求', '择偶要求', '找什么类型',
        '喜欢什么样的', '对...有要求', '要求对方', '对方的要求',
        '想找', '希望找', '要求是', '有什么择偶', '另一半', '在意的点'
    ]

    PARTNER_REQUIREMENT_FIELDS = {'height', 'age', 'education', 'location', 'monthly_income', 'occupation'}
    LOW_PRIORITY_FIELDS = {'height', 'weight', 'last_name'}
    MEDIUM_FIELDS = {'monthly_income', 'partner_requirement'}
    COOLDOWN_MANAGED_FIELDS = {'sex', 'age', 'education', 'occupation', 'location', 'marital_status'}
    LOCATION_PATTERNS = [
        '在哪个城市', '在哪座城市', '现在在哪', '现在在深圳工作生活',
        '工作生活嘛', '工作生活吗', '工作生活呀', '工作生活呢', '工作生活',
        '在哪工作生活', '在哪里工作生活', '工作生活在哪里',
    ]
    OCCUPATION_PATTERNS = [
        '做什么工作的', '从事什么工作', '做哪方面工作', '做什么工作',
        '是做什么的', '做哪行', '从事哪方面', '职业是什么', '做什么呀',
    ]

    # Phase 2: 语义槽映射（用于更精细的去重）
    SEMANTIC_SLOT_PATTERNS = {
        # 地区偏好
        'partner_pref_location': [
            '同城', '本地', '深圳', '广州', '北京', '上海', '杭州', '成都', '武汉', '南京',
            '附近的', '本地的', '同一个城市', '这边', '那边',
        ],
        # 年龄偏好
        'partner_pref_age': [
            '不超过', '以下', '以上', '岁', '90后', '80后', '00后', '95后', '同龄',
            '大一点', '小一点', '差不多大',
        ],
        # 身高偏好
        'partner_pref_height': [
            '身高', 'cm', '米', '高', '不矮',
        ],
        # 性格偏好
        'partner_pref_personality': [
            '性格', '温柔', '开朗', '内向', '外向', '稳重', '活泼', '安静',
            '幽默', '有趣', '随和', '善良', '体贴',
        ],
        # 收入偏好
        'partner_pref_income': [
            '收入', '月薪', '年薪', '工资', '万',
        ],
    }

    @staticmethod
    def detect_semantic_slot(user_message: str) -> Optional[str]:
        """
        Phase 2: 检测用户消息中提供的语义槽。

        Args:
            user_message: 用户消息

        Returns:
            检测到的语义槽名称，        """
        message = str(user_message or "").strip()
        if not message:
            return None

        for slot_name, patterns in AskTrackingService.SEMANTIC_SLOT_PATTERNS.items():
            for pattern in patterns:
                if pattern in message:
                    return slot_name

        return None

    @staticmethod
    def should_block_slot_ask(
        user_profile,
        slot_name: str,
        max_recent_slots: int = 5,
    ) -> bool:
        """
        Phase 2: 判断是否应该阻止对某个语义槽的追问。

        规则：
        1. 用户近 5 轮内明确给过该语义槽，        2. 该槽已收集完成

        Args:
            user_profile: 用户画像
            slot_name: 语义槽名称
            max_recent_slots: 最大历史轮数

        Returns:
            是否应该阻止追问
        """
        # 检查是否在最近的语义槽历史中
        recent_slots = getattr(user_profile, 'recent_semantic_slots', []) or []
        if slot_name in recent_slots[-max_recent_slots:]:
            logger.info(f"[语义槽去重] {slot_name} 在最近 {max_recent_slots} 轮内已提供，阻止追问")
            return True

        return False

    @staticmethod
    def record_semantic_slot(user_profile, slot_name: str, max_slots: int = 5) -> None:
        """
        Phase 2: 记录用户提供的语义槽。

        Args:
            user_profile: 用户画像
            slot_name: 语义槽名称
            max_slots: 最大保留数量
        """
        recent_slots = list(getattr(user_profile, 'recent_semantic_slots', []) or [])
        # 避免重复
        if slot_name not in recent_slots:
            recent_slots.append(slot_name)
            # 只保留最近的 max_slots 个
            if len(recent_slots) > max_slots:
                recent_slots = recent_slots[-max_slots:]
            user_profile.recent_semantic_slots = recent_slots
            logger.info(f"[语义槽记录] 记录 {slot_name}，当前历史: {recent_slots}")

    @staticmethod
    def _env_int(name: str, default: int) -> int:
        try:
            return int(os.getenv(name, str(default)))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        return raw.strip().lower() in ("1", "true", "yes", "on")

    def __init__(self, user_service: UserService):
        self.user_service = user_service

    async def track_ai_asked_fields(self, account_id: str, ai_response: str) -> None:
        """追踪 AI 询问的字段。"""
        from src.config.settings import get_field_keywords

        field_keywords = get_field_keywords()
        is_asking_partner_requirement = any(
            kw in ai_response for kw in self.PARTNER_REQUIREMENT_CONTEXT_KEYWORDS
        )

        asked_fields = []
        ai_response_lower = ai_response.lower()

        if is_asking_partner_requirement:
            asked_fields.append('partner_requirement')

        if any(pattern in ai_response for pattern in self.LOCATION_PATTERNS):
            asked_fields.append('location')

        if any(pattern in ai_response for pattern in self.OCCUPATION_PATTERNS):
            asked_fields.append('occupation')

        for field, keywords in field_keywords.items():
            if is_asking_partner_requirement and field in self.PARTNER_REQUIREMENT_FIELDS:
                continue
            if field in self.LOW_PRIORITY_FIELDS:
                continue
            if field == 'partner_requirement':
                continue
            if field in asked_fields:
                continue

            for keyword in keywords:
                if field == 'occupation' and keyword == '工作':
                    continue
                if keyword in ai_response_lower or keyword in ai_response:
                    asked_fields.append(field)
                    break

        if not asked_fields:
            return

        asked_fields = list(dict.fromkeys(asked_fields))

        user_profile = await self.user_service.get_user_profile(account_id)
        cooldown_turns = self._env_int("MQ_FIELD_ASK_COOLDOWN_TURNS", 2)
        skip_guard_enabled = self._env_bool("MQ_SKIP_GUARD_ENABLED", True)
        max_history = self._env_int("MQ_RECENT_ASKED_HISTORY_MAX", 10)
        cooldown_fields = set(user_profile.get_cooldown_fields(cooldown_turns))
        recorded_primary = False

        for field in asked_fields:
            is_collected = user_profile.collection_progress.get(field, False)
            is_skipped = field in user_profile.skipped_fields

            if is_collected or is_skipped:
                continue

            if field in self.COOLDOWN_MANAGED_FIELDS and field in cooldown_fields:
                logger.info(f"[智能追问-冷却] 字段 {field} 处于冷却窗口，跳过计数与自动跳过")
                continue

            if field == 'contact':
                phone_keywords = ['电话', '手机号', '号码']
                wechat_keywords = ['微信']
                asked_phone = any(kw in ai_response_lower for kw in phone_keywords)
                asked_wechat = any(kw in ai_response_lower for kw in wechat_keywords)
                if asked_phone or asked_wechat:
                    logger.debug("[智能追问] 检测到联系方式询问，由 ContactCollectionService 管理")
                    continue

            user_profile.increment_ask_count(field)
            current_count = user_profile.get_ask_count(field)
            logger.debug(f"[智能追问] AI询问了字段 {field}，当前追问次数: {current_count}")
            if field in self.COOLDOWN_MANAGED_FIELDS and not recorded_primary:
                user_profile.mark_recent_asked_field(field, max_history=max_history)
                recorded_primary = True

            # 中等字段问过一次后转为被动提取，避免像表单机一样反复追问。
            if field in self.MEDIUM_FIELDS:
                user_profile.close_active_ask(field)
                logger.debug(f"[智能追问] 中等字段 {field} 已关闭主动追问，后续仅被动提取")
                continue

            if current_count >= 2 and not skip_guard_enabled:
                user_profile.skipped_fields[field] = True
                logger.debug(f"[智能追问] 字段 {field} 已问2次未回答，自动标记为跳过")
            elif current_count >= 2 and skip_guard_enabled:
                logger.debug(f"[智能追问-防抖] 字段 {field} 达到2次，已启用 skip 防抖，不自动标记跳过")

        await self.user_service.save_user_profile(account_id, user_profile)

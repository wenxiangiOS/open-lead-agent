"""
重构后的聊天服务 - 处理对话并隐晦地收集用户信息

这是一个重构版本，将原来 1113 行的单一服务拆分为多个专职服务：
- ExtractionService: 信息提取
- ValidationService: 数据验证
- DialogueManager: 对话状态管理
- ChatService: 主流程编排
"""

import logging
from typing import Dict, Any, Optional

from src.models.personality import PersonalityProfile
from src.models.requests import ChatRequest
from src.models.user_profile import UserProfile
from src.services.ai_service import AIService
from src.services.user_service import UserService
from src.services.extraction_service import ExtractionService
from src.services.validation_service import ValidationService
from src.services.dialogue_manager import DialogueManager
from src.services.refusal_service import RefusalService
from src.services.field_skip_service import FieldSkipService
from src.utils.validators import InputValidator, RefusalDetector
from src.core.exceptions import ValidationException, AIServiceException
from src.config.settings import settings

logger = logging.getLogger(__name__)


class ChatService:
    """
    聊天服务 - 处理对话并隐晦地收集用户信息

    核心功能：
    1. 拟人化对话 - 让用户察觉不到是AI
    2. 隐晦信息收集 - 自然地收集用户信息
    3. 智能容错 - 错误提醒有限制
    4. 性别自适应 - 根据性别调整称呼
    5. 目标对象反推 - 利用目标对象性别推断用户性别

    架构：
    - 使用 ExtractionService 处理信息提取
    - 使用 ValidationService 处理数据验证
    - 使用 DialogueManager 管理对话状态
    - 本类主要负责流程编排
    """

    def __init__(
        self,
        ai_service: AIService,
        user_service: UserService
    ):
        """初始化聊天服务"""
        self.ai_service = ai_service
        self.user_service = user_service

        # 初始化专职服务
        self.extraction_service = ExtractionService(user_service)
        self.validation_service = ValidationService()
        self.dialogue_manager = DialogueManager(user_service)
        self.refusal_service = RefusalService()
        self.field_skip_service = FieldSkipService()
        self.personality_profile = PersonalityProfile()

        # 临时存储可能的拒绝字段
        self._temp_refused_fields = {}

        # 无意义输入计数器键名前缀
        self._nonsense_count_prefix = "nonsense_count:"

    async def process_chat_request(self, request: ChatRequest) -> Dict[str, Any]:
        """
        处理聊天请求 - 核心业务逻辑

        Args:
            request: 聊天请求

        Returns:
            Dict[str, Any]: 响应数据
        """
        account_id = request.accountId

        try:
            # 1. 获取用户档案
            user_profile = await self.user_service.get_user_profile(account_id)

            # 2. 检查信息是否已收集完成且用户只回复确认词（如"嗯"、"好"）
            # 如果是，直接返回空响应，避免死循环
            if user_profile.is_collection_complete():
                # 确认词列表
                affirmative_words = ['嗯', '好', '好的', '行', '可以', 'ok', '是的', '对', '是']
                is_affirmative = request.question.strip() in affirmative_words
                if is_affirmative:
                    logger.info(f"[信息收集完成] 用户只回复确认词，不调用AI，返回空响应")
                    return {
                        "success": True,
                        "response": "",  # 空响应，不显示任何内容
                        "collected_info": {},
                        "collection_complete": True,
                        "dialogId": request.dialogId
                    }

            # 3. 更新人设性别
            self.dialogue_manager.update_user_sex(user_profile)

            # 4. 检查输入是否可理解
            if not InputValidator.is_understandable(request.question):
                error_response = "抱歉，我没太理解您的意思，能换个方式说吗？"
                return self._success_response(error_response, request.dialogId)

            # 4.5. 检测无意义输入（乱码、表情符号堆砌等）
            nonsense_response = await self._check_and_handle_nonsense(request.question, account_id, user_profile)
            if nonsense_response:
                # 返回人性化回复
                return await self._build_chat_response(
                    account_id,
                    user_profile,
                    nonsense_response,
                    {},
                    request.dialogId
                )

            # 5. 检测用户拒绝
            await self._handle_refusal_detection(request.question, account_id)

            # 5. 获取对话上下文
            conversation_context = await self.dialogue_manager.get_conversation_context(account_id)

            # 6. 构建主对话提示词
            main_prompt = self.dialogue_manager.build_main_dialogue_prompt(
                request.question,
                user_profile,
                conversation_context
            )

            # 检查信息是否已收集完成（包含"已留联系"标记）
            from src.services.extraction_service import ExtractionService
            extraction_service = ExtractionService(self.user_service)
            collected_info = extraction_service.get_collected_info_summary(user_profile)
            if "已留联系" in collected_info:
                # 信息已全部收集完成，根据用户输入决定如何回复
                user_input = request.question.strip()

                # 检查是否是问候语或问题（如"在吗"、"你好"、"嗨"等）
                greeting_words = ['在吗', '在不在', '你好', '您好', '嗨', '哈喽', 'hello', 'hi']
                is_greeting = any(word in user_input for word in greeting_words)

                if is_greeting:
                    # 用户打招呼，自然回复"在的呀～"
                    logger.info(f"[信息收集完成] 用户打招呼，返回自然回复")
                    natural_response = "在的呀～小哥哥，有什么可以帮你的吗呀"
                    return await self._build_chat_response(
                        account_id,
                        user_profile,
                        natural_response,
                        {"collected": False, "all_fields": []},
                        request.dialogId
                    )
                else:
                    # 其他情况，返回收尾话术（但只返回一次，不要重复）
                    # 检查是否已经发送过收尾话术
                    last_response = await self.dialogue_manager.get_last_response(account_id)
                    closing_message = "好的呀～那你等好消息啦，祝你早日脱单🥰 匹配一般1-8小时哒~ 牵线同事联系前会提前约时间不打扰你～"

                    if last_response and closing_message in last_response:
                        # 已经发送过收尾话术，返回空响应
                        logger.info(f"[信息收集完成] 已发送过收尾话术，返回空响应")
                        return await self._build_chat_response(
                            account_id,
                            user_profile,
                            "",
                            {"collected": False, "all_fields": []},
                            request.dialogId
                        )
                    else:
                        # 第一次，返回收尾话术
                        logger.info(f"[信息收集完成] 检测到'已留联系'标记，直接返回收尾话术")
                        return await self._build_chat_response(
                            account_id,
                            user_profile,
                            closing_message,
                            {"collected": False, "all_fields": []},
                            request.dialogId
                        )

            # 7. 调用 AI 生成回复
            ai_response = await self._call_ai(main_prompt, account_id)

            # 8. 从 AI 回复中提取信息
            extracted_data = self.extraction_service.extract_json_from_response(ai_response)

            # 9. 处理提取的数据
            collection_result = await self._process_collection_result(
                account_id,
                user_profile,
                extracted_data,
                request.question
            )

            # 重新获取 user_profile 以获得最新数据
            user_profile = await self.user_service.get_user_profile(account_id)

            # 10. 处理联系方式验证
            enhanced_response = await self._handle_contact_validation(
                account_id,
                user_profile,
                collection_result,
                ai_response
            )

            # 11. 清理回复（移除 XML 标签）
            final_response = self._clean_response(enhanced_response)

            # 12. 更新对话状态
            await self._update_conversation_state(
                account_id,
                request.question,
                final_response,
                ai_response
            )

            # 13. 构建响应
            return await self._build_chat_response(
                account_id,
                user_profile,
                final_response,
                collection_result,
                request.dialogId
            )

        except Exception as e:
            logger.error(f"[对话处理] 错误: {e}")
            from src.core.error_handler import handle_error
            error_response = handle_error(e, context="chat", user_id=account_id)
            return self._error_response(error_response.get('error', '处理失败'), request.dialogId)

    async def _handle_refusal_detection(self, user_message: str, account_id: str) -> None:
        """处理拒绝检测"""
        last_response = await self.dialogue_manager.get_last_response(account_id)

        # 检测用户是否拒绝
        is_refusing = self.refusal_service.is_refusing(user_message)
        if is_refusing and last_response:
            refused_fields = self.extraction_service.infer_refused_fields(last_response)
            self._temp_refused_fields[account_id] = refused_fields

    async def _call_ai(self, prompt: str, account_id: str) -> str:
        """
        调用 AI 服务（带超时控制）

        Args:
            prompt: 完整的对话提示词
            account_id: 用户ID

        Returns:
            str: AI 回复内容

        Raises:
            AIServiceException: AI 调用失败或超时
        """
        try:
            # 使用简单的系统提示词确保用中文回复
            response = await self.ai_service.generate_response(
                message=prompt,
                system_prompt="你是一个说中文的AI助手，请用中文回复用户。",
                timeout=60  # 60秒超时
            )
            return response
        except AIServiceException as e:
            # 直接传递 AI 服务异常
            logger.error(f"[AI调用] 失败: {e}")
            raise
        except Exception as e:
            logger.error(f"[AI调用] 未预期的错误: {e}")
            raise AIServiceException(f"AI 服务调用失败: {str(e)}")

    async def _process_collection_result(
        self,
        account_id: str,
        user_profile: UserProfile,
        extracted_data: Dict[str, Any],
        user_message: str
    ) -> Dict[str, Any]:
        """处理收集结果"""
        # 处理提取的数据
        collection_result = await self.extraction_service.process_extracted_data(
            account_id,
            user_profile,
            extracted_data
        )

        # 处理拒绝字段
        if account_id in self._temp_refused_fields:
            refused_fields = self._temp_refused_fields[account_id]
            collected_fields = [f['field'] for f in collection_result.get('all_fields', [])]

            # 标记被拒绝但未被提取的字段
            for field in refused_fields:
                if field not in collected_fields:
                    self.user_service.skip_user_profile_field(account_id, field)
                    logger.info(f"[拒绝标记] 用户拒绝字段: {field}")

            del self._temp_refused_fields[account_id]

        return collection_result

    async def _handle_contact_validation(
        self,
        account_id: str,
        user_profile: UserProfile,
        collection_result: Dict[str, Any],
        ai_response: str
    ) -> str:
        """处理联系方式验证"""
        # 检查是否收集到联系方式
        collected_contact = None
        for field_info in collection_result.get('all_fields', []):
            if field_info.get('field') == 'contact':
                collected_contact = field_info.get('value')
                break

        logger.info(f"[联系方式检查] collected_contact={collected_contact}, all_fields={collection_result.get('all_fields', [])}")

        if collected_contact is None:
            return ai_response

        # 验证联系方式
        logger.info(f"[联系方式验证] 开始验证: {collected_contact}")

        is_valid, error_msg, success_msg = await self.validation_service.validate_contact(
            collected_contact,
            user_profile,
            account_id,
            self.user_service  # 传入共享的 user_service
        )

        if is_valid:
            logger.info(f"[联系方式验证成功]")
            return success_msg or ai_response
        else:
            # 撤销保存
            user_profile = await self.user_service.get_user_profile(account_id)
            user_profile.contact = None
            user_profile.collection_progress['contact'] = False
            await self.user_service.save_user_profile(account_id, user_profile)

            logger.info(f"[联系方式验证失败] 已撤销保存")
            # 如果 error_msg 为空，表示不回复（第3次及以上错误），返回空字符串
            if error_msg == "":
                return ""
            return error_msg

    def _clean_response(self, response: str) -> str:
        """清理回复（移除 XML 标签）"""
        import re
        return re.sub(r'<extract>.*?</extract>', '', response, flags=re.DOTALL).strip()

    async def _update_conversation_state(
        self,
        account_id: str,
        user_message: str,
        clean_response: str,
        raw_response: str
    ) -> None:
        """更新对话状态"""
        # 添加到历史
        await self.dialogue_manager.add_to_history(account_id, 'user', user_message)
        await self.dialogue_manager.add_to_history(account_id, 'assistant', clean_response)

        # 更新最近回复
        await self.dialogue_manager.update_recent_responses(account_id, raw_response)

        # 增加消息计数
        await self.dialogue_manager.increment_message_count(account_id)

    async def _build_chat_response(
        self,
        account_id: str,
        user_profile: UserProfile,
        response: str,
        collection_result: Dict[str, Any],
        dialog_id: Optional[str]
    ) -> Dict[str, Any]:
        """构建聊天响应"""
        # 检查是否拒绝
        is_refusal = RefusalDetector.is_refusing(response)

        # 获取消息计数
        message_count = await self.dialogue_manager.get_message_count(account_id)

        # 构建已收集信息（所有 11 个字段）
        collected_info = {
            "sex": user_profile.sex or "未留",
            "last_name": user_profile.last_name or "未留称呼",
            "age": user_profile.age or "未留",
            "height": user_profile.height or "未留",
            "weight": user_profile.weight or "未留",
            "location": user_profile.location or "未留",
            "education": user_profile.education or "未留",
            "marital_status": user_profile.marital_status or "未留",
            "monthly_income": user_profile.monthly_income or "未留",
            "occupation": user_profile.occupation or "未留",
            "contact": user_profile.contact or "未留"
        }

        return {
            "success": True,
            "response": response,
            "collected_info": collected_info,
            "collection_complete": user_profile.is_collection_complete(),
            "is_refusal": is_refusal,
            "message_count": message_count,
            "dialogId": dialog_id
        }

    def _success_response(self, response: str, dialog_id: Optional[str]) -> Dict[str, Any]:
        """构建成功响应"""
        return {
            "success": True,
            "response": response,
            "dialogId": dialog_id
        }

    def _error_response(self, error: str, dialog_id: Optional[str]) -> Dict[str, Any]:
        """构建错误响应"""
        return {
            "success": False,
            "error": error,
            "dialogId": dialog_id
        }

    # ============ 其他辅助方法 ============

    async def generate_welcome_message(self, user_id: str) -> Dict[str, Any]:
        """生成欢迎消息（已禁用）"""
        # 清除对话历史
        await self.dialogue_manager.clear_conversation(user_id)

        # 不再显示欢迎消息，直接开始对话
        return {
            "success": True,
            "message": "",
            "conversation_reset": True
        }

    async def process_user_feedback(
        self,
        user_id: str,
        message: str,
        rating: int,
        feedback_type: str = "response"
    ) -> Dict[str, Any]:
        """处理用户反馈"""
        logger.info(f"[用户反馈] user={user_id}, rating={rating}, type={feedback_type}")

        # TODO: 存储反馈到数据库
        return {
            "success": True,
            "message": "感谢您的反馈！",
            "feedback_recorded": True
        }

    async def get_user_conversation_history(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """获取对话历史"""
        history = self.user_service.get_conversation_history(user_id, limit, offset)

        return {
            "success": True,
            "history": history,
            "total": len(history),
            "limit": limit,
            "offset": offset
        }

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户资料"""
        profile = await self.user_service.get_user_profile(user_id)

        return {
            "success": True,
            "profile": profile.to_dict()
        }

    async def reset_user_conversation(self, user_id: str) -> Dict[str, Any]:
        """重置用户对话"""
        await self.dialogue_manager.clear_conversation(user_id)

        return {
            "success": True,
            "message": "对话已重置",
            "conversation_reset": True
        }

    # ============ 无意义输入检测 ============

    def _is_nonsense_input(self, text: str) -> bool:
        """
        检测是否是无意义输入（乱码、表情符号堆砌、键盘乱敲等）

        Args:
            text: 用户输入文本

        Returns:
            bool: 是否是无意义输入
        """
        import re
        from src.services.redis_service import redis_service

        text_stripped = text.strip()

        # 跳过纯中文输入（认为是有意义的）
        # 简化检查：如果主要是中文，认为是有意义的
        chinese_chars = re.findall(r'[\u4e00-\u9fa5]', text_stripped)
        if len(chinese_chars) >= len(text_stripped) * 0.5 and len(text_stripped) > 3:
            return False

        # 1. 长度过短（1-2个字符且不是有意义的内容）
        if len(text_stripped) <= 2:
            # 检查是否是中文或英文单词
            if not re.search(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{2,}', text_stripped):
                return True

        # 2. 大量表情符号/特殊字符（超过内容的30%）
        emoji_pattern = re.compile(
            '[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF'
            '\U00002702-\U000027B0\U000024C2-\U0001F251'
            '\u2600-\u26FF\u2700-\u27BF]'
        )
        emoji_count = len(emoji_pattern.findall(text_stripped))
        if emoji_count > 0 and len(text_stripped) > 0:
            emoji_ratio = emoji_count / len(text_stripped)
            if emoji_ratio > 0.3:
                return True

        # 3. 纯数字或数字+符号（且不是手机号、年龄等有意义的数字）
        if re.match(r'^[\d\s\+\-\(\)\*#]{3,}$', text_stripped):
            # 排除手机号格式
            if not re.match(r'^1[3-9]\d{9}$', re.sub(r'\s+', '', text_stripped)):
                return True

        # 4. 键盘乱敲检测 - 优先检测！
        # 检测模式：连续键盘上相邻的字母（如 "rtyui", "asdfg", "qwerty"）
        keyboard_sequences = [
            'qwertyuiop', 'asdfghjkl', 'zxcvbnm',
            '1234567890', '0987654321',
            'qwer', 'asdf', 'zxcv', 'tyui', 'ghjk', 'bnm',
            'rtyu', 'fghj', 'cvbn', 'yuiop', 'hjkl'
        ]
        text_lower = text_stripped.lower()
        for seq in keyboard_sequences:
            if seq in text_lower or seq[::-1] in text_lower:
                return True

        # 5. 字母数字混合乱码 - 新的检测方法！
        # 检测：数字和字母混合但没有形成有意义的内容
        if len(text_stripped) >= 6:
            # 检查是否是字母数字混合
            has_letter = bool(re.search(r'[a-zA-Z]', text_stripped))
            has_digit = bool(re.search(r'\d', text_stripped))

            if has_letter and has_digit:
                # 方法1：检测是否有重复的短模式（2-4字符）
                for pattern_len in range(2, 5):
                    if len(text_stripped) >= pattern_len * 2:
                        patterns = []
                        for i in range(len(text_stripped) - pattern_len + 1):
                            pattern = text_stripped[i:i + pattern_len].lower()
                            patterns.append(pattern)

                        # 检查是否有重复的模式
                        from collections import Counter
                        pattern_counts = Counter(patterns)
                        for pattern, count in pattern_counts.items():
                            if count >= 2 and pattern.isalnum():
                                # 找到重复模式
                                return True

                # 方法2：检测字符分布是否均匀（乱码特征）
                # 如果相邻字符总是频繁切换字母/数字类型
                type_switches = 0
                prev_was_digit = text_stripped[0].isdigit()
                for char in text_stripped[1:]:
                    current_is_digit = char.isdigit()
                    if current_is_digit != prev_was_digit and char.isalnum():
                        type_switches += 1
                    prev_was_digit = current_is_digit

                # 如果类型切换次数超过长度的一半，说明是乱码
                if type_switches > len(text_stripped) * 0.4:
                    return True

        # 6. 字符熵检测 - 唯一字符太少说明大量重复
        if len(text_stripped) >= 8:
            unique_chars = set(text_stripped.lower())
            unique_ratio = len(unique_chars) / len(text_stripped)
            # 如果独特字符少于50%，说明大量重复
            if unique_ratio < 0.5:
                return True

        # 7. 重复字符过多（如 "啊啊啊啊啊啊" 或 "哈哈哈..."）
        if len(text_stripped) > 5:
            # 检查是否有单个字符重复超过4次
            if re.search(r'(.)\1{4,}', text_stripped):
                return True

        # 8. 纯字母乱码检测
        # 检测：纯字母但没有形成有意义的英文单词
        if re.match(r'^[a-zA-Z]{4,}$', text_stripped):
            # 检查是否包含元音字母（英文单词通常有元音）
            has_vowel = bool(re.search(r'[aeiou]', text_stripped.lower()))
            if not has_vowel:
                # 没有元音，很可能是乱码
                return True
            # 检查辅音连续过多（超过4个连续辅音很可能是乱码）
            if re.search(r'[^aeiou\s]{5,}', text_stripped.lower()):
                return True

        # 9. 乱码模式检测：大量随机字符+符号混合
        # 检测连续的特殊字符/数字/符号堆砌
        special_char_pattern = re.compile(r'[^\w\s\u4e00-\u9fa5]{8,}')
        if special_char_pattern.search(text_stripped):
            return True

        return False

    async def _get_nonsense_count(self, user_id: str) -> int:
        """获取用户连续无意义输入次数"""
        from src.services.redis_service import redis_service
        key = f"{self._nonsense_count_prefix}{user_id}"
        count = await redis_service.get(key)
        return int(count) if count else 0

    async def _increment_nonsense_count(self, user_id: str) -> int:
        """增加无意义输入计数"""
        from src.services.redis_service import redis_service
        key = f"{self._nonsense_count_prefix}{user_id}"
        count = await self._get_nonsense_count(user_id) + 1
        await redis_service.set(key, str(count), ttl=3600)  # 1小时过期
        return count

    async def _reset_nonsense_count(self, user_id: str) -> None:
        """重置无意义输入计数"""
        from src.services.redis_service import redis_service
        key = f"{self._nonsense_count_prefix}{user_id}"
        await redis_service.delete(key)

    async def _check_and_handle_nonsense(self, user_input: str, user_id: str, user_profile) -> Optional[str]:
        """
        检测并处理无意义输入

        Args:
            user_input: 用户输入
            user_id: 用户ID
            user_profile: 用户档案

        Returns:
            Optional[str]: 如果需要特殊处理则返回回复，否则返回None
        """
        # 检测是否是无意义输入
        if self._is_nonsense_input(user_input):
            count = await self._increment_nonsense_count(user_id)

            # 第一次：友好提醒
            if count == 1:
                return self._get_first_nonsense_response(user_profile)

            # 第二次：委婉引导
            elif count == 2:
                return self._get_second_nonsense_response(user_profile)

            # 第三次：尝试理解
            elif count == 3:
                return self._get_third_nonsense_response(user_profile)

            # 第四次及以上：自然结束
            else:
                return self._get_closing_response(user_profile)
        else:
            # 正常输入，重置计数器
            await self._reset_nonsense_count(user_id)
            return None

    def _get_first_nonsense_response(self, user_profile) -> str:
        """第一次无意义输入：友好提醒"""
        sex = user_profile.sex if user_profile else None
        call_name = "小哥哥" if sex == "男" else "小姐姐" if sex == "女" else "亲"

        responses = [
            f"嗯...{call_name}是不是不小心输错啦～我看到的内容有点看不懂呢",
            f"{call_name}你是想说什么呢？我刚才看到的消息有点奇怪呢～",
            f"啊呀，{call_name}是不是手机不小心碰到啦～发的内容我没太看明白",
        ]
        import random
        return random.choice(responses)

    def _get_second_nonsense_response(self, user_profile) -> str:
        """第二次无意义输入：委婉引导"""
        sex = user_profile.sex if user_profile else None
        call_name = "小哥哥" if sex == "男" else "小姐姐" if sex == "女" else "亲"

        responses = [
            f"{call_name}要不我们重新聊聊？你方便告诉我怎么称呼你吗？比如叫什么名字呀～",
            f"好啦好啦～{call_name}是不是不太想聊这些呀？那我们先简单点，你是在哪个城市呢？",
            f"嗯呢，{call_name}我们可以先认识一下嘛～你叫什么名字呀，方便告诉我吗？",
        ]
        import random
        return random.choice(responses)

    def _get_third_nonsense_response(self, user_profile) -> str:
        """第三次无意义输入：尝试理解"""
        sex = user_profile.sex if user_profile else None
        call_name = "小哥哥" if sex == "男" else "小姐姐" if sex == "女" else "亲"

        responses = [
            f"感觉{call_name}好像不太想聊呢...要不这样吧，等你想聊的时候再来找我～",
            f"{call_name}是不是在逗我玩呀哈哈～要是真的想脱单的话，我们可以认真聊聊哦～",
            f"嗯呢，可能{call_name}现在不太方便吧～那我就不打扰你啦，有空再聊～",
        ]
        import random
        return random.choice(responses)

    def _get_closing_response(self, user_profile) -> str:
        """第四次及以上：自然结束"""
        sex = user_profile.sex if user_profile else None
        call_name = "小哥哥" if sex == "男" else "小姐姐" if sex == "女" else "亲"

        responses = [
            f"好啦好啦，{call_name}那我先忙去啦～以后真的想脱单的话随时来找我哦，拜拜～",
            f"嗯嗯，感觉{call_name}今天好像不太想聊呢，那我就不打扰啦～祝你早日脱单哦！",
            f"好哒{call_name}，那我们先这样～以后有需要的话随时来找我呀，拜拜～",
        ]
        import random
        return random.choice(responses)

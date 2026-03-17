"""
重构后的聊天服务 - 处理对话并隐晦地收集用户信息

这是一个重构版本，将原来 1113 行的单一服务拆分为多个专职服务：
- ExtractionService: 信息提取
- ValidationService: 数据验证
- DialogueManager: 对话状态管理
- ChatService: 主流程编排
"""

import asyncio
import logging
import random
from typing import Dict, Any, Optional, List

from src.models.personality import PersonalityProfile
from src.models.requests import ChatRequest
from src.models.user_profile import UserProfile
from src.services.ai_service import AIService
from src.services.collection.ask_tracking_service import AskTrackingService
from src.services.data.user_service import UserService
from src.services.data.extraction_service import ExtractionService
from src.services.data.validation_service import ValidationService
from src.services.core.dialogue_manager import DialogueManager
from src.services.refusal_service import RefusalService
from src.services.field_skip_service import FieldSkipService
from src.services.collection.contact_collection_service import ContactCollectionService
from src.services.conversation.conversation_ending_service import ConversationEndingService
from src.services.conversation.expectation_service import ExpectationService
from src.services.conversation.greeting_service import GreetingService
from src.services.conversation.input_fallback_service import InputFallbackService
from src.services.conversation.user_question_service import UserQuestionService
from src.services.collection.profile_collection_policy import ProfileCollectionPolicy
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

    # 核心字段定义（必须收集的字段）
    CORE_FIELDS = ['sex', 'age', 'education', 'occupation', 'location', 'contact']

    # 常见单字姓氏白名单（中国前100大姓）
    COMMON_SURNAMES = frozenset({
        '李', '王', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴',
        '徐', '孙', '胡', '朱', '高', '林', '何', '郭', '马', '罗',
        '梁', '宋', '郑', '谢', '韩', '唐', '冯', '于', '董', '萧',
        '程', '曹', '袁', '邓', '许', '傅', '沈', '曾', '彭', '吕',
        '苏', '卢', '蒋', '蔡', '贾', '丁', '魏', '薛', '叶', '阎',
        '余', '潘', '杜', '戴', '夏', '钟', '汪', '田', '任', '姜',
        '范', '方', '石', '姚', '谭', '廖', '邹', '熊', '金', '陆',
        '郝', '孔', '白', '崔', '康', '毛', '邱', '秦', '江', '史',
        '顾', '侯', '邵', '孟', '龙', '万', '段', '雷', '钱', '汤',
        '尹', '黎', '易', '常', '武', '乔', '贺', '赖', '龚', '文',
        # 常见复姓
        '欧阳', '司马', '上官', '诸葛', '东方', '皇甫', '令狐', '夏侯',
    })

    def __init__(
        self,
        ai_service: AIService,
        user_service: UserService
    ):
        """初始化聊天服务"""
        self.ai_service = ai_service
        self.user_service = user_service

        # 无意义输入计数器键名前缀
        self._nonsense_count_prefix = "nonsense_count:"

        # 确认词（用户回复"好的"但没留联系方式）计数器键名前缀
        self._confirm_count_prefix = "confirm_count:"

        # 初始化专职服务
        self.extraction_service = ExtractionService(user_service)
        self.ask_tracking_service = AskTrackingService(user_service)
        self.validation_service = ValidationService()
        self.dialogue_manager = DialogueManager(user_service)
        self.refusal_service = RefusalService()
        self.field_skip_service = FieldSkipService()
        self.contact_service = ContactCollectionService(user_service)
        self.ending_service = ConversationEndingService()
        self.expectation_service = ExpectationService()
        self.greeting_service = GreetingService()
        self.input_fallback_service = InputFallbackService(
            user_service=user_service,
            nonsense_prefix=self._nonsense_count_prefix,
            confirm_prefix=self._confirm_count_prefix,
        )
        self.user_question_service = UserQuestionService()
        self.collection_policy = ProfileCollectionPolicy()
        self.personality_profile = PersonalityProfile()

        # 临时存储可能的拒绝字段
        self._temp_refused_fields = {}

    async def process_chat_request(self, request: ChatRequest) -> Dict[str, Any]:
        """
        处理聊天请求 - 核心业务逻辑

        Args:
            request: 聊天请求

        Returns:
            Dict[str, Any]: 响应数据
        """
        import time
        start_time = time.time()
        account_id = request.accountId
        logger.info(f"[⏱️ 性能] 开始处理请求: account_id={account_id}")

        try:
            # 1. 获取用户档案
            user_profile = await self.user_service.get_user_profile(account_id)

            # 1.1 信任上游传入的性别，并优先落档，避免首轮重复确认
            if request.sex in ["男", "女"] and not user_profile.sex:
                user_profile.sex = request.sex
                user_profile.collection_progress["sex"] = True
                await self.user_service.save_user_profile(account_id, user_profile)
                logger.info(f"[请求性别同步] account_id={account_id}, sex={request.sex}")

            # 1.5. 如果用户档案为空（全新用户），重置无意义输入计数器
            # 这确保用户数据过期后，重新开始对话时不会受到之前计数的影响
            is_empty = user_profile.is_empty()
            message_count = await self.dialogue_manager.get_message_count(account_id)
            is_new_user_session = is_empty and message_count == 0
            logger.info(
                f"[用户档案检查] account_id={account_id}, is_empty={is_empty}, "
                f"message_count={message_count}, last_name={user_profile.last_name}"
            )
            if is_new_user_session:
                await self.input_fallback_service.reset_nonsense_count(account_id)
                # 重置对话结束状态（新用户重新开始）
                user_profile.conversation_ended = False
                # 注意：不重置 field_ask_count，因为它记录的是当前对话的追问次数
                # 即使档案为空（Redis过期），追问计数也应该保持，因为这是当前对话的上下文
                # 立即保存重置的状态，避免后续异常导致丢失
                await self.user_service.save_user_profile(account_id, user_profile)
                logger.info(f"[全新用户] 已重置无意义输入计数器和对话结束状态: {account_id}")

            # 1.6. 检查对话是否已结束（挽留失败后）
            # 如果已结束，用户再发消息时只返回简短告别，不再收集信息
            if user_profile.conversation_ended:
                logger.info(f"[对话已结束] 用户继续发消息，返回简短告别: {account_id}")
                sex = user_profile.sex
                call_name = "小哥哥" if sex == "男" else "小姐姐" if sex == "女" else "亲"
                # 检查是否已经发送过告别（避免重复）
                last_response = await self.dialogue_manager.get_last_response(account_id) or ""
                if "有需要随时再来找我" in last_response or "下次再聊" in last_response:
                    # 已经发送过告别，返回空响应
                    return await self._build_chat_response(
                        account_id,
                        user_profile,
                        "",
                        {"collected": False, "all_fields": []},
                        request.dialogId
                    )
                # 返回简短告别
                return await self._build_chat_response(
                    account_id,
                    user_profile,
                    f"好的～{call_name}，那先这样啦～有需要随时再来找我哦～拜拜👋",
                    {"collected": False, "all_fields": []},
                    request.dialogId
                )

            # 2. 检查信息是否已收集完成且用户只回复确认词（如"嗯"、"好"）
            # 如果是，直接返回空响应，避免死循环
            # 注意：只有联系方式已收集时才跳过，否则用户可能只是表示同意留电话
            if user_profile.is_collection_complete() and user_profile.contact:
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

            # 2.5. 检测用户回复确认词但没留联系方式的情况
            # 条件：择偶要求已收集 + 联系方式未收集 + 用户回复确认词
            from src.services.data.extraction_service import ExtractionService
            extraction_service = ExtractionService(self.user_service)
            collected_info_summary = extraction_service.get_collected_info_summary(user_profile)
            has_requirement = "要求:" in collected_info_summary
            has_contact = "已留联系" in collected_info_summary

            # 确认词列表
            affirmative_words = ['嗯', '好', '好的', '行', '可以', 'ok', '是的', '对', '是', '恩', '嗯嗯', '好的呢', '好呀']
            user_input = request.question.strip()
            is_affirmative = user_input in affirmative_words

            if has_requirement and not has_contact and is_affirmative:
                # 用户在被问联系方式时只回复确认词，没有提供实际号码
                confirm_count = await self.input_fallback_service.increment_confirm_count(account_id)
                logger.info(f"[确认词检测] 用户第{confirm_count}次回复确认词但没留联系方式: {user_input}")

                # 根据次数返回不同的回复
                confirm_response = self.input_fallback_service.get_confirm_word_response(user_profile, confirm_count)
                if confirm_response is not None:
                    # 注意：空字符串 "" 也是有效响应，表示不回复用户
                    return await self._build_chat_response(
                        account_id,
                        user_profile,
                        confirm_response,  # 可能是空字符串
                        {"collected": False, "all_fields": []},
                        request.dialogId
                    )
            elif has_contact:
                # 联系方式已收集，重置确认词计数器
                await self.input_fallback_service.reset_confirm_count(account_id)

            # 2.6. 用户询问匹配时长时，按业务规则直接回复，不交给 AI 自由发挥
            if self.expectation_service.is_matching_timeline_question(request.question):
                timeline_response = self.expectation_service.get_matching_timeline_response(user_profile)
                logger.info(f"[匹配时长] 命中时长问答，快速通道回复: {timeline_response}")
                return await self._build_chat_response(
                    account_id,
                    user_profile,
                    timeline_response,
                    {"collected": False, "all_fields": []},
                    request.dialogId
                )

            # 3. 更新人设性别
            self.dialogue_manager.update_user_sex(user_profile)

            # 4. 检查输入是否可理解
            if not InputValidator.is_understandable(request.question):
                error_response = "抱歉，我没太理解您的意思，能换个方式说吗？"
                return self._success_response(error_response, request.dialogId)

            # 4.4. 检测用户结束对话意图（"不说了"、"算了"等）
            end_intent_keywords = [
                '不说了', '不聊了', '不想聊', '算了', '算了算了',
                '不填了', '不填', '不写了', '不写', '下次吧',
                '先这样', '不用了', '不用', '不要了', '不要',
                '没兴趣', '没意思', '太麻烦', '太复杂', '太细了',
                '问的太细', '问的太多', '问题太多', '太费事',
                '不想说了', '豆不想说了', '不想填了', '拒绝了', '不再问了',
                '不回答了', '不答了', '不聊', '不回', '不回复',
                '不提供', '不给', '不愿意', '不方便', '不想给'
            ]
            user_input_lower = request.question.strip().lower()
            is_end_intent = any(kw in user_input_lower for kw in end_intent_keywords)

            if is_end_intent:
                # 增加结束意图计数
                user_profile.increment_ask_count('conversation_end_intent')
                end_count = user_profile.get_ask_count('conversation_end_intent')
                logger.info(f"[结束意图检测] 用户说: {request.question}，结束意图计数: {end_count}")
                # 保存用户档案
                await self.user_service.save_user_profile(account_id, user_profile)

            # 4.4.1. 检测分居状态（用户直接说"分居中"、"正在分居"等）
            # 分居状态说明用户还没离婚，不符合服务条件，需要结束对话
            separation_keywords = [
                '分居中', '正在分居', '分居状态', '分居的', '处于分居',
                '已经分居', '目前分居', '现在分居', '还在分居'
            ]
            if any(kw in user_input_lower for kw in separation_keywords):
                user_profile.conversation_ended = True
                user_profile.marital_status = "离异（分居中）"
                await self.user_service.save_user_profile(account_id, user_profile)
                logger.info(f"[分居状态识别] 用户说: {request.question}，设置 conversation_ended=True, marital_status=离异（分居中）")

                # 直接返回结束语，不调用 AI
                end_responses = [
                    "嗯嗯理解～分居中的话暂时还不符合我们的服务条件呢～等手续都办妥了再来找我吧，祝你顺利～",
                    "好的呢～分居状态暂时还没法帮你匹配哦～等一切都处理好了再来，不着急的～如果后续有任何需要和帮助，欢迎随时找我呀～"
                ]
                return await self._build_chat_response(
                    account_id,
                    user_profile,
                    random.choice(end_responses),
                    {"collected": False, "all_fields": []},
                    request.dialogId
                )

            # 4.5. 检测无意义输入（乱码、表情符号堆砌等）
            last_ai_response = await self.dialogue_manager.get_last_response(account_id) or ""
            nonsense_response = await self.input_fallback_service.check_and_handle_nonsense(
                request.question,
                account_id,
                user_profile,
                last_ai_response,
            )
            if nonsense_response:
                # 返回人性化回复
                return await self._build_chat_response(
                    account_id,
                    user_profile,
                    nonsense_response,
                    {},
                    request.dialogId
                )

            # 4.6. 检测打招呼（仅当用户档案为空时使用预设回复）
            # 但如果用户同时表达了拒绝联系方式，则跳过打招呼检测，让拒绝检测处理
            has_contact_refusal = any(kw in request.question for kw in ['不留微信', '不留电话', '不留联系方式', '不给微信', '不给电话'])
            if is_new_user_session and self.greeting_service.is_greeting(request.question) and not has_contact_refusal:
                greeting_response = self.greeting_service.get_greeting_response(request.question)
                # 模拟真人打字时间（1.0-2.0秒），像真人在思考+打字
                await asyncio.sleep(random.uniform(1.0, 2.0))
                logger.info(f"[打招呼检测] 用户打招呼: {request.question}，返回预设回复: {greeting_response}")
                return await self._build_chat_response(
                    account_id,
                    user_profile,
                    greeting_response,
                    {},
                    request.dialogId
                )

            # 5. 检测用户拒绝（包含提前拒绝联系方式）
            await self._handle_refusal_detection(request.question, account_id, user_profile)
            conversation_context = await self.dialogue_manager.get_conversation_context(account_id)
            prioritize_user_question = self.user_question_service.is_priority_question(request.question)
            if prioritize_user_question:
                logger.info(f"[答疑优先] 用户提问命中常见疑问，本轮暂停资料推进: {request.question}")

            # 6. 构建主对话提示词
            main_prompt = self.dialogue_manager.build_main_dialogue_prompt(
                request.question,
                user_profile,
                conversation_context,
                prioritize_user_question=prioritize_user_question,
            )

            # 保存用户档案（因为 build_main_dialogue_prompt 可能递增了询问计数）
            await self.user_service.save_user_profile(account_id, user_profile)

            # 检查信息是否已收集完成（包含"已留联系"标记且包含"要求:"择偶要求）
            from src.services.data.extraction_service import ExtractionService
            extraction_service = ExtractionService(self.user_service)
            collected_info = extraction_service.get_collected_info_summary(user_profile)

            # 只有联系方式和择偶要求都收集了，才算进入收尾阶段
            has_contact = "已留联系" in collected_info
            has_requirement = "要求:" in collected_info

            if has_contact and has_requirement:
                # 用户已提供联系方式和择偶要求，检查是否表示结束
                user_input = request.question.strip()

                # 结束信号词（用户表示没有其他要求了）
                ending_signals = ['没有了', '没啦', '没了', '就这些', '就这点', '暂时没有', '暂时没',
                                  '先这样', '差不多', '应该没了', '应该没', '没有了呢', '没啥了',
                                  '其他没了', '其他没', '暂时就这些', '目前没', '目前没有']
                is_ending = any(signal in user_input for signal in ending_signals)

                # 检查是否是问候语
                greeting_words = ['在吗', '在不在', '你好', '您好', '嗨', '哈喽', 'hello', 'hi']
                is_greeting = any(word in user_input for word in greeting_words)

                if is_greeting:
                    # 用户打招呼，自然回复
                    logger.info(f"[信息收集完成] 用户打招呼，返回自然回复")
                    natural_response = f"在的呀～{user_profile.get_greeting()}，你要是还有想了解的可以直接跟我说"
                    return await self._build_chat_response(
                        account_id,
                        user_profile,
                        natural_response,
                        {"collected": False, "all_fields": []},
                        request.dialogId
                    )
                elif is_ending:
                    # 用户表示没有其他要求了，返回收尾话术
                    logger.info(f"[信息收集完成] 用户表示结束: {user_input}")
                    # 检查是否已经发送过收尾话术
                    last_response = await self.dialogue_manager.get_last_response(account_id)
                    timeline_text = self.expectation_service.get_closing_timeline_text(user_profile)
                    closing_message = f"好的呀～那你等好消息啦，祝你早日脱单🥰 {timeline_text}，牵线同事联系前会提前约时间，不会打扰你的～"

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
                        return await self._build_chat_response(
                            account_id,
                            user_profile,
                            closing_message,
                            {"collected": False, "all_fields": []},
                            request.dialogId
                        )
                # else: 用户可能还有其他要求要补充，继续让 AI 对话

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

            # 收尾服务命中预设结束话术时，直接返回，不再继续联系方式验证或覆盖回复。
            if collection_result.get("success") and "response" in collection_result:
                final_response = collection_result.get("response", "")
                await self._update_conversation_state(
                    account_id,
                    request.question,
                    final_response,
                    ai_response,
                    track_asked_fields=False,
                )
                user_profile = await self.user_service.get_user_profile(account_id)
                total_duration = time.time() - start_time
                logger.info(f"[⏱️ 性能] 请求处理完成: account_id={account_id}, 总耗时={total_duration:.3f}秒")
                return await self._build_chat_response(
                    account_id,
                    user_profile,
                    final_response,
                    {"collected": False, "all_fields": []},
                    request.dialogId,
                )

            # 9.5. 如果用户提供了择偶要求，重置确认词计数器
            # 因为接下来AI会问联系方式，这是新一轮的"问联系方式"流程
            for field_info in collection_result.get('all_fields', []):
                if field_info.get('field') == 'partner_requirement':
                    await self.input_fallback_service.reset_confirm_count(account_id)
                    logger.info(f"[确认词计数器] 用户提供了择偶要求，重置确认词计数器")
                    break

            # 重新获取 user_profile 以获得最新数据
            user_profile = await self.user_service.get_user_profile(account_id)

            # 10. 处理联系方式验证
            enhanced_response = await self._handle_contact_validation(
                account_id,
                user_profile,
                collection_result,
                ai_response,
                request.question
            )

            # 10.5. 香港用户：收集电话后询问微信
            # 检查是否是香港用户且刚收集了电话但还没收集微信
            is_hong_user = self._is_hong_user(user_profile.location)
            contact_just_collected = any(
                f.get('field') == 'contact' for f in collection_result.get('all_fields', [])
            )
            if is_hong_user and contact_just_collected and not user_profile.wechat:
                # 香港用户刚提供了电话，需要询问微信
                call_name = user_profile.get_greeting()
                enhanced_response = f"好的呀～{call_name}的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面联系会更顺手一点～"
                logger.info(f"[香港用户] 电话收集完成，生成询问微信的回复")

            # 11. 清理回复（移除 XML 标签）
            # 如果 enhanced_response 为 None，表示使用原 AI 回复
            response_to_clean = enhanced_response if enhanced_response is not None else ai_response
            final_response = self._clean_response(response_to_clean)

            # 11.5. 保存 field_ask_count 快照（在 _track_ai_asked_fields 增加计数之前）
            # 用于"已跳过"显示逻辑：使用"增加前"的值，这样用户还有机会回答当前问题
            field_ask_count_before = dict(user_profile.field_ask_count) if user_profile.field_ask_count else {}

            # 12. 更新对话状态
            await self._update_conversation_state(
                account_id,
                request.question,
                final_response,
                ai_response,
                track_asked_fields=not prioritize_user_question,
            )

            # 13. 重新获取最新的用户档案（包含刚更新的 field_ask_count）
            user_profile = await self.user_service.get_user_profile(account_id)

            # 14. 构建响应
            total_duration = time.time() - start_time
            logger.info(f"[⏱️ 性能] 请求处理完成: account_id={account_id}, 总耗时={total_duration:.3f}秒")
            return await self._build_chat_response(
                account_id,
                user_profile,
                final_response,
                collection_result,
                request.dialogId,
                field_ask_count_before  # 传递"增加前"的快照，用于正确显示"已跳过"时机
            )

        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(f"[⏱️ 性能] 请求处理异常: account_id={account_id}, 总耗时={total_duration:.3f}秒, 错误={e}")
            from src.core.error_handler import handle_error
            error_response = handle_error(e, context="chat", user_id=account_id)
            return self._error_response(error_response.get('error', '处理失败'), request.dialogId)

    async def _handle_refusal_detection(self, user_message: str, account_id: str, user_profile: UserProfile) -> None:
        """
        处理拒绝检测，包括提前拒绝联系方式

        使用 ContactCollectionService 统一处理联系方式相关的拒绝检测
        """
        # === 入口日志（INFO级别，便于调试）===
        logger.info(f"[拒绝检测-开始] account_id={account_id}, phone_ask_count={user_profile.phone_ask_count}, wechat_ask_count={user_profile.wechat_ask_count}, rejected_phone={user_profile.rejected_phone}, rejected_wechat={user_profile.rejected_wechat}")

        last_response = await self.dialogue_manager.get_last_response(account_id)

        # 检测用户是否拒绝（通用拒绝检测）
        is_refusing = self.refusal_service.is_refusing(user_message)
        if is_refusing and last_response:
            refused_fields = self.extraction_service.infer_refused_fields(last_response)
            self._temp_refused_fields[account_id] = refused_fields

        # === 使用 ContactCollectionService 检测联系方式拒绝 ===
        refusal_result = self.contact_service.detect_refusal(
            message=user_message,
            profile=user_profile,
            last_response=last_response
        )

        if refusal_result:
            contact_type_cn = "电话" if refusal_result.contact_type == 'phone' else "微信"

            if refusal_result.is_final:
                logger.info(f"[拒绝检测] 用户最终拒绝{contact_type_cn}")
            else:
                logger.info(f"[拒绝检测] 用户拒绝{contact_type_cn}，询问次数: {refusal_result.ask_count_after}")

            # 保存更新后的用户档案
            await self.user_service.save_user_profile(account_id, user_profile)

        # === 检查是否应该结束对话 ===
        if self.contact_service.should_end_conversation(user_profile):
            if not user_profile.conversation_ended:
                user_profile.conversation_ended = True
                user_profile.spam_user = True
                user_profile.contact = self.contact_service.get_status_display(user_profile)
                await self.user_service.save_user_profile(account_id, user_profile)
                logger.info(f"[无效用户] 用户拒绝了微信和电话，标记为无效用户并结束对话")

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
        import time
        ai_start_time = time.time()
        logger.info(f"[⏱️ 性能] 开始调用AI: account_id={account_id}")

        try:
            # 使用简单的系统提示词确保用中文回复
            response = await self.ai_service.generate_response(
                message=prompt,
                system_prompt="你是一个说中文的AI助手，请用中文回复用户。",
                timeout=120  # 120秒超时（豆包API响应较慢）
            )
            ai_end_time = time.time()
            ai_duration = ai_end_time - ai_start_time
            logger.info(f"[⏱️ 性能] AI调用完成: account_id={account_id}, 耗时={ai_duration:.3f}秒")
            return response
        except AIServiceException as e:
            # AI 服务失败时返回空响应，不暴露 AI 身份
            logger.error(f"[AI调用] 失败: {e}，返回空响应")
            return ""
        except Exception as e:
            logger.error(f"[AI调用] 未预期的错误: {e}，返回空响应")
            return ""

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

        # === 使用统一的收尾服务检测收尾场景 ===
        # 调用 check_and_get_ending，参数顺序：user_message, profile, collection_result
        # 返回结构：{'scenario': str, 'use_ai': bool, 'description': str, 'response': str, ...}
        # 内部已调用 update_profile_for_ending，无需单独调用
        ending_info = self.ending_service.check_and_get_ending(
            user_message,        # 第1个参数：用户消息
            user_profile,        # 第2个参数：用户档案
            collection_result    # 第3个参数：收集结果
        )

        if ending_info:
            scenario = ending_info['scenario']
            use_ai = ending_info['use_ai']
            logger.info(f"[收尾检测] 检测到收尾场景: {scenario}, AI生成: {use_ai}")

            # 保存已更新的用户状态（check_and_get_ending 内部已更新 profile）
            await self.user_service.save_user_profile(account_id, user_profile)

            # AI 生成场景：不返回预设话术，由外部流程处理
            if use_ai:
                # 将 extra_instructions 传递给外部流程（通过 collection_result）
                collection_result['ending_info'] = ending_info
                logger.info(f"[收尾检测] AI生成场景，传递给外部处理: {scenario}")
            else:
                # 预设话术场景：直接返回
                response = ending_info.get('response', '')
                is_silent = response == ""  # 空模板表示静默场景

                result = {
                    "success": True,
                    "response": response,
                    "dialogId": "",
                    "collected_info": {},
                    "collected": False
                }
                if is_silent:
                    result["silent"] = True

                logger.info(f"[收尾检测] 返回预设话术，场景: {scenario}, 静默: {is_silent}")
                return result

        # === 以下为保留的旧逻辑，逐步迁移到收尾服务 ===
        # 检测离异手续状态（已办妥的情况，不是收尾场景）
        divorce_complete_keywords = [
            '办妥了', '办好了', '已办妥', '已办好', '办完了', '已经办妥', '已经办好',
            '手续办了', '手续好了', '办妥', '办好', '离了', '办了'
        ]
        if user_profile.marital_status == '离异' or '离异' in str(user_profile.marital_status):
            if any(kw in user_message for kw in divorce_complete_keywords):
                # 用户确认手续已办妥，更新婚况状态
                user_profile.marital_status = "离异（手续已办妥）"
                user_profile.divorce_confirmed = True
                await self.user_service.save_user_profile(account_id, user_profile)
                logger.info(f"[离异手续已办妥] 用户说: {user_message}，更新 marital_status=离异（手续已办妥）")

        # 处理拒绝字段
        if account_id in self._temp_refused_fields:
            refused_fields = self._temp_refused_fields[account_id]
            collected_fields = [f['field'] for f in collection_result.get('all_fields', [])]

            # 标记被拒绝但未被提取的字段
            for field in refused_fields:
                if field not in collected_fields:
                    await self.user_service.skip_user_profile_field(account_id, field)
                    logger.info(f"[拒绝标记] 用户拒绝字段: {field}")

            del self._temp_refused_fields[account_id]

        return collection_result

    async def _handle_contact_validation(
        self,
        account_id: str,
        user_profile: UserProfile,
        collection_result: Dict[str, Any],
        ai_response: str,
        user_message: str = "",
    ) -> str:
        """处理联系方式验证"""
        # 检查是否收集到联系方式（电话或微信）
        collected_contact = None
        collected_phone = None
        collected_wechat = None
        for field_info in collection_result.get('all_fields', []):
            if field_info.get('field') == 'contact':
                collected_contact = field_info.get('value')
            elif field_info.get('field') == 'phone':
                collected_phone = field_info.get('value')
            elif field_info.get('field') == 'wechat':
                collected_wechat = field_info.get('value')

        contact_value = collected_phone or collected_contact
        invalid_contact_attempt = collection_result.get("invalid_contact_attempt") or self._extract_contact_candidate_from_message(user_message)
        logger.info(f"[联系方式检查] collected_contact={contact_value}, collected_wechat={collected_wechat}, all_fields={collection_result.get('all_fields', [])}")

        # 如果收集到微信，设置 wechat_collected 标志
        if collected_wechat:
            user_profile.wechat_collected = True
            # 非香港用户：微信也可以作为联系方式
            is_hong_user = self._is_hong_user(user_profile.location)
            if not is_hong_user:
                user_profile.collection_progress['contact'] = True
            await self.user_service.save_user_profile(account_id, user_profile)
            logger.info(f"[微信收集] 设置 wechat_collected=True, 香港用户={is_hong_user}")

        # 如果没有收集到任何联系方式，检查是否所有字段都已完成
        if contact_value is None and collected_wechat is None:
            if invalid_contact_attempt:
                logger.info(f"[联系方式检查] 检测到疑似无效联系方式输入: {invalid_contact_attempt}")
                is_valid, error_msg, _ = await self.validation_service.validate_contact(
                    invalid_contact_attempt,
                    user_profile,
                    account_id,
                    self.user_service
                )
                if not is_valid:
                    return error_msg or ""

            # 检查核心字段是否全部收集
            profile_ready_for_service = self.collection_policy.has_serviceable_profile(user_profile)

            contact_collected = (
                user_profile.collection_progress.get('contact', False) or
                (user_profile.wechat and user_profile.wechat_collected)
            )

            # 如果资料已足够服务，检查联系方式收集流程是否也结束
            if profile_ready_for_service and contact_collected:
                # 检查联系方式收集流程是否还有下一步动作
                from src.services.collection.contact_collection_service import NextAction
                next_action = self.contact_service.get_next_action(user_profile)
                if next_action not in [NextAction.NONE, NextAction.END_CONVERSATION]:
                    # 联系方式收集流程还没结束，返回 AI 原回复（包含争取话术）
                    logger.info(f"[收尾检查] 联系方式收集流程未结束，next_action={next_action.value}")
                    return ai_response

                logger.info(f"[收尾检查] 所有字段已完成，返回 AI 收尾回复")
                # 移除固定话术，让 AI 根据上下文生成自然的收尾回复
                # AI 会根据 prompts.py 中的收尾指令区分场景：
                # - 用户提供了联系方式 → "那你等好消息啦，祝你早日脱单"
                # - 用户拒绝联系方式 → "有需要随时找我呀"
                return ai_response

            # 否则返回原回复
            return ai_response

        # 用户提供了联系方式（电话或微信），重置确认词计数器
        await self.input_fallback_service.reset_confirm_count(account_id)
        logger.info(f"[联系方式验证] 用户提供了联系方式，重置确认词计数器")

        # 如果只收集到微信（没有电话），尝试争取电话
        if contact_value is None and collected_wechat:
            has_phone_already = bool(user_profile.phone_collected and user_profile.phone)
            # 微信已在上面的代码中处理（设置 wechat_collected=True）
            # 检查是否可以收尾
            contact_collected = (
                user_profile.collection_progress.get('contact', False) or
                (user_profile.wechat and user_profile.wechat_collected)
            )
            profile_ready_for_service = self.collection_policy.has_serviceable_profile(user_profile)

            # === 新增：争取电话号码 ===
            # 如果用户没有提供电话，且还没争取过电话，则再问一次电话
            # 注意：不在这里设置 phone_ask_count，让 _handle_refusal 在用户拒绝时递增
            # 这样用户第一次拒绝后还有一次争取机会
            if not has_phone_already and not user_profile.rejected_phone and user_profile.phone_ask_count < 1:
                logger.info(f"[微信收集] 尝试争取电话号码")
                call_name = user_profile.get_greeting()
                return "好的呀～我先记下了。要是你电话方便的话，也可以留一个，后面联系会更及时些～"

            # 已经争取过电话，用户还是只留微信，检查是否可以收尾
            if profile_ready_for_service and contact_collected:
                logger.info(f"[微信收集] 核心字段全部收集完成，准备收尾")
                await self._mark_remaining_fields_as_skipped(account_id, user_profile)
                return "好的呀，我先记下啦，后面有合适的人选会尽快联系你～"
            else:
                # === 资料未达到可服务阈值，继续收集重要字段 ===
                decision = self.collection_policy.decide(
                    user_profile,
                    allow_contact_target=False,
                )
                logger.info(f"[微信收集] 资料未完成，继续推进字段: {decision.main_target}")

                call_name = user_profile.get_greeting()
                field_names = {
                    'sex': '是小哥哥还是小姐姐呀',
                    'age': '今年多大呢',
                    'education': '学历是什么呀',
                    'occupation': '做什么工作的呀',
                    'location': '在哪个城市呢',
                    'marital_status': '现在是单身状态在认真了解吗'
                }
                first_missing = decision.main_target
                if first_missing and first_missing in field_names:
                    question = field_names[first_missing]
                    return f"好的呀，我先记下啦。顺带问你一下，{question}"
                else:
                    return "好的呀，我先记下啦。你也可以再简单说说自己的情况～"

        # 验证电话号码
        logger.info(f"[联系方式验证] 开始验证电话: {contact_value}")

        is_valid, error_msg, success_msg = await self.validation_service.validate_contact(
            contact_value,
            user_profile,
            account_id,
            self.user_service  # 传入共享的 user_service
        )

        if is_valid:
            logger.info(f"[联系方式验证成功]")

            # === 设置电话号码和 phone_collected ===
            user_profile.phone = contact_value
            user_profile.phone_collected = True
            user_profile.contact = user_profile.get_contact_status()
            logger.info(f"[联系方式验证] 设置 phone={contact_value}, phone_collected=True")

            # === 重置电话询问计数（用户已提供电话，无需再争取）===
            user_profile.phone_ask_count = 0
            await self.user_service.save_user_profile(account_id, user_profile)
            logger.info(f"[联系方式验证] 重置 phone_ask_count = 0 并保存")

            # === 检查是否需要询问微信 ===
            next_action = self.contact_service.get_next_action(user_profile)
            logger.info(f"[联系方式验证] 下一步动作: {next_action}")

            if next_action.value == "ask_wechat":
                # 需要询问微信
                logger.info(f"[联系方式验证] 电话已收集，需要询问微信，wechat_ask_count={user_profile.wechat_ask_count}")
                # 询问次数在用户明确拒绝时由拒绝检测统一递增，这里只发起询问，不提前计数。

                call_name = user_profile.get_greeting()
                wechat_ask_response = f"好的呀～{call_name}的电话我记下啦😊 要是你微信方便的话，也可以留一个，后面沟通会更顺手一点～"

                # === 重要：将微信询问回复添加到 recent_responses ===
                # 这样后续拒绝检测时 get_last_response 才能正确获取到这条微信询问
                await self.dialogue_manager.update_recent_responses(account_id, wechat_ask_response)
                logger.info(f"[联系方式验证] 已将微信询问添加到 recent_responses")

                return wechat_ask_response

            # === 核心字段完成度检查 ===
            # 检查核心字段是否全部收集（联系方式：电话或微信有一个即可）
            contact_collected = (
                user_profile.collection_progress.get('contact', False) or
                (user_profile.wechat and user_profile.wechat_collected)
            )

            # 核心字段检查（排除contact，因为上面单独检查了
            profile_ready_for_service = self.collection_policy.has_serviceable_profile(user_profile)

            if profile_ready_for_service and contact_collected:
                # === 核心字段全部收集完成，收尾 ===
                logger.info(f"[核心字段] 全部收集完成，准备收尾")

                # 标记剩余未收集字段为"跳过"
                await self._mark_remaining_fields_as_skipped(account_id, user_profile)

                # 返回收尾回复
                return success_msg or ai_response
            else:
                # === 资料未达到可服务阈值，继续收集重要字段 ===
                decision = self.collection_policy.decide(
                    user_profile,
                    allow_contact_target=False,
                )
                logger.info(f"[核心字段] 资料未完成，继续推进字段: {decision.main_target}")

                call_name = user_profile.get_greeting()
                field_names = {
                    'sex': '是小哥哥还是小姐姐呀',
                    'age': '今年多大呢',
                    'education': '学历是什么呀',
                    'occupation': '做什么工作的呀',
                    'location': '在哪个城市呢',
                    'marital_status': '现在是单身状态在认真了解吗'
                }
                first_missing = decision.main_target
                if first_missing and first_missing in field_names:
                    question = field_names[first_missing]
                    return f"好的呀～{call_name}的电话我先记下啦。顺带问你一下，{question}"
                else:
                    return f"好的呀～{call_name}的电话我先记下啦。你也可以再简单说说自己的情况～"
        else:
            # 撤销保存 - 直接修改传入的 user_profile 对象
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

    def _extract_contact_candidate_from_message(self, user_message: str) -> Optional[str]:
        """从用户原始消息中提取疑似联系方式，用于无效联系方式兜底校验。"""
        if not user_message:
            return None

        import re

        marker_pattern = re.compile(
            r'(?:电话|手机|手机号|号码|微信|vx|wx|weixin)[^\da-zA-Z_/-]*([a-zA-Z0-9_-]{4,20})',
            re.IGNORECASE,
        )
        matched = marker_pattern.search(user_message)
        if matched:
            return matched.group(1)

        return None

    async def _update_conversation_state(
        self,
        account_id: str,
        user_message: str,
        clean_response: str,
        raw_response: str,
        track_asked_fields: bool = True,
    ) -> None:
        """更新对话状态"""
        # 添加到历史
        await self.dialogue_manager.add_to_history(account_id, 'user', user_message)
        await self.dialogue_manager.add_to_history(account_id, 'assistant', clean_response)

        # 更新最近回复（使用清理后的回复，而不是原始回复）
        # 注意：_handle_contact_validation 可能已经添加了微信询问回复，这里不要覆盖
        # 检查 recent_responses 最后一条是否已经是当前回复
        last_response = await self.dialogue_manager.get_last_response(account_id)
        if last_response != clean_response:
            await self.dialogue_manager.update_recent_responses(account_id, clean_response)

        # 增加消息计数
        await self.dialogue_manager.increment_message_count(account_id)

        # 智能追问机制：追踪AI询问的字段
        if track_asked_fields:
            await self.ask_tracking_service.track_ai_asked_fields(account_id, clean_response)

    async def _build_chat_response(
        self,
        account_id: str,
        user_profile: UserProfile,
        response: str,
        collection_result: Dict[str, Any],
        dialog_id: Optional[str],
        field_ask_count_before: Dict[str, int] = None
    ) -> Dict[str, Any]:
        """构建聊天响应

        Args:
            field_ask_count_before: AI询问前的字段计数快照，用于正确显示"已跳过"时机
                                   （使用"增加前"的值，这样用户还有机会回答当前问题）
        """
        # 检查是否拒绝
        is_refusal = RefusalDetector.is_refusing(response)

        # 获取消息计数
        message_count = await self.dialogue_manager.get_message_count(account_id)

        # 使用"增加前"的快照来判断"已跳过"显示（如果没有快照，使用当前值）
        ask_count_snapshot = field_ask_count_before if field_ask_count_before is not None else {}

        # 辅助函数：获取字段显示值（区分"未留"和"已跳过"）
        def get_field_display(field_name: str, value, default: str = "未留") -> str:
            if value:
                return str(value)
            # 检查是否被跳过（问了2次及以上未回答）
            # 使用"增加前"的快照值，这样用户还有机会回答当前问题
            ask_count = ask_count_snapshot.get(field_name, 0)
            if ask_count >= 2:
                return f"已跳过({ask_count}次未答)"
            return default

        # 构建联系方式显示值（简化版逻辑）
        def get_contact_display() -> str:
            parts = []
            # 微信号部分
            if user_profile.wechat:
                parts.append(f"微信:{user_profile.wechat}")
            elif user_profile.rejected_wechat:
                parts.append("不愿留微信")
            elif user_profile.wechat_ask_count >= 1 and not user_profile.rejected_wechat:
                parts.append("微信争取中")
            # 电话部分
            if user_profile.phone:
                parts.append(f"电话:{user_profile.phone}")
            elif user_profile.rejected_phone:
                parts.append("不愿留电话")
            elif user_profile.phone_ask_count >= 1 and not user_profile.rejected_phone:
                parts.append("电话争取中")
            # 组合结果
            if parts:
                return ", ".join(parts)
            return "未留"

        # 构建已收集信息（12 个字段，联系方式合并显示）
        collected_info = {
            "sex": get_field_display("sex", user_profile.sex),
            "last_name": get_field_display("last_name", user_profile.last_name, "未留称呼"),
            "age": get_field_display("age", user_profile.age),
            "height": get_field_display("height", user_profile.height),
            "weight": get_field_display("weight", user_profile.weight),
            "location": get_field_display("location", user_profile.location),
            "education": get_field_display("education", user_profile.education),
            "marital_status": get_field_display("marital_status", user_profile.marital_status),
            "monthly_income": get_field_display("monthly_income", user_profile.monthly_income),
            "occupation": get_field_display("occupation", user_profile.occupation),
            "contact": get_contact_display(),
            "partner_requirement": get_field_display("partner_requirement", user_profile.partner_requirement)
        }

        # 返回响应
        return {
            "success": True,
            "response": response,
            "dialogId": dialog_id,
            "collected_info": collected_info,
            "collected": collection_result.get("collected", False) if collection_result else False,
            "field": collection_result.get("field") if collection_result else None,
            "value": collection_result.get("value") if collection_result else None
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
        # 检测是否是429配额错误，如果是则返回空响应（不显示错误消息）
        if '429' in error or 'SetLimitExceeded' in error or 'TooManyRequests' in error:
            return {
                "success": True,
                "response": "",
                "dialogId": dialog_id,
                "silent": True
            }

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
        """重置用户对话（包括清除用户资料）"""
        await self.dialogue_manager.clear_conversation(user_id)

        # 清除用户资料（重置为全新用户状态）
        await self.user_service.delete_user_profile(user_id)

        return {
            "success": True,
            "message": "对话已重置",
            "conversation_reset": True
        }

    # ============ 打招呼检测 ============

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
        import logging
        from src.services.data.redis_service import redis_service

        logger = logging.getLogger(__name__)
        text_stripped = text.strip()

        # 跳过纯中文输入（认为是有意义的）
        # 简化检查：如果主要是中文，认为是有意义的
        chinese_chars = re.findall(r'[\u4e00-\u9fa5]', text_stripped)
        if len(chinese_chars) >= len(text_stripped) * 0.5 and len(text_stripped) > 3:
            logger.info(f"[无意义检测] 通过中文检查: {text_stripped}")
            return False

        # 1. 长度过短（1-2个字符且不是有意义的内容）
        if len(text_stripped) <= 2:
            # 如果是常见姓氏，认为是有意义的
            if text_stripped in self.COMMON_SURNAMES:
                logger.info(f"[无意义检测] 判定为有意义（常见姓氏）: {text_stripped}")
                return False

            # 检查是否是中文或英文单词
            pattern = r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{2,}'
            match = re.search(pattern, text_stripped)
            logger.info(f"[无意义检测] 短输入 '{text_stripped}' (len={len(text_stripped)}) 正则匹配: {match}")
            if not match:
                # 额外检查：数字+单位格式（如"5万"、"3k"、"20k"）是有意义的
                income_pattern = r'^\d+[万千百kKwW]?$|^\d+[万千百kKwW]$'
                if re.match(income_pattern, text_stripped):
                    logger.info(f"[无意义检测] 判定为有意义（收入格式）: {text_stripped}")
                    return False
                logger.info(f"[无意义检测] 判定为无意义: {text_stripped}")
                return True
            else:
                logger.info(f"[无意义检测] 判定为有意义: {text_stripped}，返回 False")
                return False  # 明确返回 False！

        # 2. 大量表情符号/特殊字符（超过内容的30%）
        # 注意：使用范围时必须精确，避免包含中文字符
        emoji_pattern = re.compile(
            '[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF'
            '\U00002702-\U000027B0\U000024C2-\U000027BF'
            '\u2600-\u26FF]'
        )
        emoji_count = len(emoji_pattern.findall(text_stripped))
        if emoji_count > 0 and len(text_stripped) > 0:
            emoji_ratio = emoji_count / len(text_stripped)
            if emoji_ratio > 0.3:
                logger.info(f"[无意义检测] 表情符号过多: {text_stripped}")
                return True

        # 3. 纯数字或数字+符号（且不是手机号、年龄等有意义的数字）
        if re.match(r'^[\d\s\+\-\(\)\*#]{3,}$', text_stripped):
            # 排除手机号格式（中国大陆11位或香港8位）
            clean_num = re.sub(r'\s+', '', text_stripped)
            if re.match(r'^1[3-9]\d{9}$', clean_num) or re.match(r'^[5-9]\d{7}$', clean_num):
                logger.info(f"[无意义检测] 手机号格式，判定有意义: {text_stripped}")
                return False

            # 排除常见的有意义数字格式
            pure_num = re.sub(r'\s+', '', text_stripped)
            try:
                num = int(pure_num)
                # 身高范围：100-250（cm）
                if 100 <= num <= 250:
                    logger.info(f"[无意义检测] 可能是身高，判定有意义: {text_stripped}")
                    return False
                # 体重范围：30-300（斤/kg）
                if 30 <= num <= 300:
                    logger.info(f"[无意义检测] 可能是体重，判定有意义: {text_stripped}")
                    return False
                # 年龄范围：18-80
                if 18 <= num <= 80:
                    logger.info(f"[无意义检测] 可能是年龄，判定有意义: {text_stripped}")
                    return False
                # 收入：常见范围
                if num >= 1000:
                    logger.info(f"[无意义检测] 可能是收入等大数字，判定有意义: {text_stripped}")
                    return False
            except ValueError:
                pass

            # 其他纯数字才判定为无意义
            logger.info(f"[无意义检测] 纯数字但无法识别含义: {text_stripped}")
            return True

        # 4. 键盘乱敲检测 - 只检测字母键盘乱敲
        # 检测模式：连续键盘上相邻的字母（如 "rtyui", "asdfg", "qwerty"）
        # 不检测数字序列，因为手机号等正常数字可能包含连续数字
        keyboard_sequences = [
            'qwertyuiop', 'asdfghjkl', 'zxcvbnm',
            'qwer', 'asdf', 'zxcv', 'tyui', 'ghjk', 'bnm',
            'rtyu', 'fghj', 'cvbn', 'yuiop', 'hjkl'
        ]
        text_lower = text_stripped.lower()
        for seq in keyboard_sequences:
            if seq in text_lower or seq[::-1] in text_lower:
                logger.info(f"[无意义检测] 键盘乱敲: {text_stripped}")
                return True

        # 5. 字母数字混合乱码 - 新的检测方法！
        # 检测：数字和字母混合但没有形成有意义的内容
        if len(text_stripped) >= 6:
            # 检查是否是字母数字混合
            has_letter = bool(re.search(r'[a-zA-Z]', text_stripped))
            has_digit = bool(re.search(r'\d', text_stripped))
            logger.info(f"[无意义检测] 字母数字检查: has_letter={has_letter}, has_digit={has_digit}")

            if has_letter and has_digit:
                # 排除微信号格式：以字母开头，6-20字符，可含字母数字下划线减号
                wechat_pattern = r'^[a-zA-Z][a-zA-Z0-9_-]{5,19}$'
                if re.match(wechat_pattern, text_stripped):
                    logger.info(f"[无意义检测] 判定为有意义（微信号格式）: {text_stripped}")
                    return False
                # 新增：从输入中提取可能的微信号（不要求整个输入匹配）
                potential_wechat = re.search(r'[a-zA-Z][a-zA-Z0-9_-]{5,19}', text_stripped)
                if potential_wechat:
                    logger.info(f"[无意义检测] 包含可能的微信号格式: {potential_wechat.group()}")
                    return False
                # 方法1：检测是否有重复的短模式（2-4字符）
                # 排除常见的数字组合（如年龄、体重等）
                # 只有当重复模式占比很高时才认为是乱码
                for pattern_len in range(2, 5):
                    if len(text_stripped) >= pattern_len * 3:  # 提高阈值：至少出现3次
                        patterns = []
                        for i in range(len(text_stripped) - pattern_len + 1):
                            pattern = text_stripped[i:i + pattern_len].lower()
                            patterns.append(pattern)

                        # 检查是否有重复的模式
                        from collections import Counter
                        pattern_counts = Counter(patterns)
                        for pattern, count in pattern_counts.items():
                            # 重复至少3次且是字母数字混合才认为是乱码
                            if count >= 3 and pattern.isalnum() and any(c.isalpha() for c in pattern) and any(c.isdigit() for c in pattern):
                                logger.info(f"[无意义检测] 重复模式(字母数字混合): {pattern} count={count}")
                                return True

                # 方法2：检测字符分布是否均匀（乱码特征）
                # 但先排除常见的有意义格式（包含单位的数字）
                meaningful_patterns = [
                    r'\d+kg',      # 体重：90kg
                    r'\d+cm',      # 身高：180cm
                    r'\d+岁',      # 年龄：28岁
                    r'\d+年',      # 年份：90年
                    r'wx[a-zA-Z0-9]+',  # 微信号
                    r'\d+\.?\d*[wW万千百]',  # 收入格式（支持小数）：1.4w、1.4万、3w、3万
                ]
                for pattern in meaningful_patterns:
                    if re.search(pattern, text_stripped.lower()):
                        logger.info(f"[无意义检测] 包含有意义格式({pattern})，跳过乱码检测: {text_stripped}")
                        return False

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
                    logger.info(f"[无意义检测] 类型切换过多: type_switches={type_switches}, len={len(text_stripped)}")
                    return True

        # 6. 字符熵检测 - 唯一字符太少说明大量重复
        # 但排除手机号（手机号可能有重复数字）
        if len(text_stripped) >= 8:
            # 先检查是否是手机号格式（中国大陆11位或香港8位）
            if re.match(r'^1[3-9]\d{9}$', text_stripped) or re.match(r'^[5-9]\d{7}$', text_stripped):
                return False  # 手机号是有意义的
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

    async def _mark_remaining_fields_as_skipped(self, account_id: str, user_profile: UserProfile) -> None:
        """
        收尾时，标记所有未收集字段为"跳过"

        这样用户下次进入时，不会重复询问这些字段
        """
        all_fields = [
            'sex', 'age', 'location', 'education', 'occupation',
            'marital_status', 'contact', 'monthly_income',
            'partner_requirement', 'last_name', 'height', 'weight'
        ]

        skipped_count = 0
        for field in all_fields:
            if not user_profile.collection_progress.get(field, False):
                user_profile.skipped_fields[field] = True
                skipped_count += 1

        if skipped_count > 0:
            await self.user_service.save_user_profile(account_id, user_profile)
            logger.info(f"[收尾] 已标记 {skipped_count} 个未收集字段为跳过")

    def _is_hong_user(self, location: Optional[str]) -> bool:
        """判断用户是否是香港用户"""
        if not location:
            return False
        location_lower = location.lower()
        return '香港' in location_lower or 'hk' in location_lower

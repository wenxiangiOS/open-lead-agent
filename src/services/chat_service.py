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

    # 预设的打招呼回复列表（按类型分组）
    GREETING_RESPONSES: Dict[str, List[str]] = {
        'formal': [  # 正式打招呼（你好、您好）
            "你好呀～有什么可以帮您的吗？",
            "你好呀～是帮自己找对象吗？",
        ],
        'casual': [  # 随意打招呼（哈喽、嗨）
            "哈喽～你也在深圳吗？",
            "哈喽～有什么可以帮您的吗？",
        ],
        'time_morning': [  # 早上问候
            "早上好呀～有什么可以帮您的吗？",
            "早安～是帮自己找对象吗？",
        ],
        'time_afternoon': [  # 下午问候
            "下午好呀～有什么可以帮您的吗？",
            "下午好～是帮自己找对象吗？",
        ],
        'time_evening': [  # 晚上问候
            "晚上好呀～有什么可以帮您的吗？",
            "晚上好～是帮自己找对象吗？",
        ],
    }

    # 幽默纠正回复（用户说错时间时使用）
    TIME_CORRECTION_RESPONSES: Dict[str, List[str]] = {
        'morning_to_afternoon': [  # 用户说早上好，但实际是下午
            "哈哈，现在已经是下午啦～下午好呀～是帮自己找对象吗？",
            "哎呀，现在下午了呢～下午好呀～有什么可以帮您的吗？",
        ],
        'morning_to_evening': [  # 用户说早上好，但实际是晚上
            "哈哈，现在已经是晚上啦～晚上好呀～是帮自己找对象吗？",
            "哎呀，现在晚上了呢～晚上好呀～有什么可以帮您的吗？",
        ],
        'afternoon_to_morning': [  # 用户说下午好，但实际是上午
            "哈哈，现在还是上午呢～早上好呀～是帮自己找对象吗？",
            "哎呀，现在是上午哦～早上好呀～有什么可以帮您的吗？",
        ],
        'afternoon_to_evening': [  # 用户说下午好，但实际是晚上
            "哈哈，现在已经是晚上啦～晚上好呀～是帮自己找对象吗？",
            "哎呀，现在晚上了呢～晚上好呀～有什么可以帮您的吗？",
        ],
    }

    # 打招呼关键词（按类型分组）
    GREETING_KEYWORDS: Dict[str, List[str]] = {
        'formal': ['你好', '您好'],
        'casual': ['哈喽', '哈罗', '嗨', 'hello', 'hi', 'Hi', '在吗', '在不在'],
        'time_morning': ['早上好', '早安', '上午好'],
        'time_afternoon': ['下午好'],
        'time_evening': ['晚上好'],
    }

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

        # 确认词（用户回复"好的"但没留联系方式）计数器键名前缀
        self._confirm_count_prefix = "confirm_count:"

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

            # 1.5. 如果用户档案为空（全新用户），重置无意义输入计数器
            # 这确保用户数据过期后，重新开始对话时不会受到之前计数的影响
            is_empty = user_profile.is_empty()
            logger.info(f"[用户档案检查] account_id={account_id}, is_empty={is_empty}, last_name={user_profile.last_name}")
            if is_empty:
                await self._reset_nonsense_count(account_id)
                # 重置追问计数器（新用户不应该有之前的追问记录）
                user_profile.field_ask_count = {}
                # 重置对话结束状态（新用户重新开始）
                user_profile.conversation_ended = False
                # 立即保存重置的状态，避免后续异常导致丢失
                await self.user_service.save_user_profile(account_id, user_profile)
                logger.info(f"[全新用户] 已重置无意义输入计数器、追问计数器和对话结束状态: {account_id}")

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
            from src.services.extraction_service import ExtractionService
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
                confirm_count = await self._increment_confirm_count(account_id)
                logger.info(f"[确认词检测] 用户第{confirm_count}次回复确认词但没留联系方式: {user_input}")

                # 根据次数返回不同的回复
                confirm_response = self._get_confirm_word_response(user_profile, confirm_count)
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
                await self._reset_confirm_count(account_id)

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

            # 4.6. 检测打招呼（仅当用户档案为空时使用预设回复）
            if is_empty and self._is_greeting(request.question):
                greeting_response = self._get_greeting_response(request.question)
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

            # 6. 构建主对话提示词
            main_prompt = self.dialogue_manager.build_main_dialogue_prompt(
                request.question,
                user_profile,
                conversation_context
            )

            # 检查信息是否已收集完成（包含"已留联系"标记且包含"要求:"择偶要求）
            from src.services.extraction_service import ExtractionService
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
                    natural_response = "在的呀～小哥哥，有什么可以帮你的吗呀"
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

            # 9.5. 如果用户提供了择偶要求，重置确认词计数器
            # 因为接下来AI会问联系方式，这是新一轮的"问联系方式"流程
            for field_info in collection_result.get('all_fields', []):
                if field_info.get('field') == 'partner_requirement':
                    await self._reset_confirm_count(account_id)
                    logger.info(f"[确认词计数器] 用户提供了择偶要求，重置确认词计数器")
                    break

            # 重新获取 user_profile 以获得最新数据
            user_profile = await self.user_service.get_user_profile(account_id)

            # 10. 处理联系方式验证
            enhanced_response = await self._handle_contact_validation(
                account_id,
                user_profile,
                collection_result,
                ai_response
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
                enhanced_response = f"好的呀～{call_name}的电话我记下啦😊 对了，方便再留个微信号吗？这样后续联系更方便呢～"
                logger.info(f"[香港用户] 电话收集完成，生成询问微信的回复")

            # 11. 清理回复（移除 XML 标签）
            # 如果 enhanced_response 为 None，表示使用原 AI 回复
            response_to_clean = enhanced_response if enhanced_response is not None else ai_response
            final_response = self._clean_response(response_to_clean)

            # 12. 更新对话状态
            await self._update_conversation_state(
                account_id,
                request.question,
                final_response,
                ai_response
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
                request.dialogId
            )

        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(f"[⏱️ 性能] 请求处理异常: account_id={account_id}, 总耗时={total_duration:.3f}秒, 错误={e}")
            from src.core.error_handler import handle_error
            error_response = handle_error(e, context="chat", user_id=account_id)
            return self._error_response(error_response.get('error', '处理失败'), request.dialogId)

    async def _handle_refusal_detection(self, user_message: str, account_id: str, user_profile: UserProfile) -> None:
        """处理拒绝检测，包括提前拒绝联系方式"""
        last_response = await self.dialogue_manager.get_last_response(account_id)

        # 检测用户是否拒绝
        is_refusing = self.refusal_service.is_refusing(user_message)
        if is_refusing and last_response:
            refused_fields = self.extraction_service.infer_refused_fields(last_response)
            self._temp_refused_fields[account_id] = refused_fields

        # === 提前拒绝联系方式的检测（场景1） ===
        # 用户在还没到问联系方式阶段时，主动说不留微信或电话
        # 这里必须在构建提示词之前执行，以便提示词能包含争取指令
        user_message_lower = user_message.lower()

        # 通用拒绝词（用于上下文感知检测）
        general_refuse_keywords = ['不留', '不给', '不想留', '不方便', '不要', '不行', '不可以', '没']

        # 显式拒绝关键词
        wechat_refuse_keywords = ['不留微信', '不给微信', '不想留微信', '不想要微信', '没微信', '不用微信']
        phone_refuse_keywords = ['不留电话', '不给电话', '不想留电话', '不留手机', '不给手机', '不想留手机']

        # 判断是否是显式拒绝
        is_explicit_wechat_refuse = any(kw in user_message_lower for kw in wechat_refuse_keywords)
        is_explicit_phone_refuse = any(kw in user_message_lower for kw in phone_refuse_keywords)

        # 只有在还没收集到联系方式时才处理
        if not user_profile.collection_progress.get('contact', False):
            # 调试日志：打印当前状态
            # 合并日志
            logger.debug(f"[拒绝检测] 消息='{user_message[:20]}...', 显式拒(微信={is_explicit_wechat_refuse},电话={is_explicit_phone_refuse}), 争取过(微信={user_profile.wechat_persuasion_attempted},电话={user_profile.phone_persuasion_attempted}), 已拒(微信={user_profile.rejected_wechat},电话={user_profile.rejected_phone})")

            # === 显式拒绝微信（用户明确说"不留微信"等）===
            # 显式拒绝检测优先执行，因为它更明确
            if is_explicit_wechat_refuse:
                if user_profile.wechat_persuasion_attempted:
                    # 已经尝试争取过，用户还是拒绝，标记为最终拒绝
                    user_profile.rejected_wechat = True
                    await self.user_service.save_user_profile(account_id, user_profile)
                    logger.info(f"[显式拒绝微信] 用户再次拒绝，标记为最终拒绝: {user_message}")
                else:
                    # 第一次拒绝，标记为已尝试争取（AI会尝试说服用户）
                    user_profile.wechat_persuasion_attempted = True
                    await self.user_service.save_user_profile(account_id, user_profile)
                    logger.info(f"[显式拒绝微信] 用户首次拒绝，标记为已尝试争取: {user_message}")

            # === 显式拒绝电话（用户明确说"不留电话"等）===
            if is_explicit_phone_refuse:
                if user_profile.phone_persuasion_attempted:
                    # 已经尝试争取过，用户还是拒绝，标记为最终拒绝
                    user_profile.rejected_phone = True
                    await self.user_service.save_user_profile(account_id, user_profile)
                    logger.info(f"[显式拒绝电话] 用户再次拒绝，标记为最终拒绝: {user_message}")
                else:
                    # 第一次拒绝，标记为已尝试争取（AI会尝试说服用户）
                    user_profile.phone_persuasion_attempted = True
                    await self.user_service.save_user_profile(account_id, user_profile)
                    logger.info(f"[显式拒绝电话] 用户首次拒绝，标记为已尝试争取: {user_message}")

            # === 上下文感知检测：用户说通用拒绝词 + 上一轮AI提到微信/电话 ===
            # 只有当用户没有使用显式拒绝关键词时，才使用上下文检测
            # 注意：这个检测在显式拒绝检测之后执行，确保显式拒绝已经设置了 persuasion_attempted 标志
            if last_response and any(kw in user_message_lower for kw in general_refuse_keywords):
                last_response_lower = last_response.lower()

                # 检测是否在争取微信后用户拒绝（上一轮AI回复包含"微信"）
                # 条件：用户没有使用显式拒绝微信关键词 + 已经尝试争取微信 + 还没有最终拒绝微信
                if not is_explicit_wechat_refuse:
                    if user_profile.wechat_persuasion_attempted and not user_profile.rejected_wechat:
                        if '微信' in last_response_lower:
                            user_profile.rejected_wechat = True
                            await self.user_service.save_user_profile(account_id, user_profile)
                            logger.info(f"[上下文拒绝] 用户在争取微信后说'{user_message}'，标记为最终拒绝微信")

                # 检测是否在争取电话后用户拒绝（上一轮AI回复包含"电话"）
                # 条件：用户没有使用显式拒绝电话关键词 + 已经尝试争取电话 + 还没有最终拒绝电话
                if not is_explicit_phone_refuse:
                    if user_profile.phone_persuasion_attempted and not user_profile.rejected_phone:
                        if '电话' in last_response_lower:
                            user_profile.rejected_phone = True
                            await self.user_service.save_user_profile(account_id, user_profile)
                            logger.info(f"[上下文拒绝] 用户在争取电话后说'{user_message}'，标记为最终拒绝电话")

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

        # === 年龄限制检查 ===
        # 如果用户年龄低于24岁，直接返回拒绝话术
        if collection_result.get("under_limit"):
            logger.info(f"[年龄限制] 用户年龄 {collection_result.get('value')} 岁，不符合服务条件")
            user_profile.conversation_ended = True
            await self.user_service.save_user_profile(account_id, user_profile)
            # 返回温和拒绝话术
            return {
                "success": True,
                "response": "哇你才这个年纪呀😊 我们的服务面向24岁以上的单身人士哦～等你再长大一点，变得更成熟了再来找我吧！现在好好读书/工作，未来一定会遇到更合适的人的～",
                "dialogId": request.dialogId,
                "collected_info": {},
                "collected": False
            }

        # === LGBT 用户检测 ===
        # 检测用户是否表明是同性恋/百合
        lgbt_keywords = [
            '同性恋', 'gay', '拉拉', 'les', 'lesbian', '百合', '女同',
            '我喜欢女生', '我喜欢男的', '喜欢同性', '我是les', 'les群体',
            '我是gay', 'gay群体', '同志', '同性行为'
        ]
        user_message_lower = user_message.lower()
        for keyword in lgbt_keywords:
            if keyword.lower() in user_message_lower:
                logger.info(f"[LGBT检测] 用户表明: {keyword}")
                user_profile.lgbt_user = True
                user_profile.conversation_ended = True
                await self.user_service.save_user_profile(account_id, user_profile)
                # 返回温和引导话术
                return {
                    "success": True,
                    "response": "谢谢你的坦诚呀😊 我们这边是做异性相亲服务的，可能不太适合你的需求呢～建议你可以去看看一些专门的交友平台，希望你能找到属于你的幸福！祝你好运～",
                    "dialogId": request.dialogId,
                    "collected_info": {},
                    "collected": False
                }

        # === 已婚用户检测 ===
        married_keywords = [
            '我结婚了', '我已经结婚了', '我有老公', '我有老婆', '我有丈夫', '我有妻子',
            '我已婚', '已婚了', '结婚了的', '家里有老婆', '家里有老公',
            '我有爱人', '我有对象', '我不是单身', '我有伴了'
        ]
        for keyword in married_keywords:
            if keyword in user_message:
                logger.info(f"[已婚检测] 用户表明已婚: {keyword}")
                user_profile.already_married = True
                user_profile.conversation_ended = True
                await self.user_service.save_user_profile(account_id, user_profile)
                return {
                    "success": True,
                    "response": "哎呀～原来你已经结婚了呀😊 那我们这边可能帮不了你了呢～我们只服务单身人士哦，祝你婚姻幸福！",
                    "dialogId": request.dialogId,
                    "collected_info": {},
                    "collected": False
                }

        # === 代相亲检测 ===
        proxy_keywords = [
            '帮朋友', '帮我家', '帮我朋友', '帮我亲戚', '帮亲戚', '帮同事',
            '替朋友', '替我家', '替我朋友', '代替朋友', '帮别人问',
            '给我朋友问', '给我朋友打听', '帮我问问', '帮人问', '替人问',
            '我朋友想找', '我亲戚想找', '我同事想找', '帮我弟', '帮我妹',
            '帮我哥', '帮我姐', '帮儿子', '帮女儿', '帮孩子'
        ]
        for keyword in proxy_keywords:
            if keyword in user_message:
                logger.info(f"[代相亲检测] 用户表明代问: {keyword}")
                user_profile.proxy_user = True
                user_profile.conversation_ended = True
                await self.user_service.save_user_profile(account_id, user_profile)
                return {
                    "success": True,
                    "response": "好的呀～不过建议让你的朋友/家人直接来和我聊会更好呢😊 这样我能更准确地了解TA的需求，帮TA找到更合适的人选～",
                    "dialogId": request.dialogId,
                    "collected_info": {},
                    "collected": False
                }

        # === 骚扰/广告检测 ===
        spam_keywords = [
            '加微信', '加我微信', '加个微信', '加我v', '加我V',
            '互推', '推广', '广告', '合作', '商务合作',
            '代理', '兼职', '赚钱', '月入', '日赚',
            '优惠', '折扣', '特价', '促销',
            '刷单', '刷好评', '刷评论',
            '贷款', '借钱', '放贷', '网贷',
            '代开发票', '办证', '刻章',
        ]
        for keyword in spam_keywords:
            if keyword in user_message:
                logger.info(f"[骚扰/广告检测] 检测到可疑内容: {keyword}")
                user_profile.spam_user = True
                user_profile.conversation_ended = True
                await self.user_service.save_user_profile(account_id, user_profile)
                return {
                    "success": True,
                    "response": "",
                    "dialogId": request.dialogId,
                    "collected_info": {},
                    "collected": False,
                    "silent": True  # 静默处理，不回复
                }

        # === 虚假信息检测 ===
        # 检测明显不合理的信息
        fake_info_patterns = [
            ('age', [999, 1000, 123, 111, 222, 333, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),  # 明显假的年龄
            ('height', [300, 400, 500, 50, 30, 20, 10]),  # 明显假的身高
        ]
        # 如果刚收集到的数据在虚假信息列表中
        for field, fake_values in fake_info_patterns:
            collected_value = collection_result.get('value') if collection_result.get('field') == field else None
            if collected_value is not None:
                try:
                    # 尝试转换为数字
                    num_value = int(str(collected_value).replace('岁', '').replace('cm', '').replace('CM', '').strip())
                    if num_value in fake_values:
                        logger.info(f"[虚假信息检测] 检测到虚假{field}: {num_value}")
                        user_profile.conversation_ended = True
                        await self.user_service.save_user_profile(account_id, user_profile)
                        return {
                            "success": True,
                            "response": "哈哈，这个信息有点意思😊 不过我们还是要认真对待相亲这件事的～如果你是真心想找对象，请告诉我真实的信息哦！",
                            "dialogId": request.dialogId,
                            "collected_info": {},
                            "collected": False
                        }
                except (ValueError, AttributeError):
                    pass

        # 检测离异手续状态
        # 注意：必须先检测"未办妥"的情况，再检测"已办妥"的情况
        # 因为"还没办好"包含"办好"，如果先检测"办好"会误判

        # 1. 手续未办妥的情况（优先检测）
        divorce_incomplete_keywords = [
            '还没办好', '还没办妥', '还没办', '正在办', '办理中',
            '正在办理', '手续没办', '还没离', '办手续中', '分居中', '正在分居'
        ]
        if user_profile.marital_status == '离异' or '离异' in str(user_profile.marital_status):
            if any(kw in user_message for kw in divorce_incomplete_keywords):
                # 手续未办妥，设置对话结束
                user_profile.marital_status = "离异（手续未办妥）"
                user_profile.conversation_ended = True
                await self.user_service.save_user_profile(account_id, user_profile)
                logger.info(f"[离异手续未办妥] 用户说: {user_message}，设置 conversation_ended=True, marital_status=离异（手续未办妥）")
            else:
                # 2. 手续已办妥的情况（只有在不包含未办妥关键词时才检测）
                divorce_complete_keywords = [
                    '办妥了', '办好了', '已办妥', '已办好', '办完了', '已经办妥', '已经办好',
                    '手续办了', '手续好了', '办妥', '办好', '离了', '办了'
                ]
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
        ai_response: str
    ) -> str:
        """处理联系方式验证"""
        # 检查是否收集到联系方式（电话或微信）
        collected_contact = None
        collected_wechat = None
        for field_info in collection_result.get('all_fields', []):
            if field_info.get('field') == 'contact':
                collected_contact = field_info.get('value')
            elif field_info.get('field') == 'wechat':
                collected_wechat = field_info.get('value')

        logger.info(f"[联系方式检查] collected_contact={collected_contact}, collected_wechat={collected_wechat}, all_fields={collection_result.get('all_fields', [])}")

        # 如果收集到微信，设置 wechat_collected 标志
        if collected_wechat:
            user_profile.wechat_collected = True
            # 非香港用户：微信也可以作为联系方式
            is_hong_user = self._is_hong_user(user_profile.location)
            if not is_hong_user:
                user_profile.collection_progress['contact'] = True
            await self.user_service.save_user_profile(account_id, user_profile)
            logger.info(f"[微信收集] 设置 wechat_collected=True, 香港用户={is_hong_user}")

        # 如果没有收集到任何联系方式，返回原回复
        if collected_contact is None and collected_wechat is None:
            return ai_response

        # 用户提供了联系方式（电话或微信），重置确认词计数器
        await self._reset_confirm_count(account_id)
        logger.info(f"[联系方式验证] 用户提供了联系方式，重置确认词计数器")

        # 如果只收集到微信（没有电话），尝试争取电话
        if collected_contact is None and collected_wechat:
            # 微信已在上面的代码中处理（设置 wechat_collected=True）
            # 检查是否可以收尾
            contact_collected = (
                user_profile.collection_progress.get('contact', False) or
                (user_profile.wechat and user_profile.wechat_collected)
            )
            core_fields_to_check = ['sex', 'age', 'education', 'occupation', 'location']
            all_core_collected = all([
                user_profile.collection_progress.get(field, False)
                for field in core_fields_to_check
            ])

            # === 新增：争取电话号码 ===
            # 如果用户没有提供电话，且还没争取过电话，则再问一次电话
            if not user_profile.phone_persuasion_attempted:
                # 标记已争取过电话
                user_profile.phone_persuasion_attempted = True
                await self.user_service.save_user_profile(account_id, user_profile)
                logger.info(f"[微信收集] 尝试争取电话号码")
                call_name = user_profile.get_greeting()
                return f"好的呀～微信我记下啦😊 对啦，方便再留个电话号码吗？电话联系会更方便及时呢～"

            # 已经争取过电话，用户还是只留微信，继续收尾流程
            if all_core_collected and contact_collected:
                logger.info(f"[微信收集] 核心字段全部收集完成，准备收尾")
                await self._mark_remaining_fields_as_skipped(account_id, user_profile)
                return ai_response
            return ai_response

        # 验证电话号码
        logger.info(f"[联系方式验证] 开始验证电话: {collected_contact}")

        is_valid, error_msg, success_msg = await self.validation_service.validate_contact(
            collected_contact,
            user_profile,
            account_id,
            self.user_service  # 传入共享的 user_service
        )

        if is_valid:
            logger.info(f"[联系方式验证成功]")

            # === 核心字段完成度检查 ===
            # 检查核心字段是否全部收集（联系方式：电话或微信有一个即可）
            contact_collected = (
                user_profile.collection_progress.get('contact', False) or
                (user_profile.wechat and user_profile.wechat_collected)
            )

            # 核心字段检查（排除contact，因为上面单独检查了
            core_fields_to_check = ['sex', 'age', 'education', 'occupation', 'location']
            all_core_collected = all([
                user_profile.collection_progress.get(field, False)
                for field in core_fields_to_check
            ])

            if all_core_collected and contact_collected:
                # === 核心字段全部收集完成，收尾 ===
                logger.info(f"[核心字段] 全部收集完成，准备收尾")

                # 标记剩余未收集字段为"跳过"
                await self._mark_remaining_fields_as_skipped(account_id, user_profile)

                # 返回收尾回复
                return success_msg or ai_response
            else:
                # === 核心字段未全部收集，不收尾 ===
                missing_fields = [f for f in core_fields_to_check
                               if not user_profile.collection_progress.get(f, False)]
                logger.info(f"[核心字段] 还有 {len(missing_fields)} 个未收集: {missing_fields}，继续收集")
                return None  # 返回 None，让调用方使用原 AI 回复
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

        # 智能追问机制：追踪AI询问的字段
        await self._track_ai_asked_fields(account_id, clean_response)

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

        # 辅助函数：获取字段显示值（区分"未留"和"已跳过"）
        def get_field_display(field_name: str, value, default: str = "未留") -> str:
            if value:
                return str(value)
            # 检查是否被跳过（问了2次及以上未回答）
            # 安全检查：确保 field_ask_count 不是 None
            ask_count_dict = user_profile.field_ask_count if user_profile.field_ask_count is not None else {}
            ask_count = ask_count_dict.get(field_name, 0)
            if ask_count >= 2:
                return f"已跳过({ask_count}次未答)"
            return default

        # 构建联系方式显示值（合并电话和微信）
        def get_contact_display() -> str:
            phone = user_profile.contact
            wechat = user_profile.wechat
            if phone and wechat:
                return f"{phone}/{wechat}"
            elif phone:
                return str(phone)
            elif wechat:
                return str(wechat)
            else:
                # 两者都没有，检查是否跳过
                ask_count_dict = user_profile.field_ask_count if user_profile.field_ask_count is not None else {}
                # 检查 contact 或 wechat 是否被跳过
                contact_ask_count = ask_count_dict.get("contact", 0)
                wechat_ask_count = ask_count_dict.get("wechat", 0)
                if contact_ask_count >= 2 or wechat_ask_count >= 2:
                    return f"已跳过({max(contact_ask_count, wechat_ask_count)}次未答)"
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

    def _detect_greeting_type(self, text: str) -> Optional[str]:
        """
        检测打招呼的类型

        Args:
            text: 用户输入文本

        Returns:
            Optional[str]: 打招呼类型（'formal', 'casual', 'time_morning', 'time_afternoon', 'time_evening'）
                          如果不是打招呼则返回 None
        """
        text_stripped = text.strip().lower()

        # 如果输入太长（超过10个字符），不认为是简单打招呼
        if len(text_stripped) > 10:
            return None

        # 按优先级检测（时间问候 > 正式问候 > 随意问候）
        for greeting_type in ['time_morning', 'time_afternoon', 'time_evening', 'formal', 'casual']:
            keywords = self.GREETING_KEYWORDS.get(greeting_type, [])
            for keyword in keywords:
                if keyword.lower() in text_stripped:
                    return greeting_type

        return None

    def _is_greeting(self, text: str) -> bool:
        """
        检测用户是否只是在打招呼

        Args:
            text: 用户输入文本

        Returns:
            bool: 是否是打招呼
        """
        return self._detect_greeting_type(text) is not None

    def _get_current_time_period(self) -> str:
        """
        获取当前时间段

        Returns:
            str: 时间段（'morning', 'afternoon', 'evening'）
        """
        from datetime import datetime
        hour = datetime.now().hour

        if 5 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 18:
            return 'afternoon'
        else:
            return 'evening'

    def _get_greeting_response(self, text: str) -> str:
        """
        获取预设的打招呼回复（根据用户输入类型匹配，支持时间纠正）

        Args:
            text: 用户输入文本

        Returns:
            str: 打招呼回复
        """
        greeting_type = self._detect_greeting_type(text)
        current_period = self._get_current_time_period()

        # 如果用户说的是时间问候，检查是否需要纠正
        if greeting_type and greeting_type.startswith('time_'):
            user_period = greeting_type.replace('time_', '')  # morning/afternoon/evening

            # 如果用户说的时间与实际时间不符，使用幽默纠正
            if user_period != current_period:
                correction_key = f"{user_period}_to_{current_period}"
                if correction_key in self.TIME_CORRECTION_RESPONSES:
                    responses = self.TIME_CORRECTION_RESPONSES[correction_key]
                    logger.info(f"[时间纠正] 用户说{user_period}，实际是{current_period}，使用幽默纠正")
                    return random.choice(responses)

        # 正常匹配或非时间问候
        if greeting_type and greeting_type in self.GREETING_RESPONSES:
            responses = self.GREETING_RESPONSES[greeting_type]
            return random.choice(responses)

        # 默认返回正式问候
        return random.choice(self.GREETING_RESPONSES['formal'])

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
        from src.services.redis_service import redis_service

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

    async def _get_confirm_count(self, user_id: str) -> int:
        """获取用户连续回复确认词的次数（针对联系方式询问）"""
        from src.services.redis_service import redis_service
        key = f"{self._confirm_count_prefix}{user_id}"
        count = await redis_service.get(key)
        return int(count) if count else 0

    async def _increment_confirm_count(self, user_id: str) -> int:
        """增加确认词回复计数"""
        from src.services.redis_service import redis_service
        key = f"{self._confirm_count_prefix}{user_id}"
        count = await self._get_confirm_count(user_id) + 1
        await redis_service.set(key, str(count), ttl=3600)  # 1小时过期
        return count

    async def _reset_confirm_count(self, user_id: str) -> None:
        """重置确认词回复计数"""
        from src.services.redis_service import redis_service
        key = f"{self._confirm_count_prefix}{user_id}"
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
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[_check_and_handle_nonsense] 开始检查: input={user_input}")

        # 检测是否是无意义输入
        is_nonsense = self._is_nonsense_input(user_input)
        logger.info(f"[_check_and_handle_nonsense] is_nonsense={is_nonsense}")

        if is_nonsense:
            count = await self._increment_nonsense_count(user_id)

            # ========== 挽留失败检测（用户在挽留阶段说"嗯"等简短确认) ==========
            # 判断条件：
            # 1. 有结束意图计数 >= 1（处于挽留阶段)
            # 2. 用户输入是简短确认词（"嗯", "好的", "哦" 等)
            # 3. 上一轮AI在挽留或接受结束（包含"慢慢来"等关键词)
            end_intent_count = user_profile.get_ask_count('conversation_end_intent')
            if end_intent_count >= 1:
                last_ai_response = await self.dialogue_manager.get_last_response(user_id) or ""
                # 挽留关键词（上一轮AI回复中包含这些词）
                retention_keywords = [
                    '随时可以', '随时', '想聊', '想聊了就聊', '什么时候都可以',
                    '先这样', '下次再聊', '拜拜', '没关系', '不打扰',
                    '慢慢来', '别急着', '不着急', '有什么不方便', '有什么顾虑',
                    '怎么了', '可以和我说', '告诉我', '可以慢慢'
                ]
                # 判断上一轮AI是否在挽留/接受结束
                if last_ai_response and any(kw in last_ai_response for kw in retention_keywords):
                    # 检测到用户接受结束
                    logger.info(f"[挽留失败检测] 用户接受结束，输入: {user_input}, 上一轮AI: {last_ai_response[:50]}...")

                    # 标记对话已结束（避免后续重复告别）
                    user_profile.conversation_ended = True
                    await self.user_service.save_user_profile(user_id, user_profile)

                    # 重置无意义计数器（避免影响后续对话)
                    await self._reset_nonsense_count(user_id)

                    # 返回简短告别
                    sex = user_profile.sex if user_profile else None
                    call_name = "小哥哥" if sex == "男" else "小姐姐" if sex == "女" else "亲"
                    responses = [
                        f"好的～{call_name}，那先这样啦～有需要随时再来找我哦～拜拜👋",
                        f"嗯嗯，好的～{call_name}，那我们下次再聊～拜拜啦👋",
                    ]
                    import random
                    return random.choice(responses)

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

        # 根据已收集的信息，问未收集的内容
        has_name = user_profile and user_profile.last_name
        has_location = user_profile and user_profile.location

        if has_name and not has_location:
            # 已有称呼但没有地区
            responses = [
                f"好啦好啦～{call_name}是不是不太想聊这些呀？那我们先简单点，你是在哪个城市呢？",
                f"没关系呀～{call_name}方便说下你在哪个城市吗？",
            ]
        elif has_name:
            # 已有称呼，问其他信息
            responses = [
                f"好啦好啦～{call_name}是不是不太想聊这些呀？没关系，我们慢慢来～",
                f"没关系呀～{call_name}我们换个话题聊聊？",
            ]
        else:
            # 没有称呼，可以问称呼
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

    async def _mark_remaining_fields_as_skipped(self, account_id: str, user_profile: UserProfile) -> None:
        """
        收尾时，标记所有未收集字段为"跳过"

        这样用户下次进入时，不会重复询问这些字段
        """
        all_fields = [
            'sex', 'last_name', 'age', 'height', 'weight',
            'location', 'education', 'marital_status', 'monthly_income',
            'occupation', 'contact', 'partner_requirement'
        ]

        skipped_count = 0
        for field in all_fields:
            if not user_profile.collection_progress.get(field, False):
                user_profile.skipped_fields[field] = True
                skipped_count += 1

        if skipped_count > 0:
            await self.user_service.save_user_profile(account_id, user_profile)
            logger.info(f"[收尾] 已标记 {skipped_count} 个未收集字段为跳过")

    async def _track_ai_asked_fields(self, account_id: str, ai_response: str) -> None:
        """
        追踪AI询问的字段（智能追问机制）

        分析AI回复，检测AI询问了哪个字段，然后增加该字段的追问计数

        Args:
            account_id: 用户ID
            ai_response: AI回复内容
        """
        from src.config.settings import get_field_keywords

        # 从配置获取字段关键词映射
        field_keywords = get_field_keywords()

        # 检测AI是否在问择偶要求（上下文检测）
        # 如果AI在问择偶要求，则不追踪基本信息字段（身高、年龄、学历等）
        partner_requirement_context_keywords = [
            '找什么样的', '有什么要求', '择偶要求', '找什么类型',
            '喜欢什么样的', '对...有要求', '要求对方', '对方的要求',
            '想找', '希望找', '要求是', '有什么择偶'
        ]
        is_asking_partner_requirement = any(kw in ai_response for kw in partner_requirement_context_keywords)

        # 在择偶要求上下文中，这些字段不应该被追踪（因为是在问对方的要求，不是用户自己的信息）
        partner_requirement_fields = {'height', 'age', 'education', 'location', 'monthly_income', 'occupation'}

        # 检测AI询问了哪个字段
        asked_fields = []
        ai_response_lower = ai_response.lower()

        for field, keywords in field_keywords.items():
            # 如果在问择偶要求，跳过基本信息字段
            if is_asking_partner_requirement and field in partner_requirement_fields:
                continue
            # 跳过 partner_requirement 字段的追踪（它有自己的逻辑）
            if field == 'partner_requirement':
                continue

            for keyword in keywords:
                if keyword in ai_response_lower or keyword in ai_response:
                    asked_fields.append(field)
                    break

        if not asked_fields:
            return

        # 获取用户档案
        user_profile = await self.user_service.get_user_profile(account_id)

        # 只追踪未收集的字段
        for field in asked_fields:
            is_collected = user_profile.collection_progress.get(field, False)
            is_skipped = field in user_profile.skipped_fields

            if not is_collected and not is_skipped:
                # 增加追问计数
                user_profile.increment_ask_count(field)
                logger.info(f"[智能追问] AI询问了字段 {field}，当前追问次数: {user_profile.get_ask_count(field)}")

        # 保存用户档案
        await self.user_service.save_user_profile(account_id, user_profile)

    def _get_confirm_word_response(self, user_profile, confirm_count: int) -> Optional[str]:
        """
        根据用户连续回复确认词的次数返回对应的回复

        Args:
            user_profile: 用户档案
            confirm_count: 连续回复确认词的次数

        Returns:
            Optional[str]: 回复内容，如果返回None则继续正常AI对话
        """
        sex = user_profile.sex if user_profile else None
        call_name = "小哥哥" if sex == "男" else "小姐姐" if sex == "女" else "亲"

        import random

        if confirm_count == 1:
            # 第一次：解释电话用途 + 询问号码
            responses = [
                f"好的呢～电话只是用于系统登记哈，牵线的小伙伴才能对接到你，我们是不能私下去牵线的～那{call_name}电话号码是多少呀？",
                f"嗯嗯～这个电话是用于系统登记的，这样牵线的小伙伴才能联系到你呢～{call_name}方便发一下电话号码吗？",
                f"好哒～电话号码是用于系统登记哈，我们这边不能私下去牵线的，需要通过系统来对接～{call_name}发一下你的电话号码给我哈～",
            ]
            return random.choice(responses)

        elif confirm_count == 2:
            # 第二次：询问微信
            responses = [
                f"好的～那{call_name}留个微信也可以呀，有合适的人选我好联系你～",
                f"嗯嗯～{call_name}不方便留电话的话，留个微信也可以呢～",
                f"好哒～那{call_name}加个微信吧，我这边有合适的可以联系你～",
            ]
            return random.choice(responses)

        elif confirm_count == 3:
            # 第三次：委婉结束话题
            responses = [
                f"嗯嗯好的～那先这样哈，有需要再联系我呀～",
                f"好哒{call_name}～那我们下次再聊，祝你早日脱单哦～",
                f"嗯嗯～那先这样吧，{call_name}有空再联系我呀～",
            ]
            return random.choice(responses)

        else:
            # 第四次及以上：不再回复，返回空响应
            return ""

    def _is_hong_user(self, location: Optional[str]) -> bool:
        """判断用户是否是香港用户"""
        if not location:
            return False
        location_lower = location.lower()
        return '香港' in location_lower or 'hk' in location_lower

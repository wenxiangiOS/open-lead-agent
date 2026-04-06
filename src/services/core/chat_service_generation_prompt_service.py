import copy
import re
from typing import Any, Dict

from src.utils.validators import PhoneValidator, WechatValidator


class ChatServiceGenerationPromptService:
    def __init__(self, host: Any) -> None:
        self.host = host

    def _build_contact_candidate_generation_instruction(
        self,
        *,
        user_message: str,
        user_profile,
        action_value: str,
    ) -> str:
        effective_action = str(action_value or "").strip()
        if effective_action not in {"ask_phone", "persuade_phone", "ask_wechat", "persuade_wechat"}:
            last_requested_type = str(getattr(user_profile, "last_contact_request_type", "") or "").strip()
            if last_requested_type == "phone":
                effective_action = "ask_phone"
            elif last_requested_type == "wechat":
                effective_action = "ask_wechat"
        if effective_action not in {"ask_phone", "persuade_phone", "ask_wechat", "persuade_wechat"}:
            return ""

        candidate, hinted_type = self.host._infer_contact_attempt_from_context(user_message, effective_action)
        if not candidate:
            return ""

        if hinted_type == "wechat":
            is_valid, _ = WechatValidator.is_valid(candidate)
            if is_valid:
                return ""
            return (
                "【联系方式候选校验提示】\n"
                "用户这轮像是在发微信号，但这个微信号看起来还不能直接确认有效。\n"
                "所以这轮不要说“我存好了/我记下了/后面联系你”。\n"
                "请直接用自然口语提醒对方微信号看起来没发完整或格式不太对，引导对方重发一个常用微信。\n"
                "语气要轻，不要业务腔，不要固定模板复读。\n"
            )

        digits = "".join(ch for ch in candidate if ch.isdigit())
        if digits.startswith("86") and len(digits) == 13 and digits[2] == "1":
            digits = digits[2:]
        is_valid_phone, _ = PhoneValidator.is_valid(digits)
        if is_valid_phone:
            return ""
        return (
            "【联系方式候选校验提示】\n"
            "用户这轮像是在发手机号，但这个号码还不能直接确认有效。\n"
            "所以这轮不要说“我存好了/我记下了/后面联系你”。\n"
            "请直接用自然口语提醒对方号码看起来不太对，引导对方重发一个常用手机号。\n"
            "语气要轻，可以解释成后面沟通会方便一点，但不要业务腔，不要固定模板复读。\n"
        )

    def _build_contact_completion_generation_instruction(
        self,
        *,
        user_profile,
        understanding_result,
    ) -> str:
        resolved_slots = dict(getattr(understanding_result, "resolved_slots", {}) or {})

        projected_profile = copy.deepcopy(user_profile)
        for field in (
            "sex",
            "age",
            "age_label",
            "education",
            "monthly_income",
            "location",
            "occupation",
            "marital_status",
            "partner_requirement",
        ):
            value = resolved_slots.get(field)
            if value not in (None, ""):
                setattr(projected_profile, field, value)

        phone_value = str(resolved_slots.get("phone") or "").strip()
        wechat_value = str(resolved_slots.get("wechat") or "").strip()
        generic_contact = str(resolved_slots.get("contact") or "").strip()
        if not phone_value and generic_contact and generic_contact.isdigit():
            phone_value = generic_contact
        if not wechat_value and generic_contact and not generic_contact.isdigit():
            wechat_value = generic_contact

        if phone_value:
            projected_profile.phone = phone_value
            projected_profile.phone_collected = True
        if wechat_value:
            projected_profile.wechat = wechat_value
            projected_profile.wechat_collected = True
        if phone_value or wechat_value:
            projected_profile.collection_progress["contact"] = True

        if not self.host._can_end_with_contact_completion(projected_profile):
            return ""

        ending_info = self.host.ending_service.build_ending_info("normal_complete", projected_profile)
        extra = str(ending_info.get("extra_instructions") or "").strip()
        projected_profile.conversation_ended = False
        if not extra:
            return ""
        return (
            "【联系方式完成收尾专用生成】\n"
            "当前唯一任务：当前资料与联系方式已经满足收尾条件，这轮第一次生成就直接完成自然收尾。\n"
            "第一次生成的话术就是最终展示话术，后续不会再改写。\n"
            "这轮必须满足：\n"
            "1. 不要再追问任何资料，不要再索要电话或微信。\n"
            "2. 不要出现“我存好了/我记下了/我都记清楚了/有合适的人选我再跟你同步/有消息我联系你/发资料给你”这类说法。\n"
            "3. 只输出一段自然中文收尾，不要分条，不要反问。\n"
            f"4. {extra}\n"
        )

    def _build_contact_success_followup_generation_instruction(
        self,
        *,
        user_message: str,
        user_profile,
        action_value: str,
    ) -> str:
        candidate_meta = self.host.contact_validation_flow_service.classify_contact_candidate(
            user_message=user_message,
            user_profile=user_profile,
            next_action_value=action_value,
        )
        classification = str(candidate_meta.get("classification") or "").strip()
        contact_type = str(candidate_meta.get("contact_type") or "").strip()
        candidate = str(candidate_meta.get("candidate") or "").strip()
        if classification not in {"valid_phone", "valid_wechat"} or not contact_type or not candidate:
            return ""

        projected_profile = copy.deepcopy(user_profile)
        if contact_type == "phone":
            projected_profile.phone = candidate
            projected_profile.phone_collected = True
            projected_profile.pending_contact_candidate = None
            projected_profile.pending_contact_field = None
            projected_profile.pending_contact_hint = None
        else:
            projected_profile.wechat = candidate
            projected_profile.wechat_collected = True
            projected_profile.pending_contact_candidate = None
            projected_profile.pending_contact_field = None
            projected_profile.pending_contact_hint = None
        projected_profile.contact = projected_profile.get_contact_status()

        projected_next_action = self.host.contact_service.get_next_action(projected_profile, user_message)
        projected_action_value = str(getattr(projected_next_action, "value", projected_next_action) or "").strip()

        followup_map = {
            ("phone", "ask_wechat"): "微信",
            ("phone", "persuade_wechat"): "微信",
            ("wechat", "ask_phone"): "电话",
            ("wechat", "persuade_phone"): "电话",
        }
        followup_label = followup_map.get((contact_type, projected_action_value), "")
        if not followup_label:
            return ""

        current_label = "手机号" if contact_type == "phone" else "微信"
        return (
            "【联系方式成功后顺带追问专用生成】\n"
            f"用户这轮刚刚提供了有效{current_label}，而且按当前状态机，下一步应该继续询问{followup_label}。\n"
            "这轮第一次生成就要一次性完成两个动作：\n"
            f"1. 自然确认{current_label}已收到；\n"
            f"2. 顺势轻问{followup_label}。\n"
            "第一次生成的话术就是最终展示话术，后续不会再改写。\n"
            "这轮不要只确认已收到就结束，也不要拆到下一轮再问。\n"
            "语气要像真人顺着聊，只能给一句很轻的原因，比如后面沟通更顺一点、联系更方便一点。\n"
            "不要营销腔，不要承诺过满，不要固定模板复读。\n"
        )

    def _should_limit_opening_followup_to_single_field(
        self,
        *,
        user_message: str,
        user_profile,
        understanding_result,
    ) -> bool:
        if str(getattr(understanding_result, "primary_turn_type", "") or "").strip() != "opening":
            return False
        if str(getattr(user_profile, "sex", "") or "").strip():
            return False

        resolved_slots = dict(getattr(understanding_result, "resolved_slots", {}) or {})
        inferred_preference = str(
            resolved_slots.get("partner_gender_preference")
            or getattr(user_profile, "partner_gender_preference", "")
            or self.host.turn_understanding_service._extract_partner_gender_preference(user_message)  # noqa: SLF001
            or ""
        ).strip()
        return inferred_preference in {"男", "女"}

    @staticmethod
    def _detect_suspicious_profile_value(user_message: str) -> tuple[str, str]:
        text = str(user_message or "").strip()
        if not text:
            return "", ""

        age_match = re.search(r"(?:今年|我今年|年龄|岁数)?\s*(\d{1,4})\s*岁", text)
        if age_match:
            age_text = age_match.group(1)
            try:
                age_value = int(age_text)
            except ValueError:
                age_value = 0
            if age_value <= 10 or age_value >= 120:
                return "age", f"{age_text}岁"

        height_meter_match = re.search(r"(?:身高|高)\s*(\d(?:\.\d+)?)\s*米", text)
        if height_meter_match:
            try:
                meter_value = float(height_meter_match.group(1))
            except ValueError:
                meter_value = 0.0
            if meter_value <= 0.8 or meter_value >= 2.6:
                return "height", f"{height_meter_match.group(1)}米"

        height_cm_match = re.search(r"(?:身高|高)\s*(\d{2,3})\s*(?:cm|厘米)?", text, re.IGNORECASE)
        if height_cm_match:
            try:
                height_value = int(height_cm_match.group(1))
            except ValueError:
                height_value = 0
            if height_value <= 80 or height_value >= 260:
                return "height", f"{height_cm_match.group(1)}cm"
        return "", ""

    def _build_suspicious_value_generation_instruction(self, *, user_message: str) -> str:
        field, raw_value = self._detect_suspicious_profile_value(user_message)
        if not field or not raw_value:
            return ""

        field_label = "年龄" if field == "age" else "身高"
        return (
            "【异常资料澄清专用生成】\n"
            f"用户这轮给出的{field_label}看起来像是输错了，当前检测到的异常值是“{raw_value}”。\n"
            f"这轮第一次生成的唯一任务，是像真人一样先澄清这个{field_label}是不是输入错误。\n"
            "第一次生成的话术就是最终展示话术，后续不会再改写。\n"
            "必须满足：\n"
            f"1. 只围绕“{field_label}”做澄清确认，不要继续追问职业、收入、学历、联系方式等其他字段。\n"
            "2. 不要直接结束对话，不要指责用户，也不要说对方在乱填。\n"
            "3. 语气要自然，像顺手确认对方是不是手滑输错了。\n"
            "4. 不要固定模板复读。\n"
        )

    @staticmethod
    def _build_primary_followup_generation_instruction(
        *,
        ask_field: str,
        side_target: str = "",
    ) -> str:
        field_label_map = {
            "sex": "性别",
            "age": "年龄/年龄段",
            "education": "学历",
            "occupation": "工作方向",
            "location": "常住城市",
            "marital_status": "婚况/感情状态",
            "monthly_income": "收入区间",
            "partner_requirement": "择偶要求/更看重哪一点",
        }
        main_label = field_label_map.get(ask_field, ask_field)
        side_label = field_label_map.get(side_target, side_target) if side_target else ""
        instruction = (
            "【字段追问主路径生成】\n"
            f"当前唯一主任务：第一次生成就把这轮对“{main_label}”的追问完成。\n"
            "第一次生成的话术就是最终展示话术，后续不会再改写。\n"
            "这轮必须满足：\n"
            "1. 先顺着当前上下文轻接一句，再自然追问，不要只做承接不提问。\n"
            "2. 主问题只能围绕当前字段，不能问偏，不能改问别的主字段。\n"
            "3. 问法要自然口语化，像真人顺着聊，不要模板腔，不要客服腔。\n"
            "4. 不要空话、废话，不要只说‘我记下了’就停住。\n"
            "5. 如果不是解释型重问，就不要硬塞一大段解释；解释只在确实需要时轻轻带一句。\n"
            "6. 默认只完成这一轮该做的追问，不要超量追问。\n"
        )
        if side_label:
            instruction += (
                f"7. 这轮允许把“{side_label}”作为顺带字段自然融合，但主线仍然必须是“{main_label}”。\n"
                "8. 如果顺带字段不够自然，就不要硬拼；总问题数最多两个，而且必须有明显衔接。\n"
            )
        else:
            instruction += "7. 这轮只问当前主字段，不要额外再补第二个无关问题。\n"
        return instruction

    @staticmethod
    def _build_retry_generation_instruction(*, ask_field: str, retry_reason: str) -> str:
        field_label_map = {
            "sex": "性别",
            "age": "年龄/年龄段",
            "education": "学历",
            "occupation": "工作方向",
            "location": "常住城市",
            "marital_status": "婚况/感情状态",
            "monthly_income": "收入区间",
            "partner_requirement": "择偶要求/更看重哪一点",
        }
        field_label = field_label_map.get(ask_field, ask_field)
        reason_line = (
            "用户刚对当前核心资料说了“先不方便说/不想说”之类的话。"
            if retry_reason == "soft_refusal"
            else "这个字段上一轮没有形成有效询问或被中途打断，这轮需要换个更自然的方式重新问回来。"
        )
        return (
            "【字段解释型重问专用生成】\n"
            f"当前唯一任务：针对“{field_label}”做一次换话术+解释型重问。\n"
            "这轮第一次生成就要把这次重问完成，第一次生成的话术就是最终展示话术。\n"
            f"{reason_line}\n"
            "这轮必须同时满足：\n"
            "1. 先轻接住当前上下文，再顺着往下问。\n"
            "2. 用一句自然解释说明只是想大概了解一下，不用说太细。\n"
            "3. 继续追问同一个字段，不能跳去别的字段。\n"
            "4. 只输出一段自然中文，不要分条，不要模板腔，不要拼接两段问题。\n"
            "5. 不要说“先跳过这块”“那就先不问了”“咱们慢慢聊就好”这种会放弃当前字段的话。\n"
            "6. 不要只安抚不追问。\n"
            "7. 不要用很别扭的尾巴，比如“学历不？”“工作不？”。\n"
            "8. 如果字段是婚况，只能用“婚况”或“感情状态”，禁止出现“单身状态”。\n"
            "9. 不要用“哈哈”“哈呀”这种过度随意的口头语起手。\n"
            "10. 不要用“摸个底”“探个底”“先盘一下”这种不自然、带测试感的说法。\n"
            "11. 解释要更像真人：围绕“只是想大概了解下，后面顺着你的情况聊会更合适/更顺一点”，不要泛泛而谈。\n"
            "12. 语气要轻，但不要油，不要玩笑感太重。\n"
            "13. 可参考的语气方向是：‘我不是想问得很细，就是想大概了解下……你说个大概就行。’只参考语气，不要机械照抄。\n"
        )

    @staticmethod
    def _build_contact_action_generation_instruction(*, action_value: str) -> str:
        action_label_map = {
            "ask_phone": "第一次自然询问电话",
            "persuade_phone": "电话第一次拒绝后的换话术+解释型继续争取电话",
            "ask_wechat": "第一次自然询问微信",
            "persuade_wechat": "微信第一次拒绝后的换话术+解释型继续争取微信",
        }
        target_label_map = {
            "ask_phone": "电话",
            "persuade_phone": "电话",
            "ask_wechat": "微信",
            "persuade_wechat": "微信",
        }
        target_label = target_label_map.get(action_value, "联系方式")
        return (
            "【联系方式动作专用生成】\n"
            f"当前唯一任务：{action_label_map.get(action_value, action_value)}。\n"
            "这轮第一次生成就要把这个联系方式动作完成，第一次生成的话术就是最终展示话术。\n"
            f"这轮只能围绕“{target_label}”生成，不能擅自切到另一种联系方式。\n"
            "必须满足：\n"
            "1. 只围绕当前指定联系方式说话。\n"
            "2. 如果是 persuade 场景，要先轻接顾虑，再给一句低压力解释，再继续问同一种联系方式。\n"
            "3. 不要把电话拒绝直接改成问微信，也不要把微信拒绝直接改成问电话。\n"
            "4. 不要营销腔，不要“哈哈”起手，不要长篇说服。\n"
            "5. 禁止说“发资料 / 发照片 / 推具体人选 / 安排见面 / 发你资料 / 发对方资料”。\n"
            "6. 只能表达“后续沟通更顺一点 / 继续联系更方便一点”，不能把用途说得过满。\n"
            "7. 只输出一条自然、简短、口语化的中文回复。\n"
        )

    def build_response_plan_generation_instruction(
        self,
        *,
        user_message: str,
        user_profile,
        turn_decision,
        understanding_result,
    ) -> str:
        spec = self.host.response_plan_builder.build(
            turn_decision=turn_decision,
            user_profile=user_profile,
            user_message=user_message,
            understanding_result=understanding_result,
        )
        return self.host.response_plan_prompt_formatter.build_generation_instruction(spec)

    def build_generation_prompt(
        self,
        *,
        user_message: str,
        user_profile,
        conversation_context: Dict[str, Any],
        turn_decision,
        understanding_result,
    ) -> str:
        base_prompt = self.host.dialogue_manager.build_main_dialogue_prompt(
            user_message,
            user_profile,
            conversation_context,
            prioritize_user_question=turn_decision.prioritize_user_question,
            primary_move=turn_decision.primary_move,
            allow_contact_target=turn_decision.allow_contact_target,
            allow_medium_target=turn_decision.allow_medium_target,
        )
        bridge_instruction = self.host._build_profile_bridge_generation_instruction(
            user_message=user_message,
            user_profile=user_profile,
            turn_decision=turn_decision,
            conversation_context=conversation_context,
        )
        contact_completion_instruction = self._build_contact_completion_generation_instruction(
            user_profile=user_profile,
            understanding_result=understanding_result,
        )
        suspicious_value_instruction = self._build_suspicious_value_generation_instruction(
            user_message=user_message,
        )
        response_plan_instruction = self.build_response_plan_generation_instruction(
            user_message=user_message,
            user_profile=user_profile,
            turn_decision=turn_decision,
            understanding_result=understanding_result,
        )
        retry_instruction = ""
        ask_field = str(getattr(turn_decision, "ask_field", "") or "").strip()
        pending_retry_field = str(getattr(user_profile, "pending_retry_field", "") or "").strip()
        retryable_fields = {
            "sex", "age", "education", "occupation", "location",
            "marital_status", "monthly_income", "partner_requirement",
        }
        side_target = ""
        if ask_field and ask_field != "contact":
            try:
                policy_decision = self.host.collection_policy.decide(
                    user_profile,
                    user_message=user_message,
                    allow_contact_target=getattr(turn_decision, "allow_contact_target", False),
                    allow_medium_target=getattr(turn_decision, "allow_medium_target", False),
                    prioritize_user_question=getattr(turn_decision, "prioritize_user_question", False),
                    primary_move=getattr(turn_decision, "primary_move", "ack_and_ask"),
                )
                if str(getattr(policy_decision, "main_target", "") or "").strip() == ask_field:
                    candidate_side_target = str(getattr(policy_decision, "side_target", "") or "").strip()
                    if (
                        candidate_side_target
                        and candidate_side_target != ask_field
                        and self.host.collection_policy.can_actively_ask(user_profile, candidate_side_target)
                    ):
                        side_target = candidate_side_target
            except Exception:
                side_target = ""
        if self._should_limit_opening_followup_to_single_field(
            user_message=user_message,
            user_profile=user_profile,
            understanding_result=understanding_result,
        ):
            side_target = ""
        primary_followup_instruction = ""
        if ask_field in retryable_fields and not (
            getattr(understanding_result, "subtype", None) == "soft_refusal_current_field"
            or pending_retry_field == ask_field
        ):
            primary_followup_instruction = self._build_primary_followup_generation_instruction(
                ask_field=ask_field,
                side_target=side_target if getattr(turn_decision, "allow_medium_target", False) else "",
            )
        if ask_field in retryable_fields:
            if getattr(understanding_result, "subtype", None) == "soft_refusal_current_field":
                retry_instruction = self._build_retry_generation_instruction(
                    ask_field=ask_field,
                    retry_reason="soft_refusal",
                )
            elif pending_retry_field == ask_field:
                retry_instruction = self._build_retry_generation_instruction(
                    ask_field=ask_field,
                    retry_reason="pending_retry",
                )
        if ask_field == "contact":
            try:
                next_action = self.host.contact_service.get_next_action(user_profile, user_message)
                action_value = str(getattr(next_action, "value", next_action) or "").strip()
            except Exception:
                action_value = ""
            if action_value in {"ask_phone", "persuade_phone", "ask_wechat", "persuade_wechat"}:
                retry_instruction = "\n\n".join(
                    part for part in (
                        primary_followup_instruction,
                        retry_instruction,
                        self._build_contact_action_generation_instruction(action_value=action_value),
                        self._build_contact_success_followup_generation_instruction(
                            user_message=user_message,
                            user_profile=user_profile,
                            action_value=action_value,
                        ),
                        self._build_contact_candidate_generation_instruction(
                            user_message=user_message,
                            user_profile=user_profile,
                            action_value=action_value,
                        ),
                    )
                    if str(part or "").strip()
                )
        elif primary_followup_instruction:
            retry_instruction = "\n\n".join(
                part for part in (primary_followup_instruction, retry_instruction) if str(part or "").strip()
            )
        opening_intent_detection_enabled = self.host._should_run_opening_intent_detection(
            conversation_context,
            user_profile,
        ) and turn_decision.response_channel == "model"
        return self.host.prompt_assembly_service.assemble_for_generation(
            base_prompt,
            profile_bridge_instruction=bridge_instruction,
            response_plan_instruction="\n\n".join(
                part
                for part in (contact_completion_instruction, suspicious_value_instruction, retry_instruction, response_plan_instruction)
                if str(part or "").strip()
            ),
            opening_intent_detection_enabled=opening_intent_detection_enabled,
        )

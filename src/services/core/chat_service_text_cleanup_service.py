import re
from typing import Any, Dict, Optional

from src.models.user_profile import UserProfile
from src.services.core.chat_service_contact_text_service import ChatServiceContactTextService
from src.services.core.chat_service_response_cleanup_service import (
    ChatServiceResponseCleanupService,
)


class ChatServiceTextCleanupService:
    def __init__(self, host: Any) -> None:
        self.host = host

    @staticmethod
    def soften_absolute_promise_language(response: str) -> str:
        text = str(response or "").strip()
        if not text:
            return text

        phrase_replacements = (
            (r"绝对不会", "一般不会"),
            (r"绝不会", "一般不会"),
            (r"肯定不会", "一般不会"),
            (r"一定不会", "一般不会"),
            (r"完全不会", "一般不会"),
            (r"保证不会", "尽量避免"),
            (r"确保不会", "尽量避免"),
            (r"绝对不", "一般不"),
            (r"肯定不", "一般不"),
            (r"一定不", "先不"),
            (r"绝对会", "会"),
            (r"肯定会", "会"),
            (r"一定会", "会"),
        )
        for pattern, replacement in phrase_replacements:
            text = re.sub(pattern, replacement, text)

        single_word_replacements = (
            (r"绝对", "尽量"),
            (r"肯定", "会"),
            (r"一定", ""),
            (r"保证", "尽量"),
            (r"确保", "尽量"),
        )
        for pattern, replacement in single_word_replacements:
            text = re.sub(pattern, replacement, text)

        text = re.sub(r"尽量尽量", "尽量", text)
        text = re.sub(r"会会", "会", text)
        text = re.sub(r"先不先不", "先不", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def sanitize_robotic_tone(response: str) -> str:
        """压掉明显的登记腔、客服腔和业务身份腔。"""
        text = str(response or "").strip()
        if not text:
            return text
        preserve_terminal_copy = (
            any(marker in text for marker in ("等好消息", "祝你早日脱单", "提前约时间", "不打扰你"))
            and any(marker in text for marker in ("匹配一般1-8小时", "匹配一般1-2天"))
        )

        replacements = {
            "我是帮大家做交友匹配的小缘": "我是小缘",
            "交友匹配": "聊这个",
            "我先确认一下": "我想先确认一下",
            "顺口问下": "想问下",
            "给你匹配到合适的人选": "后面要是有合适的方向",
            "及时联系到你": "继续联系上你",
            "及时通知到你": "继续联系上你",
            "方便及时通知到你": "方便继续联系上你",
            "资料差不多先了解到了": "后面要是继续聊得合适",
            "我已经记下啦": "我先记下了",
            "我先记下来啦": "我先记下了",
            "哈哈是呀，": "",
            "是这样哦，": "",
            "发资料用微信也顺手": "后续沟通用微信也更顺一点",
            "发资料走微信也顺手": "后续沟通用微信也更顺一点",
            "发你资料": "继续沟通",
            "发对方资料": "继续沟通",
        }
        for before, after in replacements.items():
            text = text.replace(before, after)

        text = re.sub(r"我记下来了", "我先记下了", text)
        text = re.sub(r"我记下来了。", "我先记下了。", text)
        text = re.sub(r"我记下你是", "你是", text)
        text = re.sub(r"我记下来啦", "我先记下了", text)
        text = re.sub(r"我记下来", "我先记下了", text)
        text = re.sub(r"我记下了", "我先记下了", text)
        text = re.sub(r"我记下", "我先记下了", text)
        text = re.sub(r"我先按([^，。！？!?]+)记(着|下|哈)?", r"\1是吧", text)
        text = re.sub(r"我先按([^，。！？!?]+)理解", r"\1是吧", text)
        text = re.sub(r"那我先按([^，。！？!?]+)记(着|下|哈)?", r"\1是吧", text)
        text = re.sub(r"我知道了来你是", "我知道了，你是", text)
        text = re.sub(r"我知道了你是", "你是", text)
        text = re.sub(r"(好的|好呀|好哒)，?你是", r"\1，你是", text)
        text = re.sub(r"^好[，,\s]*你是(男生|女生)(?:啦|呀|哈|啊)?[。.]?\s*", "", text)
        text = re.sub(r"^好[，,\s]*(男生|女生)是吧[。.]?\s*", "", text)
        text = re.sub(r"^(你是|是)(男生|女生)(?:啦|呀|哈|啊)?[。.]?\s*", "", text)
        text = re.sub(r"^你在[^。！？!?]{0,20}是吧[。.]?\s*", "", text)
        text = re.sub(r"^(?:好[，,\s]*)?(?:在)?[^。！？!?]{1,8}这边是吧[。.]?\s*", "", text)
        text = re.sub(
            r"^(?:好[，,\s]*)?(?:做)?[^。！？!?]{1,10}(?:是吧|我知道了|这块我知道了|方向，明白了)[。.]?\s*",
            "",
            text,
        )
        text = re.sub(
            r"^(?:好[，,\s]*)?(?:90后|80后|00后|\d{2}岁)(?:呀[，,]?)?(?:知道了|明白了|我知道了|是吧)?[。.]?\s*",
            "",
            text,
        )
        text = re.sub(r"^(?:好[，,\s]*)?(?:本科|大专|硕士|博士)(?:这边明白了|我知道了|是吧)?[。.]?\s*", "", text)
        text = re.sub(r"^(?:好[，,\s]*)?[^。！？!?]{1,12}这行我接住了[。.]?\s*", "", text)
        text = re.sub(r"^(?:好[，,\s]*)?学历这块是[^。！？!?]{1,12}[。.]?\s*", "", text)
        text = re.sub(r"^(?:好[，,\s]*)?现在主要做[^。！？!?]{1,14}这块(?:[，,]?是吧)?[。.]?\s*", "", text)
        text = re.sub(r"发(?:你|给你)?(?:对方)?资料", "后续沟通", text)
        text = re.sub(r"发照片", "继续沟通", text)
        text = re.sub(r"推具体人选", "继续沟通", text)
        text = re.sub(r"安排见面", "后续沟通", text)
        text = re.sub(r"后续有合适的(?:对象|人选)[^，。！？!?]*发资料[^，。！？!?]*", "后续沟通起来也更顺一点", text)
        text = re.sub(r"有适配的(?:对象|人选)[^，。！？!?]*发资料[^，。！？!?]*", "后续沟通起来也更顺一点", text)

        blacklist_patterns = [
            r"同城脱单联盟",
            r"牵线(小伙伴|同事)?",
            r"精准匹配",
            r"第一时间联系",
        ]
        if not preserve_terminal_copy:
            blacklist_patterns.extend(
                [
                    r"好消息",
                    r"祝你早日脱单[🥰~！!。]*",
                    r"匹配一般1-8小时[^\n。！？!?]*",
                    r"匹配一般1-2天[^\n。！？!?]*",
                ]
            )
        for pattern in blacklist_patterns:
            text = re.sub(pattern, "", text)

        text = re.sub(r"那我们就按([^，。！？!?]+)来聊", r"\1是吧", text)
        text = re.sub(r"按([^，。！？!?]+)来聊", r"\1是吧", text)
        text = re.sub(r"按这个方向来聊", "这个方向我大概有数了", text)
        text = re.sub(r"按这个优先推进", "", text)
        text = re.sub(r"按这个优先筛", "", text)
        text = re.sub(r"按你的优先级来", "", text)
        text = re.sub(r"我先按([^，。！？!?]+)来理解", r"\1是吧", text)
        text = re.sub(r"我先按([^，。！？!?]+)来聊", r"\1是吧", text)

        text = re.sub(r"[，,]?我们先不连着问资料[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?我先不连着追问[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?这轮我先不把资料问得太密[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?这轮先不把资料问得太密[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?我先把节奏放缓一点[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?先不把资料问得太密[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?这轮我先不继续追资料[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?这轮我先不追问资料[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?我先不追问资料[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?我先不往资料上追问[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?(我|那我)?语气放轻松(一点|些)?[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?我就把语气放轻一点[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?我就轻松一点跟你聊[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?问得有点密了[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?像查户口一样[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?按流程来[^。！？!?]*", "", text)
        text = re.sub(r"[，,]?按当前沟通流程来[^。！？!?]*", "", text)

        text = re.sub(r"按这个方向帮你筛[^。！？!?]*", "", text)
        text = re.sub(r"按这个优先推进[^。！？!?]*", "", text)
        text = re.sub(r"我照这个方向[^。！？!?]*", "", text)
        text = re.sub(r"按这个方向来[^。！？!?]*", "", text)

        text = re.sub(r"说一个最在意的匹配点[^。！？!?]*", "", text)
        text = re.sub(r"先说一个最在意[^。！？!?]*", "", text)
        text = re.sub(r"你先告诉我你最看重[^。！？!?]*", "", text)
        text = re.sub(r"我们可以先说一个[^。！？!?]*", "", text)
        text = re.sub(r"最看重的匹配条件[^。！？!?]*", "", text)
        text = re.sub(r"我按这个优先筛[^。！？!?]*", "", text)
        text = re.sub(r"我好优先筛选[^。！？!?]*", "", text)
        text = re.sub(r"你最看重哪一点，可以先顺手说说[^。！？!?]*", "", text)
        text = re.sub(r"你会更看重哪个[^。！？!?]*", "", text)
        text = re.sub(r"你会更偏哪边[^。！？!?]*", "", text)
        text = re.sub(r"按同城思路跟你聊[^。！？!?]*", "", text)
        text = re.sub(r"你最看重[^？?]*[？?]", "", text)
        text = re.sub(r"你最在意[^？?]*[？?]", "", text)

        text = re.sub(r"主目标[：:][^。\n]*", "", text)
        text = re.sub(r"顺带目标[：:][^。\n]*", "", text)
        text = re.sub(r"本轮计划[：:][^。\n]*", "", text)
        text = re.sub(r"用户类型[：:][^。\n]*", "", text)
        text = re.sub(r"可进联系方式[：:][^。\n]*", "", text)

        text = re.sub(r"^好的，[，,\s]*", "好，", text)
        text = re.sub(r"^好呀，[，,\s]*", "好，", text)
        text = re.sub(r"^好哒，[，,\s]*", "好，", text)
        text = re.sub(r"^哈哈好的[，,\s]*", "好，", text)
        text = re.sub(r"^哈哈[，,\s]*", "", text)
        text = re.sub(r"联系电话不([。！？!?]?)", r"联系电话吗\1", text)
        text = re.sub(r"^(?:了|啦|呀|呢|哈|啊)[。．]\s*", "", text)
        text = re.sub(r"([。！？!?])\s*(哈哈，原来|原来|这样的话|所以说)\s*$", r"\1", text)
        text = re.sub(r"^(哈哈，原来|原来|这样的话|所以说)\s*$", "", text)
        text = ChatServiceTextCleanupService.soften_absolute_promise_language(text)
        text = re.sub(r"[，,。]{2,}", "。", text)
        text = re.sub(r"([。！？!?])([^\s])", r"\1 \2", text)
        text = re.sub(r"\s+", " ", text).strip(" ，,。")
        text = ChatServiceResponseCleanupService.strip_broken_edge_fragments(text)
        return text

    def apply_refusal_respect_guard(
        self,
        response: str,
        user_profile: UserProfile,
        user_message: str = "",
    ) -> str:
        text = str(response or "").strip()
        message = str(user_message or "").strip()
        if not text or not message:
            return text
        if not any(
            re.search(pattern, message)
            for pattern in (r"不方便", r"不想说", r"先不说", r"不留", r"不太想", r"算了", r"再说吧")
        ):
            return text

        if (
            user_profile.phone_collected
            and not user_profile.wechat_collected
            and any(token in message for token in ("微信",))
            and any(token in message for token in ("干嘛", "为什么", "还要", "有电话"))
        ):
            return (
                "主要是有时候电话不一定方便接，微信发个消息你会更方便看到，"
                "所以我才顺手问一句。你要是不想留也没关系，我们按电话联系就行。"
            )

        if "必须" in text or "一定要" in text or "赶紧留电话" in text or "不留不行" in text:
            return "没关系，这块我们先不急，按你方便的节奏来。"

        try:
            next_action = self.host.contact_service.get_next_action(user_profile, message)
            action_value = getattr(next_action, "value", str(next_action))
        except Exception:
            action_value = "none"

        if action_value in {"none", "end"} and self.host.contact_service.is_contact_complete(user_profile):
            if self.host._can_end_with_contact_completion(user_profile):
                return self.host._get_contact_completion_ending_response(user_profile)
            if self.host._can_end_without_contact(user_profile):
                return self.host._get_no_contact_completion_response()
            return self.host._get_contact_terminal_or_resume_response(user_profile, message)

        if action_value == "ask_wechat":
            response = ChatServiceContactTextService.build_ask_wechat_fallback()
            if not any(token in response for token in ("没关系", "不急", "不勉强")):
                return f"没关系，{response}"
            return response
        if action_value == "persuade_wechat":
            return ChatServiceContactTextService.build_persuade_wechat_fallback()
        if action_value == "ask_phone":
            return "我知道你这会儿可能对电话有点顾虑。你要是方便的话，留个常用手机号就行，后面有合适方向我也方便联系你。"
        if action_value == "persuade_phone":
            return "我懂，你现在可能对电话这块还有点犹豫。你要是方便的话，留个常用手机号就行，后面有合适方向我也方便联系你。"
        if self.host._contains_contact_push_markers(text):
            return "没关系，这块我们先不急，继续聊别的也可以。"
        if not any(marker in text for marker in ("没关系", "不急", "不勉强", "理解", "那我们先")):
            return f"没关系，{text}"
        return text

    def prevent_no_repeat_hold_from_blocking_progress(
        self,
        response: str,
        user_profile: UserProfile,
        *,
        collection_result: Optional[Dict[str, Any]] = None,
        user_message: str = "",
    ) -> str:
        text = str(response or "").strip()
        if not text or user_profile.conversation_ended:
            return text
        if self.host._contains_contact_push_markers(text):
            return text

        no_repeat_hold_markers = (
            "不在这上面打转",
            "不重复绕了",
            "继续往下聊",
            "继续往下说",
            "接着往下聊",
        )
        if not any(marker in text for marker in no_repeat_hold_markers):
            return text

        unresolved_core = self.host.collection_policy.get_uncovered_core_fields(user_profile)
        if unresolved_core:
            next_field = self.host.collection_policy.get_main_target(
                user_profile,
                can_enter_contact=False,
                allow_contact_target=False,
            ) or unresolved_core[0]
            if next_field:
                return self.host._build_followup_seed_for_model_rewrite(
                    next_field,
                    user_profile,
                    user_message=user_message,
                )

        if self.host.collection_policy.can_enter_contact(user_profile):
            return self.host._build_followup_seed_for_model_rewrite(
                "contact",
                user_profile,
                user_message=user_message,
            )

        return text

    def downgrade_premature_profile_summary(
        self,
        response: str,
        user_profile: UserProfile,
        *,
        collection_result: Optional[Dict[str, Any]] = None,
        ask_field: Optional[str] = None,
    ) -> str:
        text = str(response or "").strip()
        if not text:
            return text

        current_ask_field = str(ask_field or "").strip()
        if current_ask_field not in {
            "sex",
            "age",
            "education",
            "occupation",
            "location",
            "marital_status",
            "monthly_income",
            "partner_requirement",
        }:
            return text

        if self.host.collection_policy.can_enter_contact(user_profile):
            return text

        summary_patterns = (
            r"^(?:(?:好哦|好呀|好哒|好|好的|嗯)[，,]\s*)?你的基本情况我大概有数啦[，,]?",
            r"^(?:(?:好哦|好呀|好哒|好|好的|嗯)[，,]\s*)?你的情况我大概有数啦[，,]?",
            r"^(?:(?:好哦|好呀|好哒|好|好的|嗯)[，,]\s*)?你的基本情况我这边已经了解得差不多了[，,]?",
            r"^(?:(?:好哦|好呀|好哒|好|好的|嗯)[，,]\s*)?你的情况我这边已经了解得差不多了[，,]?",
            r"^(?:(?:好哦|好呀|好哒|好|好的|嗯)[，,]\s*)?我这边大概了解了[，,]?",
            r"^(?:(?:好哦|好呀|好哒|好|好的|嗯)[，,]\s*)?我这边心里有数了[，,]?",
        )
        if not any(re.search(pattern, text) for pattern in summary_patterns):
            return text

        extracted_fields = [
            item for item in (collection_result or {}).get("all_fields", [])
            if isinstance(item, dict) and str(item.get("field") or "").strip()
        ]
        ack_prefix = ""
        if extracted_fields:
            ack_order = ("marital_status", "education", "occupation", "location", "age", "sex")
            for field_name in ack_order:
                matched = next((item for item in extracted_fields if str(item.get("field") or "").strip() == field_name), None)
                if not matched:
                    continue
                ack = self.host._build_contextual_followup_ack(  # noqa: SLF001
                    field_name,
                    matched.get("value"),
                    ask_field=current_ask_field,
                    user_profile=user_profile,
                    include_followup_transition=False,
                )
                if ack:
                    ack_prefix = ack.strip()
                    break

        if not ack_prefix:
            fallback_map = {
                "monthly_income": "好，这两个点我先接住。",
                "marital_status": "好，这个我先接住。",
                "partner_requirement": "好，这个方向我先接住。",
                "education": "好，我先顺着你刚说的继续聊。",
                "occupation": "好，我先顺着你刚说的继续聊。",
                "location": "好，我先顺着你刚说的继续聊。",
                "age": "好，我先顺着你刚说的继续聊。",
                "sex": "好，我先顺着你刚说的继续聊。",
            }
            ack_prefix = fallback_map.get(current_ask_field, "好，我先顺着你刚说的继续聊。")

        updated = text
        for pattern in summary_patterns:
            updated = re.sub(pattern, "", updated).strip()
        updated = re.sub(r"^[，,\s]+", "", updated).strip()
        updated = re.sub(r"\s+", " ", updated)
        if not updated:
            return ack_prefix
        return f"{ack_prefix} {updated}".strip()

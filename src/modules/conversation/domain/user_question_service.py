"""识别需要优先答疑的用户问题。"""

from __future__ import annotations

import re

from src.modules.conversation.domain.collection_concern_detector import (
    CollectionConcernDetector,
    CollectionConcernMatch,
)


class UserQuestionService:
    """判断用户当前是否在表达常见疑问或顾虑。"""

    QUESTION_PATTERNS = (
        r"收费",
        r"怎么收费",
        r"多少钱",
        r"定制服务",
        r"门店",
        r"线下门店",
        r"实体店",
        r"到店",
        r"线下见面",
        r"在哪里",
        r"位置在哪",
        r"具体在哪",
        r"具体位置",
        r"门店地址",
        r"怎么匹配",
        r"匹配流程",
        r"怎么牵线",
        r"怎么联系",
        r"能加对方微信",
        r"能直接联系",
        r"要对方照片",
        r"发照片",
        r"成功率",
        r"脱单率",
        r"中介吗",
        r"你们是做什么的",
        r"靠谱吗",
        r"真的假的",
        r"安全吗",
        r"隐私",
        r"泄露",
        r"保密",
        r"为啥要留电话",
        r"为什么要留电话",
        r"留电话干嘛",
        r"要电话干嘛",
        r"电话用途",
        r"电话有什么用",
        r"为啥要留微信",
        r"为什么要留微信",
        r"留微信干嘛",
        r"微信用途",
        r"没看懂",
        r"看不懂",
        r"听不懂",
        r"啥意思",
        r"什么意思",
        r"解释下",
        r"解释一下",
        r"只想要",
        r"就要他",
        r"就要她",
        r"就想跟",
        r"指定",
        r"这个人",
        r"这个男生",
        r"这个女生",
        r"暂时不想结婚",
        r"着急结婚的不要",
        r"不要着急结婚",
        r"节奏一致",
    )

    FAQ_RESPONSE_RULES = (
        (
            "specific_target",
            (r"只想要", r"就要他", r"就要她", r"就想跟", r"指定", r"这个人", r"这个男生", r"这个女生"),
            (
                "我明白，你现在就是更看中这一个人。不过感情还是双向的，能不能继续也得看双方想法；如果最后不合适，我们再聊别的方向。",
                "你现在更偏向这一个人，这个我知道了。不过后面能不能继续，还是得看双方意愿；如果不合适，我们再看别的合适方向。",
                "你是先看中这一个人，对吧。不过后面能不能继续还得看双方感觉；如果不合适，我们再顺着你的想法往下聊。",
            ),
        ),
        (
            "marriage_pace",
            (r"暂时不想结婚", r"着急结婚的不要", r"不要着急结婚", r"节奏一致"),
            (
                "我明白，你现在更在意的是相处节奏别太赶。你更适合那种节奏一致、别一上来就催着定下来的人。",
                "好，这个点我记住了。你更希望先正常相处、慢慢了解，不想碰那种一上来就把结婚节奏压得很紧的人。",
                "知道了，你现在更看重的是节奏合拍，不想一开始就被婚姻进度追着走。这个点我听明白了。",
            ),
        ),
        (
            "contact_why",
            (
                r"为啥要留电话",
                r"为什么要留电话",
                r"留电话干嘛",
                r"要电话干嘛",
                r"电话用途",
                r"电话有什么用",
                r"为啥要留微信",
                r"为什么要留微信",
                r"留微信干嘛",
                r"微信用途",
            ),
            (
                "主要是后面要是还想继续聊，能方便找到你，不会拿去乱用。",
                "留联系方式只是为了后面沟通方便一点，不是一留就马上有人来打扰你。",
                "留个联系方式主要是怕后面聊到一半断掉，怎么往下聊也会先跟你说清楚。",
            ),
        ),
        (
            "info_collection_why",
            CollectionConcernDetector.DIRECT_PATTERNS,
            (
                "我先跟你说清楚，这些资料主要是为了后面沟通时别理解偏了，不是拿去乱登记的。",
                "问这些不是想查你户口，是想先把你的基本情况弄明白一点，后面聊起来会更顺。",
                "这些信息只是用来判断怎么顺着你的情况往下聊，不会因为你一说就拿去乱用。",
            ),
        ),
        (
            "clarification",
            (r"没看懂", r"看不懂", r"听不懂", r"啥意思", r"什么意思", r"解释下", r"解释一下"),
            (
                "我换个直白说法：我说的“匹配点”就是你在意的几个条件，比如年龄范围、城市、工作节奏、是否单身和相处感觉。",
                "简单说，“匹配点”就是我们用来筛人的关键条件，比如同城、年龄段、工作和你更看重的性格点。",
                "你这个问题很好理解：所谓“匹配点”，就是你觉得重要的标准，比如城市、年龄、工作状态和相处舒适度。",
            ),
        ),
        (
            "mediator",
            (r"中介吗", r"你们是做什么的"),
            (
                "我们这边是做同城脱单匹配的，主要帮单身男女牵线认识。",
                "我们是做同城脱单匹配的，不是那种随便推人的中介，会先把你的情况和想法聊清楚，再看后面怎么安排。",
                "我们主要是帮单身男女做脱单牵线的，前面会先了解清楚你的情况，再往合适的方向聊。",
            ),
        ),
        (
            "fee",
            (r"怎么收费", r"收费", r"多少钱", r"定制服务"),
            (
                "咱们基础匹配这部分不收费，后面如果真有你想进一步了解的，再看要不要选定制服务就行。",
                "基础这部分是免费的，定制服务是可选项，不想做也完全没关系。",
                "先放心，普通匹配不涉及收费；后面的定制部分按你自己的意愿来，不会硬推。",
                "是否收费主要看你后面要不要选定制服务，基础匹配这部分先不收费，一切按你自己的意愿来。",
            ),
        ),
        (
            "store_location",
            (r"线下门店", r"门店", r"位置在哪", r"在哪里", r"实体店", r"到店", r"线下见面", r"具体在哪", r"具体位置", r"门店地址"),
            (
                "线下门店是有的，深圳这边有门店；如果你不在深圳，后面是否线下沟通要看实际安排，不是现在就把具体门店信息定下来。",
                "深圳这边是有线下门店的，外地这块要看后面实际聊到哪一步再安排，不会现在就直接定到店流程。",
                "可以线下了解，不过具体门店位置和怎么安排，要等前面情况聊得差不多了再往下定。",
            ),
        ),
        (
            "how_match",
            (r"怎么匹配", r"匹配流程", r"怎么牵线"),
            (
                "一般是先把你的基本情况和要求聊清楚，前面先沟通了解情况，再看后面怎么继续推进；合不合适你都可以自己决定。",
                "通常会先了解你的情况和偏好，前面先线上聊清楚，后面怎么安排再结合实际情况往下走。",
                "大致就是先把你这边的情况和想法摸清，再看有没有适合继续了解的，不是上来就直接往下推。",
            ),
        ),
        (
            "contact_exchange",
            (r"能加对方微信", r"能直接联系", r"直接加对方微信", r"直接加微信", r"可以直接加"),
            (
                "这个不会一上来就直接互相留微信，前面会先把双方情况沟通清楚；后面如果真要继续，也会先和你确认。",
                "一般不会现在就直接互相加联系方式，前面还是先沟通和确认；后面如果双方都愿意，再决定怎么继续。",
                "不会一开始就直接给你对方的联系方式，前面会先把沟通情况和双方意愿确认清楚，再往后安排。",
            ),
        ),
        (
            "photo",
            (r"要对方照片", r"发照片", r"先看照片"),
            (
                "照片这类内容当前不会往下给，前面还是先看双方沟通和意愿，也得顾及隐私边界。",
                "这类信息不会一上来就直接给，主要还是先保护双方隐私，避免太冒进。",
                "照片不是当前阶段直接发的内容，前面会先把基本情况和想法聊清楚。",
            ),
        ),
        (
            "success_rate",
            (r"成功率", r"脱单率"),
            (
                "这种事还是得看双方是不是聊得来，不过我们会尽量把不合适的情况提前过滤掉。",
                "有聊得不错的情况，但结果还是看双方相处和沟通状态。",
                "这种事没有谁能提前说满，不过会尽量帮你减少无效来回。",
            ),
        ),
        (
            "service_area",
            (r"服务哪些地区", r"服务范围", r"哪些地区"),
            (
                "目前主要做深圳及周边地区，也覆盖部分合作城市范围。",
                "目前以深圳和周边为主，其他城市看合作服务点安排。",
                "服务范围主要在深圳及周边，部分城市也能覆盖到。",
            ),
        ),
        (
            "timeline",
            (r"多久能找到", r"时间", r"周期"),
            (
                "这块没有固定时长，主要还是看资料情况和后续沟通节奏。",
                "时间不好先给你说死，一般会先看情况是否合适，再往后沟通。",
                "周期会因人而异，这边更适合先把你的情况了解清楚。",
            ),
        ),
        (
            "reliable",
            (r"靠谱吗", r"真的假的", r"安全吗"),
            (
                "你这个顾虑很正常，我们会先把信息和沟通节奏把住，安全和靠谱会放在前面。",
                "这个担心可以理解，我们会先做基本把关，不会随便往下推。",
                "可以理解你会担心，我们不会不加判断地乱往下接，这点你可以放心一些。",
            ),
        ),
        (
            "privacy",
            (r"隐私", r"泄露", r"保密", r"会不会泄露", r"会泄露吗"),
            (
                "这块你可以放心，资料和联系方式只会放在当前沟通里用，不会对外乱传，我们会尽量保护你的隐私。",
                "隐私这块会做保护，联系方式也不会随便泄露出去。",
                "我们会把隐私和信息安全放在前面，资料不会拿去乱用，这点你可以放心。",
            ),
        ),
    )

    FAQ_REPEAT_FOLLOWUPS = (
        "我理解你会反复确认，这很正常。你更担心价格、流程，还是隐私安全？",
        "你这个点我明白。你最在意的是费用透明，还是匹配后的沟通安排？",
        "可以多问几次没关系。你更担心哪块，我按那块展开给你说清楚。",
    )

    SEMANTIC_HINTS = {
        "fee": ("收费", "费用", "价格", "价位", "多少钱", "要钱", "付费", "收费标准", "收费方式", "怎么收", "咋收"),
        "store_location": ("门店", "线下", "地址", "位置", "在哪", "哪里", "到店", "实体店", "定位"),
        "how_match": ("匹配", "流程", "牵线", "怎么安排", "怎么找", "怎么做", "怎么介绍"),
        "contact_exchange": ("加微信", "直接联系", "直接加", "互换联系方式", "能加", "对方微信", "直接加对方"),
        "contact_why": ("为什么留电话", "为啥留电话", "留电话干嘛", "电话用途", "为什么留微信", "留微信干嘛", "微信用途"),
        "clarification": ("没看懂", "看不懂", "听不懂", "啥意思", "什么意思", "解释下", "解释一下"),
        "specific_target": ("只想要", "就要他", "就要她", "指定", "这个人", "这个男生", "这个女生"),
        "marriage_pace": ("暂时不想结婚", "着急结婚的不要", "不要着急结婚", "节奏一致", "慢慢来"),
        "photo": ("照片", "相片", "头像", "先看图", "先看照片"),
        "success_rate": ("成功率", "脱单率", "成功案例", "成了多少"),
        "service_area": ("服务范围", "覆盖", "地区", "哪些城市", "服务哪些"),
        "timeline": ("多久", "多长时间", "周期", "几天", "几周", "什么时候"),
        "mediator": ("中介", "你们是做什么", "你们干嘛的"),
        "reliable": ("靠谱", "真的假的", "安全", "可信吗", "真实吗"),
        "privacy": ("隐私", "泄露", "保密", "隐私安全", "信息安全"),
    }
    QUESTION_CUES = ("吗", "么", "?", "？", "咋", "怎么", "如何", "能不能", "可不可以", "多少")
    TIMELINE_STRONG_PATTERNS = (
        r"多久.*联系我",
        r"什么时候.*联系我",
        r"多久.*有消息",
        r"什么时候.*有消息",
        r"多久.*通知我",
        r"什么时候.*通知我",
        r"多久.*进展",
        r"什么时候.*进展",
        r"后面.*多久",
        r"后续.*多久",
        r"一般.*多久",
        r"大概.*多久",
        r"等通知",
        r"等消息",
        r"多久会联系",
        r"什么时候会联系",
    )

    def __init__(self) -> None:
        self.collection_concern_detector = CollectionConcernDetector()

    def is_priority_question(self, text: str) -> bool:
        """命中常见业务疑问时，本轮先答疑。"""
        return self.detect_quick_faq_intent(text) is not None

    def detect_collection_concern(
        self,
        text: str,
        *,
        last_asked_field: str = "",
        last_response: str = "",
        recent_responses: tuple[str, ...] | list[str] | None = None,
        in_contact_flow: bool = False,
    ) -> CollectionConcernMatch | None:
        return self.collection_concern_detector.detect(
            message=text,
            last_asked_field=last_asked_field,
            last_response=last_response,
            recent_responses=recent_responses,
            in_contact_flow=in_contact_flow,
        )

    def detect_quick_faq_intent(self, text: str) -> str | None:
        """识别 FAQ 意图，命中返回 intent id。"""
        message = (text or "").strip().lower()
        if not message:
            return None

        if any(re.search(pattern, message) for pattern in self.TIMELINE_STRONG_PATTERNS):
            return "timeline"

        for intent, patterns, _ in self.FAQ_RESPONSE_RULES:
            if intent == "info_collection_why":
                continue
            if any(re.search(pattern, message) for pattern in patterns):
                return intent

        concern_match = self.detect_collection_concern(text)
        if concern_match:
            return concern_match.intent

        has_question_shape = any(cue in message for cue in self.QUESTION_CUES)
        scored: dict[str, int] = {}
        for intent, hints in self.SEMANTIC_HINTS.items():
            score = sum(1 for hint in hints if hint in message)
            if score > 0:
                scored[intent] = score

        if not scored:
            return None

        best_intent = max(scored, key=scored.get)
        best_score = scored[best_intent]
        if best_score >= 2 or (best_score >= 1 and has_question_shape):
            return best_intent
        return None

    def get_quick_faq_response(
        self,
        text: str,
        *,
        repeat_count: int = 1,
        recent_responses: tuple[str, ...] | list[str] | None = None,
    ) -> str | None:
        """
        对标准 FAQ 问法走快速直出，减少该类轮次的模型耗时。
        未命中时返回 None，保持原有 AI 流程。
        """
        intent = self.detect_quick_faq_intent(text)
        if not intent:
            return None

        recent = set(recent_responses or [])
        for intent_id, _, responses in self.FAQ_RESPONSE_RULES:
            if intent_id != intent:
                continue
            candidates = [r for r in responses if r not in recent]
            if not candidates:
                candidates = list(responses)

            if repeat_count >= 3:
                if intent == "clarification":
                    idx = (repeat_count - 1) % len(candidates)
                    return candidates[idx]
                followup_candidates = [r for r in self.FAQ_REPEAT_FOLLOWUPS if r not in recent]
                if not followup_candidates:
                    followup_candidates = list(self.FAQ_REPEAT_FOLLOWUPS)
                followup_idx = (repeat_count - 3) % len(followup_candidates)
                return followup_candidates[followup_idx]

            idx = (repeat_count - 1) % len(candidates)
            return candidates[idx]
        return None

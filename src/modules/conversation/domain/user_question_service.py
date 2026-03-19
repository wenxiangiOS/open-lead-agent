"""识别需要优先答疑的用户问题。"""

from __future__ import annotations

import re


class UserQuestionService:
    """判断用户当前是否在表达常见疑问或顾虑。"""

    QUESTION_PATTERNS = (
        r'收费',
        r'怎么收费',
        r'多少钱',
        r'定制服务',
        r'门店',
        r'线下门店',
        r'在哪里',
        r'位置在哪',
        r'怎么匹配',
        r'匹配流程',
        r'怎么牵线',
        r'怎么联系',
        r'能加对方微信',
        r'能直接联系',
        r'要对方照片',
        r'发照片',
        r'成功率',
        r'脱单率',
        r'中介吗',
        r'你们是做什么的',
        r'靠谱吗',
        r'真的假的',
        r'安全吗',
        r'隐私',
        r'泄露',
        r'保密',
        r'为啥要留电话',
        r'为什么要留电话',
        r'留电话干嘛',
        r'要电话干嘛',
        r'电话用途',
        r'电话有什么用',
        r'为啥要留微信',
        r'为什么要留微信',
        r'留微信干嘛',
        r'微信用途',
    )

    FAQ_RESPONSE_RULES = (
        (
            "contact_why",
            (
                r'为啥要留电话', r'为什么要留电话', r'留电话干嘛', r'要电话干嘛', r'电话用途', r'电话有什么用',
                r'为啥要留微信', r'为什么要留微信', r'留微信干嘛', r'微信用途',
            ),
            (
                "主要是为了后续有合适人选时能及时联系到你，不会拿去做营销骚扰，你可以放心。",
                "这个联系方式只用于匹配进展通知和约时间沟通，不会随便打扰你。",
                "留联系方式是为了后续对接更顺畅，只有匹配到合适对象时才会联系你。",
            ),
        ),
        (
            "mediator",
            (r'中介吗', r'你们是做什么的'),
            (
                "我们是同城脱单联盟，主要做真人牵线匹配，不是那种撒网式中介。你要是还有顾虑也可以继续问我。",
                "我们更像真人牵线服务，不是广撒网中介。你担心哪块我可以直接讲清楚。",
                "我们是做真实资料匹配和牵线的，不走中介那套流水线。你还有顾虑可以继续问我。",
            ),
        ),
        (
            "fee",
            (r'怎么收费', r'收费', r'多少钱', r'定制服务'),
            (
                "咱们基础匹配是免费的，定制服务是可选项，不合适你也可以直接拒绝。你要是还有顾虑也可以继续问我。",
                "基础牵线这块不收费，定制服务是你自愿选，不想做也完全没关系。",
                "先放心，普通匹配是免费的；定制部分按你意愿来，不会强推。",
            ),
        ),
        (
            "store_location",
            (r'线下门店', r'门店', r'位置在哪', r'在哪里'),
            (
                "我们有深圳门店，其他城市也有合作服务点；匹配到合适阶段会给你发具体定位。你要是还有顾虑也可以继续问我。",
                "深圳这边有线下门店，外地是合作服务点，到了合适阶段会发你具体地址。",
                "线下点位有的，深圳门店比较稳定，其他城市按合作点安排。",
            ),
        ),
        (
            "how_match",
            (r'怎么匹配', r'匹配流程', r'怎么牵线'),
            (
                "流程是先线上了解并做匹配筛选，双方聊得来再安排线下见面，这样更稳妥。你要是还有顾虑也可以继续问我。",
                "我们先线上把关资料和偏好，匹配到合适的人再安排线下见面。",
                "一般先做线上匹配，确认双方都愿意后再推进见面，节奏会更稳。",
            ),
        ),
        (
            "contact_exchange",
            (r'能加对方微信', r'能直接联系'),
            (
                "一般是双方都觉得合适后，由牵线同事安排互换联系方式，不会一上来就直接对接。你要是还有顾虑也可以继续问我。",
                "通常会先做双方意愿确认，再由牵线同事安排互换联系方式。",
                "不是一开始就直接互加，先确认匹配度再安排互换会更安全。",
            ),
        ),
        (
            "photo",
            (r'要对方照片', r'发照片', r'先看照片'),
            (
                "照片通常是双方都觉得合适后再互换，这样更尊重彼此隐私。你要是还有顾虑也可以继续问我。",
                "照片一般会在双方都有继续意愿后再互换，主要是保护隐私。",
                "先看资料匹配度，合适后再互换照片会更稳妥一些。",
            ),
        ),
        (
            "success_rate",
            (r'成功率', r'脱单率'),
            (
                "我们做过不少成功牵线案例，但脱单是双向选择，会尽量帮你提高匹配契合度。你要是还有顾虑也可以继续问我。",
                "这边有不少真实牵线案例，不过结果还是看双方匹配和沟通状态。",
                "成功案例是有的，我们会尽量把契合度做高，减少无效接触。",
            ),
        ),
        (
            "service_area",
            (r'服务哪些地区', r'服务范围', r'哪些地区'),
            (
                "目前主要做深圳及周边地区，也覆盖部分合作城市范围。你要是还有顾虑也可以继续问我。",
                "目前以深圳和周边为主，其他城市看合作服务点安排。",
                "服务范围主要在深圳及周边，部分城市也能覆盖到。",
            ),
        ),
        (
            "timeline",
            (r'多久能找到', r'时间', r'周期'),
            (
                "匹配周期会因人而异，一般先看资料契合度和双方沟通节奏。你要是还有顾虑也可以继续问我。",
                "时间这块没有绝对值，通常先看匹配度和双方反馈速度。",
                "周期会跟你的条件和偏好有关，我们会尽量帮你缩短匹配时间。",
            ),
        ),
        (
            "reliable",
            (r'靠谱吗', r'真的假的', r'安全吗'),
            (
                "这块可以放心，我们是做真人审核和牵线流程把控的，整体会以安全和靠谱为优先。你要是还有顾虑也可以继续问我。",
                "你这个顾虑很正常，我们这边有人审和流程把关，安全和真实性是优先项。",
                "可以理解你会担心，我们是按真人审核和牵线流程来做，不是随便对接。",
            ),
        ),
        (
            "privacy",
            (r'隐私', r'泄露', r'保密', r'会不会泄露', r'会泄露吗'),
            (
                "这块你可以放心，资料和联系方式只用于匹配与牵线，不会对外乱传，我们会尽量保护你的隐私。",
                "隐私这块会做保护，联系方式只在匹配推进时用于对接，不会随便泄露出去。",
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
        "store_location": ("门店", "线下", "地址", "位置", "在哪", "哪里", "到店"),
        "how_match": ("匹配", "流程", "牵线", "怎么安排", "怎么找", "怎么做"),
        "contact_exchange": ("加微信", "直接联系", "直接加", "互换联系方式", "能加"),
        "contact_why": ("为什么留电话", "为啥留电话", "留电话干嘛", "电话用途", "为什么留微信", "留微信干嘛", "微信用途"),
        "photo": ("照片", "相片", "头像", "先看图", "先看照片"),
        "success_rate": ("成功率", "脱单率", "成功案例", "成了多少"),
        "service_area": ("服务范围", "覆盖", "地区", "哪些城市", "服务哪些"),
        "timeline": ("多久", "多长时间", "周期", "几天", "几周", "什么时候"),
        "mediator": ("中介", "你们是做什么", "你们干嘛的"),
        "reliable": ("靠谱", "真的假的", "安全", "可信吗", "真实吗"),
        "privacy": ("隐私", "泄露", "保密", "隐私安全", "信息安全"),
    }
    QUESTION_CUES = ("吗", "么", "?", "？", "咋", "怎么", "如何", "能不能", "可不可以", "多少")

    def is_priority_question(self, text: str) -> bool:
        """命中常见业务疑问时，本轮先答疑。"""
        return self.detect_quick_faq_intent(text) is not None

    def detect_quick_faq_intent(self, text: str) -> str | None:
        """识别 FAQ 意图，命中返回 intent id。"""
        message = (text or "").strip().lower()
        if not message:
            return None

        for intent, patterns, _ in self.FAQ_RESPONSE_RULES:
            if any(re.search(pattern, message) for pattern in patterns):
                return intent

        # 二层语义兜底：规则未命中时，基于同义短语 + 疑问线索判断 FAQ 意图。
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
        # 至少命中2个语义线索，或命中1个线索且有明确问句形态。
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
                # 第三次及以上使用“承接+分流顾虑”轮转，并尽量避开最近重复。
                followup_candidates = [r for r in self.FAQ_REPEAT_FOLLOWUPS if r not in recent]
                if not followup_candidates:
                    followup_candidates = list(self.FAQ_REPEAT_FOLLOWUPS)
                followup_idx = (repeat_count - 3) % len(followup_candidates)
                return followup_candidates[followup_idx]

            # 稳定轮转，避免同一会话随机撞到同一句。
            idx = (repeat_count - 1) % len(candidates)
            return candidates[idx]
        return None

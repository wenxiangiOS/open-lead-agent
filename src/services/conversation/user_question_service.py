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
    )

    FAQ_RESPONSE_RULES = (
        (
            (r'中介吗', r'你们是做什么的'),
            "我们是同城脱单联盟，主要做真人牵线匹配，不是那种撒网式中介。你要是还有顾虑也可以继续问我。",
        ),
        (
            (r'怎么收费', r'收费', r'多少钱', r'定制服务'),
            "咱们基础匹配是免费的，定制服务是可选项，不合适你也可以直接拒绝。你要是还有顾虑也可以继续问我。",
        ),
        (
            (r'线下门店', r'门店', r'位置在哪', r'在哪里'),
            "我们有深圳门店，其他城市也有合作服务点；匹配到合适阶段会给你发具体定位。你要是还有顾虑也可以继续问我。",
        ),
        (
            (r'怎么匹配', r'匹配流程', r'怎么牵线'),
            "流程是先线上了解并做匹配筛选，双方聊得来再安排线下见面，这样更稳妥。你要是还有顾虑也可以继续问我。",
        ),
        (
            (r'能加对方微信', r'能直接联系'),
            "一般是双方都觉得合适后，由牵线同事安排互换联系方式，不会一上来就直接对接。你要是还有顾虑也可以继续问我。",
        ),
        (
            (r'要对方照片', r'发照片', r'先看照片'),
            "照片通常是双方都觉得合适后再互换，这样更尊重彼此隐私。你要是还有顾虑也可以继续问我。",
        ),
        (
            (r'成功率', r'脱单率'),
            "我们做过不少成功牵线案例，但脱单是双向选择，会尽量帮你提高匹配契合度。你要是还有顾虑也可以继续问我。",
        ),
        (
            (r'服务哪些地区', r'服务范围', r'哪些地区'),
            "目前主要做深圳及周边地区，也覆盖部分合作城市范围。你要是还有顾虑也可以继续问我。",
        ),
        (
            (r'多久能找到', r'时间', r'周期'),
            "匹配周期会因人而异，一般先看资料契合度和双方沟通节奏。你要是还有顾虑也可以继续问我。",
        ),
        (
            (r'靠谱吗', r'真的假的', r'安全吗'),
            "这块可以放心，我们是做真人审核和牵线流程把控的，整体会以安全和靠谱为优先。你要是还有顾虑也可以继续问我。",
        ),
    )

    def is_priority_question(self, text: str) -> bool:
        """命中常见业务疑问时，本轮先答疑。"""
        message = (text or "").strip().lower()
        if not message:
            return False

        return any(re.search(pattern, message) for pattern in self.QUESTION_PATTERNS)

    def get_quick_faq_response(self, text: str) -> str | None:
        """
        对标准 FAQ 问法走快速直出，减少该类轮次的模型耗时。
        未命中时返回 None，保持原有 AI 流程。
        """
        message = (text or "").strip().lower()
        if not message:
            return None

        for patterns, response in self.FAQ_RESPONSE_RULES:
            if any(re.search(pattern, message) for pattern in patterns):
                return response
        return None

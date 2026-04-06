import random
from typing import Optional


class ChatServiceBridgeTextService:
    @staticmethod
    def build_bridge_back_prefix(last_side_topic_type: Optional[str]) -> str:
        if not last_side_topic_type:
            return ""

        bridge_variants = {
            "faq": [
                "这块先这样。",
                "这个先放一边。",
                "照片这块先不往下走。",
                "联系方式这块先这样。",
            ],
            "boundary": [
                "这块先不勉强。",
                "这个先放一边。",
                "这块先这样。",
            ],
            "complaint": [
                "嗯，那我们换个节奏。",
                "好，那我们先不聊资料。",
            ],
            "risk": [
                "这块先不聊了。",
                "这个话题先这样。",
            ],
        }
        variants = bridge_variants.get(last_side_topic_type, ["这块先这样。"])
        return random.choice(variants)

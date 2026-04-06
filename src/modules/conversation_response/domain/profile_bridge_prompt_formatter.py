from __future__ import annotations


class ProfileBridgePromptFormatter:
    """负责把 profile bridge 约束序列化成模型提示片段。"""

    @staticmethod
    def build_generation_instruction(
        *,
        summary: str,
        main_prompt_label: str,
        side_prompt_labels: list[str],
    ) -> str:
        required_fields = "；".join([main_prompt_label, *side_prompt_labels])
        return (
            "【当前轮生成模式：PROFILE_BRIDGE（高优先级）】\n"
            "这条模式优先级高于通用的泛化融合追问风格。\n"
            f"用户这轮刚提供了这些信息：{summary}。\n"
            "本轮请顺着这些已给信息继续聊，不要先机械复述资料，也不要脱离上下文直接裸问。\n"
            f"本轮必须同时问到这些内容：{required_fields}。\n"
            "要求：\n"
            f"1. 以“{main_prompt_label}”为主问题，并把“{'；'.join(side_prompt_labels)}”自然带在同一句或紧邻句里一起问。\n"
            "2. 问法必须利用用户刚给的信息做桥接，比如顺着城市或当前状态继续聊，但不要写成固定模板。\n"
            "3. 如果回复里没有利用上面至少一项刚给信息，就算本轮生成不合格。\n"
            "4. 不要漏掉必须一起带出的相近字段，不要只问主字段。\n"
            "5. 保持口语化、像顺着聊下去，优先 1 句完成，不要列表，不要复述全部资料。\n"
        )

    @staticmethod
    def prepend_instruction(prompt: str, bridge_instruction: str) -> str:
        if not bridge_instruction:
            return prompt
        return f"{bridge_instruction.strip()}\n\n{prompt}"

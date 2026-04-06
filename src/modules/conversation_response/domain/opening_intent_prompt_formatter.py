from __future__ import annotations


class OpeningIntentPromptFormatter:
    """负责构造开场意图检测的模型提示片段。"""

    @staticmethod
    def build_detection_instruction() -> str:
        instruction = """
【开场意图识别】
如果当前仍处于开场前两轮，请先判断这句用户输入的开场意图，并在回复最前面输出：
<opening_intent>{"intent":"意图名","confidence":0.00,"secondary_intent":null}</opening_intent>

可选意图：
- opening_greeting
- opening_light_consult
- explicit_matchmaking_opening
- low_pressure_opening
- opening_faq
- opening_spam_or_promo
- opening_clarify
- opening_profile_provided
- opening_boundary_or_contact_refusal
- opening_mixed_intent
- opening_emotional_or_defensive
- opening_reverse_question
- opening_proxy_inquiry
- opening_eligibility_concern
- opening_resource_request
- opening_ambiguous_short
- opening_test_or_playful
- opening_hybrid_promo_real

要求：
1. 只输出一个主意图；如果确实混合，再给 secondary_intent。
2. 输出完 <opening_intent> 后，紧接着输出给用户看的自然回复。
3. 如果是 low_pressure_opening，不要直接追问 sex/age/location/education/occupation/contact。
4. 如果是 opening_faq，先答问题，不要直接切资料。
5. 如果是 opening_boundary_or_contact_refusal，先接住边界，不要推进电话微信或资料。
"""
        return instruction.strip()

    @staticmethod
    def prepend_instruction(prompt: str, instruction: str) -> str:
        if not instruction:
            return prompt
        return f"{instruction.strip()}\n\n{prompt}"

"""Text generator for creating personalized responses"""

import random
from typing import Dict, List, Any, Optional
from src.models.personality import PersonalityProfile


class TextGenerator:
    """Generate text with personality traits"""

    def __init__(self):
        """Initialize text generator"""
        pass

    def generate_greeting(
        self,
        personality: PersonalityProfile,
        user_name: str = "用户"
    ) -> str:
        """Generate personalized greeting"""
        greetings = [
            f"你好{user_name}！我是{personality.name}，很高兴认识你！",
            f"嗨，{user_name}！我是{personality.name}，你的专属红娘～",
            f"{user_name}你好！我是{personality.name}，今天心情怎么样？",
        ]

        greeting = random.choice(greetings)
        catchphrases = getattr(personality, "catchphrases", None) or []
        if catchphrases:
            greeting = f"{random.choice(catchphrases)}，{greeting}"

        try:
            emotion = personality.generate_emotion_emoji()
        except Exception:
            emotion = random.choice(["😊", "😂", "😅"])
        return f"{greeting} {emotion}"

    def generate_response_with_context(
        self,
        personality: PersonalityProfile,
        user_message: str,
        context: Dict[str, Any]
    ) -> str:
        """Generate response with conversation context"""
        # Get response style based on personality
        style = personality.get_response_style()

        # Base response
        base_response = self._generate_base_response(personality, user_message)

        # Add personality traits
        enhanced_response = base_response

        # Add fillers if personality requires
        if personality.should_add_filler():
            fillers = personality.get_speech_pattern("fillers")
            enhanced_response = f"{random.choice(fillers)}，{enhanced_response}"

        # Add catchphrase if personality requires
        if personality.should_use_catchphrase():
            catchphrase = personality.get_random_catchphrase()
            enhanced_response = f"{catchphrase}，{enhanced_response}"

        # Add emotion emoji if personality requires
        if personality.should_add_emotion():
            emoji = personality.generate_emotion_emoji()
            enhanced_response += f" {emoji}"

        return enhanced_response

    def _generate_base_response(
        self,
        personality: PersonalityProfile,
        user_message: str
    ) -> str:
        """Generate base response"""
        # Simple response generation based on message keywords
        message_lower = user_message.lower()

        if any(word in message_lower for word in ["你好", "hi", "hello", "嗨"]):
            return "你好！很高兴能和你聊天！"
        elif any(word in message_lower for word in ["找对象", "脱单", "交友"]):
            return "找对象是件很美好的事呢！你想找个什么样的伴侣？"
        elif any(word in message_lower for word in ["多大了", "年龄", "几岁"]):
            return "年龄不是最重要的，重要的是两个人是否合得来！"
        elif any(word in message_lower for word in ["做什么", "职业", "工作"]):
            return "工作是为了更好地生活，但不要让工作占据你所有的时间哦！"
        elif any(word in message_lower for word in ["建议", "推荐", "介绍"]):
            return "我很乐意给你一些建议，你觉得怎么样？"
        elif any(word in message_lower for word in ["谢谢", "感谢"]):
            return "不客气！能帮到我就好！"
        else:
            return "我在认真地听你说呢，请继续讲吧！"

    def add_personality_filler_words(
        self,
        personality: PersonalityProfile,
        text: str
    ) -> str:
        """Add personality-specific filler words"""
        fillers = personality.get_speech_pattern("fillers")
        if not fillers:
            return text
        return f"{random.choice(fillers)}，{text}"

    def add_emotion_emoji(
        self,
        personality: PersonalityProfile,
        text: str,
        emotion: str = "neutral"
    ) -> str:
        """Add emotion emoji to text"""
        emoji = personality.generate_emotion_emoji()
        return f"{text} {emoji}"

    def generate_catchphrase_response(
        self,
        personality: PersonalityProfile,
        catchphrase: str,
        context: str
    ) -> str:
        """Generate response with catchphrase"""
        response_patterns = [
            f"{catchphrase}，{context}",
            f"{context}，{catchphrase}。",
            f"{catchphrase}！{context}",
        ]

        return random.choice(response_patterns)

    def generate_professional_advice(
        self,
        topic: str,
        user_id: str
    ) -> str:
        """Generate professional advice"""
        advice_templates = [
            f"关于{topic}，我建议你可以从以下几个方面考虑：",
            f"对于{topic}这个问题，我的建议是：",
            f"在{topic}方面，我想分享一些经验：",
            f"关于{topic}，我有一些建议想和你分享：",
        ]

        template = random.choice(advice_templates)

        # Add general advice
        advice_parts = [
            "真诚最重要",
            "相互尊重是基础",
            "沟通要坦诚",
            "要有耐心",
            "保持自我",
            "不要太心急",
            "了解对方",
            "尊重差异",
        ]

        # Select 2-3 random advice points
        selected_advice = random.sample(advice_parts, k=random.randint(2, 3))

        # Build complete advice
        full_advice = f"{template}\n"
        for i, advice in enumerate(selected_advice, 1):
            full_advice += f"{i}. {advice}\n"

        full_advice += "希望这些建议对你有帮助！"

        return full_advice

    def generate_light_hearted_response(
        self,
        personality: PersonalityProfile,
        context: str
    ) -> str:
        """Generate light-hearted response"""
        light_hearted_templates = [
            f"{context}，哈哈哈，你说得对！",
            f"{context}，确实如此呢！😄",
            f"{context}，我也是这么想的！",
            f"{context}，你说得很有道理！",
            f"{context}，哈哈，有意思！",
        ]

        # Add personality traits
        if personality.should_add_emotion():
            template = random.choice(light_hearted_templates)
            emotion = personality.generate_emotion_emoji()
            return f"{template} {emotion}"

        return random.choice(light_hearted_templates)

    def generate_follow_up_question(
        self,
        personality: PersonalityProfile,
        context: str
    ) -> str:
        """Generate follow-up question"""
        question_templates = [
            f"{context}，那你觉得怎么样呢？",
            f"{context}，你有什么想法吗？",
            f"{context}，能详细说说吗？",
            f"{context}，这确实是个值得思考的问题，你觉得呢？",
            f"{context}，我很想听听你的看法。",
        ]

        # Add personality-specific question style
        traits = getattr(personality, "personality", {}) or {}
        curiosity = traits.get("curiosity", 0.0) if isinstance(traits, dict) else 0.0
        professionalism = traits.get("professionalism", 0.0) if isinstance(traits, dict) else 0.0

        if curiosity > 0.8:
            question_templates.append(f"{context}，这是真的吗？快和我分享分享！")

        if professionalism > 0.8:
            question_templates.append(f"{context}，这很有趣。能具体说说你的经历吗？")

        question = random.choice(question_templates)
        if ("？" not in question) and ("吗" not in question) and ("呢" not in question):
            question = f"{question.rstrip('。')}，你怎么看呢？"
        return question

    def generate_encouragement(
        self,
        personality: PersonalityProfile,
        situation: str
    ) -> str:
        """Generate encouraging message"""
        encouragement_templates = [
            f"{situation}，别灰心，一切都会好起来的！",
            f"{situation}，保持积极的心态，你一定能找到属于自己的幸福！",
            f"{situation}，相信自己，你值得被爱！",
            f"{situation}，加油！美好的事情即将发生！",
            f"{situation}，别担心，一切都会慢慢好起来的！",
        ]

        # Add personality-specific encouragement
        if personality.should_add_emotion():
            template = random.choice(encouragement_templates)
            emotion = personality.generate_emotion_emoji()
            return f"{template} {emotion}"

        return random.choice(encouragement_templates)

    def generate_summary(
        self,
        personality: PersonalityProfile,
        points: List[str]
    ) -> str:
        """Generate summary from key points"""
        if not points:
            return ""

        summary_templates = [
            "总结一下：",
            "总的来说：",
            "简单来说：",
            "主要观点：",
        ]

        template = random.choice(summary_templates)

        summary = f"{template}\n"
        for i, point in enumerate(points, 1):
            summary += f"{i}. {point}\n"

        # Add personality closing
        if personality.should_add_emotion():
            emotion = personality.generate_emotion_emoji()
            summary += f"\n希望这些对你有帮助！{emotion}"
        else:
            summary += "\n希望这些对你有帮助！"

        return summary

    def generate_personalized_response(
        self,
        personality: PersonalityProfile,
        user_message: str,
        user_context: Dict[str, Any]
    ) -> str:
        """Generate fully personalized response"""
        # Analyze user message
        from src.utils.input_analyzer import InputAnalyzer
        analyzer = InputAnalyzer()
        analysis = analyzer.analyze_comprehensive(user_message)

        # Get response based on intent
        intent = analysis["intent"]
        emotion = analysis["emotion"]

        # Generate response based on intent
        if intent == "greeting":
            return self.generate_greeting(personality)
        elif intent == "relationship_seeking":
            return self.generate_professional_advice("找对象", user_context.get("user_id", ""))
        elif intent == "personal_info_request":
            return "我觉得最重要的不是外在条件，而是内在品质和价值观是否匹配。"
        elif intent == "complaint":
            return self.generate_encouragement(personality, "我理解你的感受")
        elif intent == "compliment":
            return "谢谢你的夸奖！我会继续努力的！"
        elif intent == "question_general":
            return self.generate_follow_up_question(personality, user_message)
        elif intent == "request_help":
            return self.generate_professional_advice("情感问题", user_context.get("user_id", ""))
        else:
            return self.generate_light_hearted_response(personality, user_message)

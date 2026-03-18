"""Input analyzer for understanding user intent"""

import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class InputAnalyzer:
    """Analyzer for understanding user input"""

    def __init__(self):
        """Initialize input analyzer"""
        # Intent patterns
        self.intent_patterns = {
            "greeting": [
                r"^(你好|hello|hi|嗨|您好|哈喽|yo|hey)",
                r"(早上好|下午好|晚上好|早安|午安|晚安)",
            ],
            "relationship_seeking": [
                r"(找对象|脱单|交友|相亲|恋爱|约会)",
                r"(想|要|希望).*?(男朋友|女朋友|伴侣)",
                r"(单身|寂寞|孤独|没人陪)",
            ],
            "personal_info_request": [
                r"(多大了|年龄|几岁)",
                r"(做什么的|职业|工作|行业)",
                r"(身高|体重|三围)",
                r"(学历|学校|专业)",
                r"(兴趣|爱好|喜欢)",
            ],
            "complaint": [
                r"(不好|差|糟糕|烂|失望)",
                r"(不懂|不明白|不明白为什么)",
                r"(太|很).*?(慢|复杂|麻烦)",
                r"(不想|不要|别)",
                r"(不满意)",
            ],
            "compliment": [
                r"(好|棒|不错|厉害|厉害了)",
                r"(谢谢|感谢|多谢)",
                r"(喜欢|满意|开心|高兴)",
            ],
            "question_general": [
                r"(怎么|如何|为什么|什么|哪里|什么时候)",
                r"(.*?吗|.*?呢)",
            ],
            "request_help": [
                r"(建议|推荐|介绍|推荐)",
                r"(能|可以|帮我|教我).*?(吗|呢)",
                r"(求|求教|求推荐)",
            ],
        }

        # Keyword patterns for extraction
        self.keyword_patterns = {
            "age_range": [
                r"(\d{1,2})[-~—](\d{1,2})岁",
                r"(\d{1,2})[-~—](\d{1,2})",
                r"(\d{1,2})\+岁",
                r"(\d{1,2})岁以上",
            ],
            "location": [
                r"(北京|上海|广州|深圳|杭州|南京|成都|武汉|西安|天津)",
                r"(广东省|江苏省|浙江省|山东省|河南省|四川省)",
                r"([\u4e00-\u9fa5]{2,}(市|区|省))",
            ],
            "height_requirement": [
                r"(\d{1,3})cm",
                r"(\d{1,3})厘米",
                r"(\d{1,3})cm以上",
                r"(\d{1,3})cm以下",
                r"(\d{1,3})[-~—](\d{1,3})cm",
            ],
            "education": [
                r"(本科|硕士|博士|研究生|专科|高中|中专)",
                r"(大学毕业|在校|学生|学霸)",
            ],
            "occupation": [
                r"(工程师|设计师|医生|律师|教师|程序员)",
                r"(IT|互联网|金融|教育|医疗|法律)",
            ],
            "interests": [
                r"(电影|电视剧|综艺|动漫)",
                r"(音乐|唱歌|乐器|舞蹈)",
                r"(运动|健身|跑步|篮球|足球)",
                r"(旅行|旅游|摄影|美食)",
                r"(阅读|看书|学习|写作)",
                r"(游戏|电竞|动漫|二次元)",
            ],
        }

        # Emotion detection patterns
        self.emotion_patterns = {
            "happy": [
                r"(开心|高兴|快乐|愉快|兴奋|激动|喜悦)",
                r"(棒|好|赞|不错|厉害|完美)",
                r"(哈|呵|哈哈|呵呵|嘻嘻|嘿嘿)",
            ],
            "sad": [
                r"(难过|伤心|沮丧|失望|郁闷|不开心)",
                r"(哭|流泪|哭泣|痛苦)",
                r"(呜|呜呜|555|呜呜呜)",
            ],
            "angry": [
                r"(生气|愤怒|恼火|气愤|烦躁)",
                r"(烦|讨厌|鄙视|垃圾)",
                r"(怒|哼|切|靠)",
            ],
            "anxious": [
                r"(焦虑|担心|紧张|不安|着急)",
                r"(害怕|恐惧|担心|怕)",
            ],
            "confused": [
                r"(不明白|不懂|不清楚|疑惑)",
                r"(为什么|怎么|如何)",
            ],
        }

    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze text for intent and confidence"""
        if not text:
            return {"intent": "unknown", "confidence": 0.0}

        text_lower = text.lower()

        # Check each intent pattern
        best_intent = "unknown"
        best_confidence = 0.0

        for intent, patterns in self.intent_patterns.items():
            confidence = 0.0
            match_count = 0

            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    match_count += 1

            if match_count > 0:
                confidence = 0.9 + 0.1 * (match_count / len(patterns))
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_intent = intent

        # Resolve common conflicts by intent priority.
        if best_intent != "unknown":
            priority = {
                "relationship_seeking": 100,
                "personal_info_request": 95,
                "complaint": 90,
                "request_help": 80,
                "greeting": 70,
                "compliment": 60,
                "question_general": 10,
                "unknown": 0,
            }
            winning_intent = best_intent
            winning_score = priority.get(best_intent, 0)
            for intent, patterns in self.intent_patterns.items():
                if intent == best_intent:
                    continue
                if any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in patterns):
                    score = priority.get(intent, 0)
                    if score > winning_score:
                        winning_intent = intent
                        winning_score = score
            best_intent = winning_intent

        return {
            "intent": best_intent,
            "confidence": best_confidence,
            "text": text
        }

    def extract_keywords(self, text: str) -> Dict[str, Any]:
        """Extract keywords and entities from text"""
        keywords: List[str] = []
        extracted_info: Dict[str, Any] = {}

        for token in ["男朋友", "女朋友", "对象", "脱单", "交友", "恋爱"]:
            if token in text:
                keywords.append(token)

        age_range_match = re.search(r"(\d{1,2})\s*[-~—]\s*(\d{1,2})\s*岁?", text)
        if age_range_match:
            start_age, end_age = age_range_match.group(1), age_range_match.group(2)
            extracted_info["age_range"] = f"{start_age}-{end_age}"
            keywords.extend([start_age, end_age])
            if "岁" in text:
                keywords.append("岁")

        height_plus_match = re.search(r"身高\s*(\d{2,3})\s*(?:cm|厘米)?\s*以上", text, re.IGNORECASE)
        if height_plus_match:
            height = height_plus_match.group(1)
            extracted_info["height_requirement"] = f"{height}+"
            keywords.extend(["身高", height])
        else:
            height_match = re.search(r"身高\s*(\d{2,3})", text)
            if height_match:
                height = height_match.group(1)
                extracted_info["height_requirement"] = height
                keywords.extend(["身高", height])

        city_match = re.search(r"(北京|上海|广州|深圳|杭州|南京|成都|武汉|西安|天津)", text)
        if city_match:
            extracted_info["location"] = city_match.group(1)
            keywords.append(city_match.group(1))

        for token in ["工作", "旅游", "旅行", "学历", "本科", "硕士", "博士"]:
            if token in text:
                keywords.append(token)

        # Fallback to existing pattern map when canonical extraction is absent.
        for info_type, patterns in self.keyword_patterns.items():
            if info_type in extracted_info:
                continue
            for pattern in patterns:
                m = re.search(pattern, text, re.IGNORECASE)
                if not m:
                    continue
                if m.lastindex and m.lastindex >= 2 and info_type in {"age_range", "height_requirement"}:
                    extracted_info[info_type] = f"{m.group(1)}-{m.group(2)}"
                    keywords.extend([m.group(1), m.group(2)])
                else:
                    val = m.group(1) if m.lastindex else m.group(0)
                    extracted_info[info_type] = val
                    keywords.append(val)
                break

        unique_keywords: List[str] = []
        seen = set()
        for keyword in keywords:
            if keyword not in seen:
                seen.add(keyword)
                unique_keywords.append(keyword)

        result = {"keywords": unique_keywords, "extracted_info": extracted_info}
        result.update(extracted_info)
        return result

    def detect_emotion(self, text: str) -> str:
        """Detect emotion in text"""
        if not text:
            return "neutral"

        text_lower = text.lower()

        # Check each emotion pattern
        emotion_scores = {}

        for emotion, patterns in self.emotion_patterns.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                score += len(matches)
            emotion_scores[emotion] = score

        # Return emotion with highest score, or neutral if no emotion detected
        if max(emotion_scores.values()) > 0:
            return max(emotion_scores, key=emotion_scores.get)
        else:
            return "neutral"

    def analyze_comprehensive(self, text: str) -> Dict[str, Any]:
        """Perform comprehensive analysis of text"""
        if not text:
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "keywords": [],
                "emotion": "neutral",
                "extracted_info": {}
            }

        # Perform individual analyses
        intent_analysis = self.analyze(text)
        keywords_analysis = self.extract_keywords(text)
        emotion = self.detect_emotion(text)

        # Combine results
        return {
            "intent": intent_analysis["intent"],
            "confidence": intent_analysis["confidence"],
            "keywords": keywords_analysis["keywords"],
            "emotion": emotion,
            "extracted_info": keywords_analysis["extracted_info"],
            "text": text
        }

    def get_intent_suggestions(self, intent: str) -> List[str]:
        """Get response suggestions for given intent"""
        suggestions = {
            "greeting": [
                "你好！很高兴认识你！",
                "嗨！我是小桃子，有什么可以帮你的吗？",
                "你好！今天过得怎么样？"
            ],
            "relationship_seeking": [
                "我很理解你想找对象的心情，能具体说说你的要求吗？",
                "找对象是件很重要的事，我们可以慢慢来聊聊你的需求。",
                "想脱单很正常，让我帮你分析一下你的情况吧。"
            ],
            "personal_info_request": [
                "关于个人信息，我觉得最重要的是真诚和善良。",
                "个人条件很重要，但性格和价值观更重要哦。",
                "我可以分享一些关于交友的看法，你想听吗？"
            ],
            "complaint": [
                "很抱歉让你有不好的体验，我会努力改进的。",
                "我理解你的感受，让我们一起想想解决方案吧。",
                "抱歉让你失望了，有什么具体问题我可以帮你吗？"
            ],
            "compliment": [
                "谢谢你的夸奖！我会继续努力的！",
                "很高兴能帮到你！",
                "谢谢！我会继续提供更好的服务的。"
            ],
            "question_general": [
                "这是个很好的问题，让我想想怎么回答你。",
                "关于这个问题，我有些建议想和你分享。",
                "这个问题值得深入思考，我们可以慢慢聊。"
            ],
            "request_help": [
                "我很乐意帮你！请具体说说你需要什么帮助。",
                "没问题！我会尽我所能为你提供帮助。",
                "我很想帮你解决问题，请告诉我具体情况。"
            ],
            "unknown": [
                "我在学习怎么更好地和你交流，能再具体说说吗？",
                "不太理解你的意思，能换个方式说吗？",
                "我还在学习中，请多包涵。"
            ]
        }

        return suggestions.get(intent, suggestions["unknown"])

    def get_contextual_response(self, text: str, context: Dict[str, Any]) -> str:
        """Get contextual response based on analysis and history"""
        analysis = self.analyze_comprehensive(text)
        intent = analysis["intent"]
        emotion = analysis["emotion"]

        # Get intent suggestions
        suggestions = self.get_intent_suggestions(intent)

        # Select appropriate suggestion based on context
        if context.get("is_new_user", False):
            # For new users, be more welcoming
            return suggestions[0] if suggestions else "你好！我是小桃子！"
        elif emotion == "sad" and intent == "complaint":
            # For sad users, be more empathetic
            return suggestions[1] if len(suggestions) > 1 else "我理解你的感受。"
        else:
            # Use a random suggestion
            import random
            return random.choice(suggestions) if suggestions else "让我想想怎么回答你。"

    def is_confirmation_response(self, text: str) -> bool:
        """
        检测用户输入是否为确认性回复

        Args:
            text: 用户输入文本

        Returns:
            bool: 是否为确认性回复
        """
        text = text.strip().lower()

        # 确认性关键词
        confirmation_keywords = [
            '好', '嗯', '可以', '行', 'ok', '好的', '嗯嗯', '好的呢',
            '行呢', '可以呢', '好呢', '嗯呢', '好哒', '嗯哒', '行哒',
            '可以哒', '好呀', '嗯呀', '可以呀', '行呀', '好哦', '嗯哦',
            '可以哦', '行哦', '好哈', '嗯哈', '可以哈', '行哈', '好的~',
            '嗯~', '可以~', '行~', '好的～', '嗯～', '可以～', '行～',
            '好滴', '嗯滴', '可以滴', '行滴', '好的!', '嗯!', '可以!',
            '行!', '好！', '嗯！', '可以！', '行！', 'ok', 'ok的', 'ok呢',
            'ok哈', 'ok呀', 'ok哦', 'ok~', 'ok～', '没问题', '没问题呢',
            '没问题哈', '没问题呀', '没问题哦', '没问题~', '没问题～',
            '没问题哒', '没问题滴', '没问题!', '没问题！', '没问题哒',
            '没问题呢', '没问题哈', '没问题呀', '没问题哦', '没问题~',
            '没问题～', '没问题滴', '没问题!', '没问题！', '没问题哒',
            '没问题呢', '没问题哈', '没问题呀', '没问题哦', '没问题~',
            '没问题～', '没问题滴', '没问题!', '没问题！', '没问题哒',
            '没问题呢', '没问题哈', '没问题呀', '没问题哦', '没问题~',
            '没问题～', '没问题滴', '没问题!', '没问题！', '没问题哒',
        ]

        # 检查是否是纯确认性回复（排除包含其他内容的情况）
        for keyword in confirmation_keywords:
            if text == keyword or text == keyword + '~' or text == keyword + '～':
                return True

        # 检查是否是确认性回复（可能带表情）
        # 移除表情符号后检查
        text_without_emoji = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        if text_without_emoji in ['好', '嗯', '可以', '行', 'ok']:
            return True

        return False

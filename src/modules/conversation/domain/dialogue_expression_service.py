from __future__ import annotations

import re
from typing import Any, Dict, Optional

from src.models.user_profile import UserProfile


class DialogueExpressionService:
    """负责将结构化意图翻译成更自然的人类化表达。"""

    STRONG_SEEK_FEMALE_CUES = (
        "找女生", "找女孩子", "找小姐姐", "找个女生", "找女朋友", "找个女朋友", "找老婆", "喜欢女生", "想找女性",
    )
    STRONG_SEEK_MALE_CUES = (
        "找男生", "找男孩子", "找小哥哥", "找个男生", "找男朋友", "找个男朋友", "找老公", "喜欢男生", "想找男性",
    )
    WEAK_SEEK_FEMALE_CUES = {
        "温柔": 2.0,
        "文静": 2.0,
        "贤惠": 3.0,
        "顾家": 2.0,
        "身材苗条": 3.0,
        "苗条": 3.0,
        "漂亮": 2.0,
        "长相清秀": 2.0,
        "气质好": 2.0,
        "爱干净": 1.5,
        "会照顾人": 1.5,
        "会做饭": 2.0,
        "长发": 1.5,
        "白净": 1.5,
        "甜美": 1.5,
        "不强势": 2.0,
        "性格软一点": 2.0,
        "小鸟依人": 2.0,
        "甜一点": 1.5,
        "可爱一点": 1.5,
        "温婉": 2.0,
        "善解人意": 2.0,
        "脾气好": 1.5,
        "女生味一点": 2.0,
    }
    WEAK_SEEK_MALE_CUES = {
        "成熟稳重": 2.0,
        "有担当": 3.0,
        "有责任心": 3.0,
        "有安全感": 2.0,
        "上进": 2.0,
        "事业心强": 2.0,
        "可靠": 2.0,
        "体贴": 2.0,
        "幽默": 1.5,
        "不幼稚": 2.0,
        "成熟点": 2.0,
        "比我大一点": 2.0,
        "有主见": 2.0,
        "会规划生活": 1.5,
        "有经济基础": 2.0,
        "有房有车": 2.0,
        "大气一点": 1.5,
        "高一点": 1.0,
        "个子高一点": 1.0,
        "比我高": 1.0,
        "身高高一点": 1.0,
    }
    GENDER_CHALLENGE_PATTERNS = (
        r"这你还看不出来",
        r"这还看不出来",
        r"你还看不出来",
        r"还要问",
        r"还不知道",
        r"你还不知道",
        r"我这要求",
    )
    SOFT_GENDER_CONFIRM_THRESHOLD = 3.0

    def __init__(self) -> None:
        self._cursor: Dict[str, int] = {}

    CORE_FIELD_PROMPTS = {
        "sex": (
            "先随便聊聊，你这边是男生还是女生呀？",
            "我先认识你一下，你这边是男生还是女生呀？",
            "我先简单了解下，你这边是男生还是女生呀？",
        ),
        "age": (
            "你是几几年的呀？",
            "方便说下你是哪一年出生的吗？",
            "你大概是哪一年的呀？",
        ),
        "location": (
            "你现在主要在哪个城市生活呀？",
            "你平时主要在哪边生活？",
            "你现在是在什么城市生活呀？",
        ),
        "education": (
            "你大概是什么学历呀？",
            "方便说下你的学历吗？",
            "你的学历背景大概是怎样的？",
        ),
        "occupation": (
            "你现在主要做哪方面工作呀？",
            "平时是做什么工作的？",
            "工作这块你现在主要在哪个方向？",
        ),
    }

    OPENING_INTENT_BRIDGES = (
        "好呀，你也可以先简单介绍下自己，我顺着了解会更自然一点。或者我先问你一个小问题，你这边是男生还是女生呀？",
        "行呀，那我先认识下你。你也可以先简单说说自己，我这边顺着了解会更顺一点；要不我先问你，你这边是男生还是女生呀？",
    )

    GREETING_RESUME_SEX_PROMPTS = (
        "在呢，你这边是男生还是女生呀？",
        "你好呀，我在呢。你这边是男生还是女生呀？",
        "在的，我接着了解下，你这边是男生还是女生呀？",
    )

    CONTACT_PROMPTS = (
        "先留个手机号也行，后面如果有合适的进展，我这边也好继续联系上你。",
        "你要是方便的话，先留个手机号也行，后面有合适的我再跟你接着聊。",
        "电话先留一个也行，真有合适的方向，我这边联系你会顺一点。",
    )

    TRANSITION_PREFIXES = {
        "age": ("好呀", "那我再了解下", "顺着聊到这儿"),
        "location": ("好呀", "那我再问你一个", "顺着聊到这儿"),
        "education": ("好呀", "那我再了解下", "顺着聊到这儿"),
        "occupation": ("好呀", "那我再问你一个", "顺着聊到这儿"),
        "contact": ("聊到这儿", "那我顺手问你一个"),
    }

    SENSITIVE_REASON_VARIANTS = {
        "age": (
            "这样后面接话会更顺一点。",
            "后面我也更好顺着往下聊。",
        ),
        "location": (
            "后面我也能优先往同城这边留意。",
            "这样我后面更好先看同城方向。",
        ),
        "education": (
            "这样后面我也更好往相对合适的方向看。",
            "这个先对齐了，后面接话会更顺一点。",
        ),
        "monthly_income": (
            "这样我后面更好往条件相近的方向留意。",
            "我心里也更好有个大概范围。",
        ),
        "marital_status": (
            "这个我先确认清楚，后面接话会更顺一点。",
            "这个点先对齐了，后面就不容易聊岔。",
        ),
    }

    MID_CONVERSATION_CORE_FIELD_PROMPTS = {
        "sex": (
            "你这边是男生还是女生呀？",
            "我再确认一下，你这边是男生还是女生呀？",
        ),
    }

    def render_field_question(
        self,
        field: Optional[str],
        *,
        profile: Optional[UserProfile] = None,
        stage: str = "collect",
        user_message: str = "",
        preference_hint: str = "",
    ) -> str:
        if not field:
            return "你继续说，我顺着往下了解。"
        if field == "contact":
            return self.render_contact_question(profile=profile, stage=stage, user_message=user_message)
        if field == "sex":
            soft_confirmation = self._build_soft_gender_confirmation_prompt(
                profile,
                user_message=user_message,
                preference_hint=preference_hint,
            )
            if soft_confirmation:
                return soft_confirmation
        if field == "sex" and self._looks_like_opening_matchmaking_intent(user_message):
            return self._next_variant("opening:intent_bridge", self.OPENING_INTENT_BRIDGES)
        if field == "sex" and self._looks_like_short_greeting(user_message):
            return self._next_variant("greeting:resume_sex", self.GREETING_RESUME_SEX_PROMPTS)
        if field == "partner_requirement":
            bridged_preference = self._build_bridged_partner_requirement_prompt(profile)
            if bridged_preference:
                return bridged_preference
            return "你对另一半大概有什么要求呀？比如年龄、城市、性格这些，你会更看重哪方面？"
        if field == "marital_status":
            bridged_marital = self._build_bridged_marital_status_prompt(profile)
            if bridged_marital:
                return bridged_marital
            variants = (
                "你现在婚况方便说个大概吗？我想先确认准一点，因为有的人分居中也会直接说自己单身。",
                "感情状态这边你方便说个大概吗？我多问一句哈，主要是有些情况不一定一句单身就能概括。",
                "婚况这边我想先了解一下，像分居中这种情况，很多人也会直接说自己单身，所以我先确认细一点。",
            )
            return self._pick_variant_avoiding_recent_openings("core:marital_status", variants, profile)
        if field == "monthly_income":
            bridged_income = self._build_bridged_income_prompt(profile)
            if bridged_income:
                return bridged_income
            return self._maybe_add_reason(
                "monthly_income",
                "如果你方便的话，我再轻问一句，你月收入大概在哪个区间？不方便说也没关系。",
            )
        prompts = self._get_core_field_prompts(field, stage=stage)
        if not prompts:
            return "你继续说，我顺着往下了解。"
        if field == "occupation":
            contextual_occupation = self._build_contextual_occupation_prompt(user_message, profile=profile)
            if contextual_occupation:
                return contextual_occupation
        if field == "age":
            birth_year_bucket_prompt = self._build_birth_year_bucket_prompt(profile)
            if birth_year_bucket_prompt:
                return birth_year_bucket_prompt
            if profile and (getattr(profile, "age", None) or str(getattr(profile, "age_label", "") or "").strip()):
                bridged_marital = self._build_bridged_marital_status_prompt(profile)
                if bridged_marital:
                    return bridged_marital
                variants = (
                    "你现在婚况方便说个大概吗？我想先确认准一点，因为有的人分居中也会直接说自己单身。",
                    "感情状态这边你方便说个大概吗？我多问一句哈，主要是有些情况不一定一句单身就能概括。",
                    "婚况这边我想先了解一下，像分居中这种情况，很多人也会直接说自己单身，所以我先确认细一点。",
                )
                return self._pick_variant_avoiding_recent_openings("age:marital_status", variants, profile)
            bridged_age = self._build_bridged_age_prompt(profile)
            if bridged_age:
                return bridged_age
        base = self._next_variant(f"core:{field}", prompts)
        base = self._maybe_add_reason(field, base)
        return self._maybe_add_transition_prefix(field, base, user_message=user_message)

    def _get_core_field_prompts(self, field: str, *, stage: str) -> Optional[tuple[str, ...]]:
        if field == "sex" and stage != "opening":
            return self.MID_CONVERSATION_CORE_FIELD_PROMPTS.get(field) or self.CORE_FIELD_PROMPTS.get(field)
        return self.CORE_FIELD_PROMPTS.get(field)

    def render_contact_question(
        self,
        *,
        profile: Optional[UserProfile] = None,
        stage: str = "collect",
        user_message: str = "",
    ) -> str:
        location = str(getattr(profile, "location", "") or "").strip() if profile else ""
        occupation = str(getattr(profile, "occupation", "") or "").strip() if profile else ""
        if location and occupation:
            variants = (
                f"你在{location}做{occupation}这块是吧，留个手机号会更方便一点，后面有合适的我也好联系上你。",
                f"像你现在在{location}做{occupation}这块，留个手机号的话，后面有合适进展我也好及时联系你。",
                f"你这边在{location}做{occupation}我有数了，方便的话留个手机号，后面有合适的我好联系你。",
            )
            base = self._pick_variant_avoiding_recent_openings("contact:context:location_occupation", variants, profile)
            return self._maybe_add_transition_prefix("contact", base, user_message=user_message)
        if location:
            variants = (
                f"你现在在{location}这边是吧，方便的话留个手机号，后面有合适的我也好联系上你。",
                f"像你现在在{location}这边，留个手机号会更方便一点，后面有合适进展我也好联系你。",
            )
            base = self._pick_variant_avoiding_recent_openings("contact:context:location", variants, profile)
            return self._maybe_add_transition_prefix("contact", base, user_message=user_message)
        if occupation:
            variants = (
                f"你现在做{occupation}这块我有数了，方便的话留个手机号，后面有合适的我也好联系你。",
                f"像你做{occupation}这行，留个手机号会更方便一点，后面有合适进展我也好联系上你。",
            )
            base = self._pick_variant_avoiding_recent_openings("contact:context:occupation", variants, profile)
            return self._maybe_add_transition_prefix("contact", base, user_message=user_message)
        base = self._next_variant("contact", self.CONTACT_PROMPTS)
        return self._maybe_add_transition_prefix("contact", base, user_message=user_message)

    def _maybe_add_transition_prefix(self, field: str, base: str, *, user_message: str = "") -> str:
        message = str(user_message or "").strip()
        if not message:
            return base

        short_answer = len(message) <= 8 and not any(token in message for token in ("？", "?", "吗", "怎么", "为什么"))
        if not short_answer:
            return base

        prefixes = self.TRANSITION_PREFIXES.get(field) or ()
        if not prefixes:
            return base
        prefix = self._next_variant(f"prefix:{field}", prefixes)
        if field == "contact":
            return base

        if prefix in {"好呀", "那我再了解下", "顺着聊到这儿", "那我再问你一个"}:
            return f"{prefix}，{base}"
        return base

    def _maybe_add_reason(self, field: str, base: str) -> str:
        variants = self.SENSITIVE_REASON_VARIANTS.get(field) or ()
        if not variants:
            return base
        idx = self._cursor.get(f"reason:{field}", 0)
        self._cursor[f"reason:{field}"] = idx + 1
        # 控制解释出现频率：年龄/城市更低频，其他敏感字段适中。
        modulo = 5 if field in {"age", "location"} else 3
        if idx % modulo != 0:
            return base
        reason = variants[idx % len(variants)]
        if "？" in base:
            return base.replace("？", f"？{reason}")
        return f"{base} {reason}"

    def _build_soft_gender_confirmation_prompt(
        self,
        profile: Optional[UserProfile],
        *,
        user_message: str = "",
        preference_hint: str = "",
    ) -> Optional[str]:
        if not profile or getattr(profile, "sex", None):
            return None

        inference_context = self.resolve_gender_inference_context(
            profile=profile,
            user_message=user_message,
            preference_hint=preference_hint,
        )
        if inference_context["guess"] == "unknown":
            return None

        guess = str(inference_context["guess"])
        confidence = str(inference_context["confidence"])
        if confidence == "weak":
            return None

        guess_label = "男生" if guess == "male" else "女生"
        is_challenge = self._looks_like_gender_confirmation_challenge(user_message)
        evidence = str(inference_context.get("evidence") or "").strip()

        explicit_relationship_preference = ""
        if "找男朋友" in evidence:
            explicit_relationship_preference = "找男朋友"
        elif "找女朋友" in evidence:
            explicit_relationship_preference = "找女朋友"

        if is_challenge:
            lead = self._next_variant(
                f"sex:challenge:lead:{guess_label}",
                ("哈哈", "你这么说也有道理", "这个嘛，被你发现了"),
            )
            inference_ack = self._next_variant(
                f"sex:challenge:ack:{guess_label}",
                ("这个我大概能看出来", "方向上我其实大概能看出来", "这个方向我心里大概有数"),
            )
            reason = self._next_variant(
                f"sex:challenge:reason:{guess_label}",
                ("不过这种我还是会确认一下", "但这种我一般还是会问准一点", "不过我还是得确认清楚点"),
            )
            example = self._next_variant(
                f"sex:challenge:example:{guess_label}",
                (
                    "也有男生来找男朋友的",
                    "也有女生来找女朋友的",
                    "也会遇到同向在了解的情况",
                ),
            )
            confirm = self._next_variant(
                f"sex:challenge:confirm:{guess_label}",
                (
                    f"你这边是{guess_label}对吧？",
                    f"你这边现在是{guess_label}这个方向是吧？",
                ),
            )
            return f"{lead}，{inference_ack}，{reason}，{example}。{confirm}"

        if explicit_relationship_preference:
            lead = self._next_variant(
                f"sex:explicit_pref:lead:{explicit_relationship_preference}",
                (
                    f"想{explicit_relationship_preference}是吧",
                    f"好呀，你这边是想{explicit_relationship_preference}",
                    f"明白，你这边是想{explicit_relationship_preference}",
                ),
            )
            confirm = self._next_variant(
                f"sex:explicit_pref:confirm:{guess_label}",
                (
                    f"你这边是{guess_label}对吗？",
                    f"我顺手确认下，你是{guess_label}对吗？",
                ),
            )
            return f"{lead}，{confirm}"

        prefix = self._next_variant(
            f"sex:soft:prefix:{guess_label}",
            ("我再确认一下", "我顺手确认一下", "我这边再确认一下"),
        )
        confirm = self._next_variant(
            f"sex:soft:confirm:{guess_label}",
            (
                f"你这边是{guess_label}对吧？",
                f"你这边是{guess_label}，对吧？",
            ),
        )
        return f"{prefix}，{confirm}"

    def resolve_gender_inference_context(
        self,
        *,
        profile: Optional[UserProfile],
        user_message: str = "",
        preference_hint: str = "",
    ) -> Dict[str, Any]:
        preference = str(preference_hint or "").strip()
        source = "hint" if preference else ""
        if not preference and profile:
            preference = str(getattr(profile, "partner_requirement", "") or "").strip()
            if preference:
                source = "profile"
        if not preference:
            preference = self._extract_preference_hint_from_message(user_message)
            if preference:
                source = "message"

        if not preference:
            return {"guess": "unknown", "confidence": "weak", "evidence": "", "source": ""}

        inference = self._infer_gender_from_preference(preference)
        inference["evidence"] = preference
        inference["source"] = source
        return inference

    @staticmethod
    def _extract_preference_hint_from_message(user_message: str) -> str:
        message = str(user_message or "").strip()
        if not message:
            return ""

        patterns = (
            r"(找(?:个|一个)?男朋友)",
            r"(找(?:个|一个)?女朋友)",
            r"(找(?:个|一个)?男生)",
            r"(找(?:个|一个)?女生)",
            r"(喜欢男生)",
            r"(喜欢女生)",
            r"(想找男性)",
            r"(想找女性)",
        )
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                return match.group(1)

        return ""

    def _infer_gender_from_preference(self, preference_text: str) -> Dict[str, object]:
        text = re.sub(r"\s+", "", str(preference_text or ""))
        if not text:
            return {"guess": "unknown", "confidence": "weak", "seek_female_score": 0.0, "seek_male_score": 0.0}

        # 显式关系词优先单独处理，避免被后续泛化词表覆盖。
        if "找男朋友" in text:
            return {"guess": "female", "confidence": "strong", "seek_female_score": 0.0, "seek_male_score": 100.0}
        if "找女朋友" in text:
            return {"guess": "male", "confidence": "strong", "seek_female_score": 100.0, "seek_male_score": 0.0}

        if re.search(r"(?:^|想找|想要|喜欢|偏向|找)(?:一个|个)?(?:同城|本地|深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港)?的?(女生|女孩子|女性)", text):
            return {"guess": "male", "confidence": "strong", "seek_female_score": 100.0, "seek_male_score": 0.0}
        if re.search(r"(?:^|想找|想要|喜欢|偏向|找)(?:一个|个)?(?:同城|本地|深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港)?的?(男生|男孩子|男性)", text):
            return {"guess": "female", "confidence": "strong", "seek_female_score": 0.0, "seek_male_score": 100.0}

        if any(cue in text for cue in self.STRONG_SEEK_FEMALE_CUES):
            return {"guess": "male", "confidence": "strong", "seek_female_score": 100.0, "seek_male_score": 0.0}
        if any(cue in text for cue in self.STRONG_SEEK_MALE_CUES):
            return {"guess": "female", "confidence": "strong", "seek_female_score": 0.0, "seek_male_score": 100.0}

        seek_female_score = sum(score for cue, score in self.WEAK_SEEK_FEMALE_CUES.items() if cue in text)
        seek_male_score = sum(score for cue, score in self.WEAK_SEEK_MALE_CUES.items() if cue in text)
        seek_male_score += self._score_height_cues(text, seeking_male=True)
        seek_female_score += self._score_height_cues(text, seeking_male=False)

        if seek_female_score >= self.SOFT_GENDER_CONFIRM_THRESHOLD and seek_female_score > seek_male_score:
            return {
                "guess": "male",
                "confidence": "medium",
                "seek_female_score": seek_female_score,
                "seek_male_score": seek_male_score,
            }
        if seek_male_score >= self.SOFT_GENDER_CONFIRM_THRESHOLD and seek_male_score > seek_female_score:
            return {
                "guess": "female",
                "confidence": "medium",
                "seek_female_score": seek_female_score,
                "seek_male_score": seek_male_score,
            }
        return {
            "guess": "unknown",
            "confidence": "weak",
            "seek_female_score": seek_female_score,
            "seek_male_score": seek_male_score,
        }

    @staticmethod
    def _score_height_cues(text: str, *, seeking_male: bool) -> float:
        score = 0.0
        if seeking_male:
            if re.search(r"(至少|不低于)?183(?:cm|CM|厘米)?(?:以上|\+)?", text):
                score += 2.5
            elif re.search(r"(至少|不低于)?180(?:cm|CM|厘米)?(?:以上|\+)?", text):
                score += 2.0
            elif re.search(r"(至少|不低于)?178(?:cm|CM|厘米)?(?:以上|\+)?", text):
                score += 1.5
            elif re.search(r"(至少|不低于)?175(?:cm|CM|厘米)?(?:以上|\+)?", text):
                score += 1.0
            elif re.search(r"(至少|不低于)?170(?:cm|CM|厘米)?(?:以上|\+)?", text):
                score += 0.5
            return score

        if "160左右" in text or "165左右" in text:
            score += 0.5
        if "娇小一点" in text or "小个子一点" in text:
            score += 1.0
        if "不太高" in text or "不要太高" in text:
            score += 0.5
        return score

    def _looks_like_gender_confirmation_challenge(self, user_message: str) -> bool:
        text = str(user_message or "").strip()
        if not text:
            return False
        return any(re.search(pattern, text) for pattern in self.GENDER_CHALLENGE_PATTERNS)

    def _next_variant(self, key: str, candidates: tuple[str, ...]) -> str:
        if not candidates:
            return ""
        idx = self._cursor.get(key, 0) % len(candidates)
        self._cursor[key] = idx + 1
        return candidates[idx]

    @staticmethod
    def _opening_signature(text: str) -> str:
        normalized = re.sub(r"[\s，,。！？!?~～、:：;；'\"（）()]+", "", str(text or ""))
        return normalized[:8]

    def _pick_variant_avoiding_recent_openings(
        self,
        key: str,
        candidates: tuple[str, ...],
        profile: Optional[UserProfile],
    ) -> str:
        if not candidates:
            return ""
        recent = {
            self._opening_signature(item)
            for item in getattr(profile, "recent_response_openings", [])[-5:]
            if str(item or "").strip()
        }
        idx = self._cursor.get(key, 0)
        self._cursor[key] = idx + 1
        ordered = [candidates[(idx + offset) % len(candidates)] for offset in range(len(candidates))]
        for candidate in ordered:
            if self._opening_signature(candidate) not in recent:
                return candidate
        return ordered[0]

    @staticmethod
    def _looks_like_opening_matchmaking_intent(user_message: str) -> bool:
        message = str(user_message or "").strip()
        if not message:
            return False
        if not re.search(r"(找对象|想找对象|帮我找个对象|相亲|脱单|找另一半|找个男朋友|找个女朋友|认真聊聊)", message):
            return False
        if re.search(r"(男生|男的|女生|女的|90后|\d{2}岁|深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港|本科|硕士|博士|it|运营|程序员|单身|离异)", message.lower()):
            return False
        return True

    @staticmethod
    def _looks_like_short_greeting(user_message: str) -> bool:
        normalized = re.sub(r"[\s，,。！？!?~～、呀啊呢哈啦]+", "", str(user_message or "").lower())
        if not normalized:
            return False
        return normalized in {"你好", "您好", "嗨", "哈喽", "hi", "hello", "在吗"}

    def _build_bridged_income_prompt(self, profile: Optional[UserProfile]) -> Optional[str]:
        occupation = str(getattr(profile, "occupation", "") or "").strip()
        if not occupation:
            return None
        variants = (
            f"做{occupation}的话，收入这块大概在什么区间呀？",
            f"你做{occupation}这行的话，收入大概在哪个范围？",
            f"像{occupation}这类工作，你现在月收入大概在哪一档呀？",
        )
        return self._pick_variant_avoiding_recent_openings("bridge:income", variants, profile)

    def _build_bridged_age_prompt(self, profile: Optional[UserProfile]) -> Optional[str]:
        education = str(getattr(profile, "education", "") or "").strip()
        if not education:
            return None
        age = getattr(profile, "age", None)
        age_label = str(getattr(profile, "age_label", "") or "").strip()
        if age or age_label:
            return None
        variants = (
            f"{education}是吧，那你是几几年的呀？",
            f"那我顺着问下，你是哪一年的呀？",
            f"{education}这块我有数了，那你大概是哪一年出生的呀？",
        )
        return self._pick_variant_avoiding_recent_openings("bridge:age", variants, profile)

    def _build_birth_year_bucket_prompt(self, profile: Optional[UserProfile]) -> Optional[str]:
        bucket = str(getattr(profile, "pending_birth_year_bucket", "") or "").strip()
        if not bucket or getattr(profile, "birth_year_confirmation_closed", False):
            return None
        bucket_match = re.search(r"^(\d{2})后$", bucket)
        if not bucket_match:
            return None
        prefix = bucket_match.group(1)
        variants = (
            f"好，那你具体是{prefix}几年的呀？",
            f"{bucket}我先知道了，那你具体是哪一年的呀？",
            f"那我再确认下，你是{prefix}几年的呀？",
        )
        return self._pick_variant_avoiding_recent_openings("bridge:birth_year_bucket", variants, profile)

    def _build_bridged_marital_status_prompt(self, profile: Optional[UserProfile]) -> Optional[str]:
        age_label = str(getattr(profile, "age_label", "") or "").strip()
        if not age_label:
            age = getattr(profile, "age", None)
            age_label = f"{age}岁" if age else ""
        if not age_label:
            return None
        variants = (
            "那我顺着问一句，你现在婚况方便说个大概吗？我想确认准一点，因为有的人分居中也会直接说自己单身。",
            "说到这儿，你现在感情状态也方便简单说下吗？我多问一句，主要是有些情况不一定一句单身就能概括。",
            "我再接着了解一句，你现在婚况大概是怎样的呀？像分居中这种情况，很多人也会直接说自己单身，所以我先确认细一点。",
        )
        return self._pick_variant_avoiding_recent_openings("bridge:marital", variants, profile)

    def _build_bridged_partner_requirement_prompt(self, profile: Optional[UserProfile]) -> Optional[str]:
        marital_status = str(getattr(profile, "marital_status", "") or "").strip()
        if not marital_status:
            return None
        variants = (
            f"那你找对象的时候，会更看重对方哪一点呀？",
            f"说到这儿，你会更在意对方哪方面呀？",
            f"那你对另一半大概有什么要求呀？你会更看重哪一点？",
        )
        return self._pick_variant_avoiding_recent_openings("bridge:partner_requirement", variants, profile)

    def _build_contextual_occupation_prompt(self, user_message: str, *, profile: Optional[UserProfile] = None) -> Optional[str]:
        message = str(user_message or "").strip()
        city_match = re.search(r"(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港)", message)
        if not city_match and profile:
            city_match = re.search(r"(深圳|广州|杭州|上海|北京|成都|武汉|苏州|香港)", str(getattr(profile, "location", "") or ""))
        if not city_match:
            return None
        city = city_match.group(1)
        variants = (
            f"那你现在在{city}主要做哪方面工作呀？",
            f"你现在在{city}这边主要做什么呀？",
        )
        return self._next_variant("bridge:occupation", variants)

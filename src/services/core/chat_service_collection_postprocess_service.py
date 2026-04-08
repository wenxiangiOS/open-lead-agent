import logging
from typing import Any, Dict, Optional
import re

logger = logging.getLogger(__name__)


def _is_affirmative_confirmation_answer(text: str) -> bool:
    return bool(
        re.search(
            r"^\s*(?:是的|对|对的|嗯|嗯嗯|没错|是|好的|好)"
            r"(?:[呀呢啊哦哈啦嘛]*)?"
            r"(?:\s*[，,、 ]\s*(?:单身|未婚|离异|已婚|分居))?\s*$",
            str(text or ""),
        )
    )


class ChatServiceCollectionPostprocessService:
    CORE_RETRYABLE_FIELDS = {"sex", "age", "education", "occupation", "location"}

    def __init__(self, host: Any) -> None:
        self.host = host

    @staticmethod
    def _looks_like_tail_completion_reply(user_message: str) -> bool:
        text = str(user_message or "").strip()
        if not text:
            return False
        normalized = re.sub(r"[\s，,。！？!?~～、:：;；'\"（）()]+", "", text.lower()).strip()
        if not normalized:
            return False
        tail_markers = (
            "就这些",
            "就这样",
            "没有了",
            "没了",
            "其他没有了",
            "其他没了",
            "其他的没有了",
            "差不多",
            "差不多了",
            "没别的了",
            "没别的要求了",
        )
        return any(marker in normalized for marker in tail_markers)

    @staticmethod
    def _is_impossible_age_value(value: object) -> bool:
        try:
            age_value = int(str(value).strip())
        except (TypeError, ValueError):
            return False
        return age_value <= 10 or age_value >= 120

    @staticmethod
    def _is_impossible_height_value(value: object) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        digits = re.sub(r"\D", "", text)
        if digits:
            try:
                height_value = int(digits)
            except ValueError:
                height_value = 0
            if height_value <= 80 or height_value >= 260:
                return True
        meter_match = re.search(r"(\d(?:\.\d+)?)\s*米", text)
        if meter_match:
            try:
                meter_value = float(meter_match.group(1))
            except ValueError:
                meter_value = 0.0
            return meter_value <= 0.8 or meter_value >= 2.6
        return False

    def _should_hard_end_fake_info(
        self,
        *,
        user_message: str,
        user_profile,
        collection_result: Dict[str, Any],
    ) -> bool:
        suspicious_fields = self._find_suspicious_profile_fields(
            user_message=user_message,
            user_profile=user_profile,
            collection_result=collection_result,
        )
        if not suspicious_fields:
            return False

        error_count = dict(getattr(user_profile, "error_count", {}) or {})
        return all(int(error_count.get(f"suspicious_{field}", 0) or 0) >= 2 for field in suspicious_fields)

    def _find_suspicious_profile_fields(
        self,
        *,
        user_message: str,
        user_profile,
        collection_result: Dict[str, Any],
    ) -> list[str]:
        if not self.host._looks_like_fake_info_message(user_message):
            return []

        suspicious: list[str] = []
        all_fields = list(collection_result.get("all_fields") or [])
        for item in all_fields:
            if not isinstance(item, dict):
                continue
            field = str(item.get("field") or "").strip()
            value = item.get("value")
            if field == "age" and self._is_impossible_age_value(value):
                suspicious.append("age")
            if field == "height" and self._is_impossible_height_value(value):
                suspicious.append("height")

        if self._is_impossible_age_value(getattr(user_profile, "age", None)):
            suspicious.append("age")
        if self._is_impossible_height_value(getattr(user_profile, "height", None)):
            suspicious.append("height")
        return sorted(set(suspicious))

    async def _apply_suspicious_value_clarification_state(
        self,
        *,
        account_id: str,
        user_profile,
        collection_result: Dict[str, Any],
        suspicious_fields: list[str],
    ) -> None:
        if not suspicious_fields:
            return

        error_count = dict(getattr(user_profile, "error_count", {}) or {})
        for field in suspicious_fields:
            key = f"suspicious_{field}"
            error_count[key] = int(error_count.get(key, 0) or 0) + 1
            if field == "age":
                user_profile.age = None
                user_profile.age_label = None
                user_profile.collection_progress["age"] = False
                user_profile.collection_progress["age_label"] = False
                collection_result["all_fields"] = [
                    item
                    for item in (collection_result.get("all_fields") or [])
                    if str(item.get("field") or "").strip() not in {"age", "age_label"}
                ]
            elif field == "height":
                user_profile.height = None
                user_profile.collection_progress["height"] = False
                collection_result["all_fields"] = [
                    item
                    for item in (collection_result.get("all_fields") or [])
                    if str(item.get("field") or "").strip() != "height"
                ]

        user_profile.error_count = error_count
        collection_result["suspicious_value_clarification"] = {"fields": suspicious_fields}
        await self.host.user_service.save_user_profile(account_id, user_profile)

    async def process_after_extraction(
        self,
        *,
        account_id: str,
        user_profile,
        collection_result: Dict[str, Any],
        user_message: str,
        last_response: str,
    ) -> Dict[str, Any]:
        if self._should_hard_end_fake_info(
            user_message=user_message,
            user_profile=user_profile,
            collection_result=collection_result,
        ):
            ending_info = self.host.ending_service.build_ending_info("fake_info", user_profile)
            await self.host.user_service.save_user_profile(account_id, user_profile)
            collection_result["ending_info"] = ending_info
            logger.info("[收尾检测] 命中虚假信息硬兜底 fake_info")
            return collection_result

        suspicious_fields = self._find_suspicious_profile_fields(
            user_message=user_message,
            user_profile=user_profile,
            collection_result=collection_result,
        )
        if suspicious_fields:
            await self._apply_suspicious_value_clarification_state(
                account_id=account_id,
                user_profile=user_profile,
                collection_result=collection_result,
                suspicious_fields=suspicious_fields,
            )
            logger.info("[异常值澄清] 标记可疑字段待澄清: %s", ",".join(suspicious_fields))

        ending_info = self.host.ending_service.check_and_get_ending(
            user_message,
            user_profile,
            collection_result,
        )

        if ending_info:
            scenario = ending_info["scenario"]
            logger.info("[收尾检测] 检测到收尾场景: %s, AI生成: True", scenario)
            if scenario == "both_rejected":
                ending_info["use_ai"] = False
                ending_info["response"] = self.host._get_both_rejected_ending_response()
                collection_result["response"] = ending_info["response"]
                logger.info("[收尾检测] both_rejected 改为固定业务收尾")

            await self.host.user_service.save_user_profile(account_id, user_profile)
            collection_result["ending_info"] = ending_info
            logger.info("[收尾检测] AI生成场景，传递给外部处理: %s", scenario)
        elif self.host._can_end_with_contact_completion(user_profile) and (
            bool(collection_result.get("collected"))
            or bool(collection_result.get("all_fields"))
            or self._looks_like_tail_completion_reply(user_message)
        ):
            ending_info = self.host.ending_service.build_ending_info("normal_complete", user_profile)
            await self.host.user_service.save_user_profile(account_id, user_profile)
            collection_result["ending_info"] = ending_info
            logger.info("[收尾检测] 补触发 normal_complete: coverage 已完成，直接进入业务收尾")

        await self._apply_divorce_confirmation_gate(
            account_id=account_id,
            user_profile=user_profile,
            collection_result=collection_result,
            user_message=user_message,
            last_response=last_response,
            ending_info=ending_info,
        )
        await self._apply_refused_field_side_effects(
            account_id=account_id,
            user_profile=user_profile,
            collection_result=collection_result,
        )
        return collection_result

    async def _apply_divorce_confirmation_gate(
        self,
        *,
        account_id: str,
        user_profile,
        collection_result: Dict[str, Any],
        user_message: str,
        last_response: str,
        ending_info: Optional[Dict[str, Any]],
    ) -> None:
        divorce_confirmation_negative = (
            self.host._is_short_negative_reply(user_message)
            and self.host._is_divorce_confirmation_question(last_response)
        )
        if "离异" in str(user_profile.marital_status or ""):
            if self.host._is_divorce_status_complete_message(user_message) or (
                bool(getattr(user_profile, "divorce_confirmation_pending", False))
                and self.host._is_divorce_confirmation_question(last_response)
                and _is_affirmative_confirmation_answer(user_message)
            ):
                user_profile.marital_status = "离异（手续已办妥）"
                user_profile.divorce_confirmed = True
                user_profile.divorce_confirmation_pending = False
                await self.host.user_service.save_user_profile(account_id, user_profile)
                collection_result["divorce_confirmation_cleared"] = True
                logger.info("[离异手续已办妥] 用户说: %s，更新 marital_status=离异（手续已办妥）", user_message)
            elif self.host._is_divorce_status_incomplete_message(user_message) or divorce_confirmation_negative:
                user_profile.marital_status = "离异（手续未办妥）"
                user_profile.divorce_confirmed = False
                user_profile.divorce_confirmation_pending = False
                await self.host.user_service.save_user_profile(account_id, user_profile)
                collection_result["ending_info"] = self.host.ending_service.build_ending_info(
                    "divorce_incomplete",
                    user_profile,
                )
                logger.info("[离异手续未办妥] 用户说: %s，进入结束场景 divorce_incomplete", user_message)
            elif not ending_info and "办妥" not in str(user_profile.marital_status or "") and not user_profile.divorce_confirmed:
                user_profile.divorce_confirmation_pending = True
                await self.host.user_service.save_user_profile(account_id, user_profile)
                collection_result["divorce_confirmation_pending"] = True
                logger.info("[离异手续待确认] 用户说: %s，锁定本轮只确认手续", user_message)
        elif user_profile.divorce_confirmation_pending:
            user_profile.divorce_confirmation_pending = False
            await self.host.user_service.save_user_profile(account_id, user_profile)

    async def _apply_refused_field_side_effects(
        self,
        *,
        account_id: str,
        user_profile,
        collection_result: Dict[str, Any],
    ) -> None:
        if account_id not in self.host._temp_refused_fields:
            return

        refused_fields = self.host._temp_refused_fields[account_id]
        collected_fields = [f["field"] for f in collection_result.get("all_fields", [])]
        for field in refused_fields:
            if field not in collected_fields:
                ask_count = int(getattr(user_profile, "field_ask_count", {}).get(field, 0) or 0)
                if field in self.CORE_RETRYABLE_FIELDS and ask_count < 2:
                    user_profile.set_pending_retry_field(field)
                    logger.info("[拒绝标记] 核心字段首次拒绝，保留一次解释型重问: %s", field)
                    continue

                user_profile.close_active_ask(field)
                if str(getattr(user_profile, "pending_retry_field", "") or "").strip() == field:
                    user_profile.clear_pending_retry_field()
                logger.info("[拒绝标记] 关闭字段主动追问，转被动提取: %s", field)
        await self.host.user_service.save_user_profile(account_id, user_profile)
        del self.host._temp_refused_fields[account_id]

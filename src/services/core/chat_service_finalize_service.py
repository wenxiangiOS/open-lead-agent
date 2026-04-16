from typing import Any, Dict

from src.models.user_profile import UserProfile
from src.modules.conversation.domain.turn_decision import TurnDecision
from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingResult
from src.services.core.chat_service_contact_text_service import ChatServiceContactTextService


class ChatServiceFinalizeService:
    def __init__(self, host: Any) -> None:
        self.host = host

    async def finalize_generated_response(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        turn_decision: TurnDecision,
        turn_understanding: TurnUnderstandingResult,
        collection_result: Dict[str, Any],
        response_to_clean: str,
        ai_response: str,
        bridge_prefix: str,
        contact_gate_before: bool,
        message_count: int,
    ) -> tuple[str, bool, UserProfile]:
        self._reset_turn_alignment_obs()
        invalid_contact_feedback = await self._maybe_override_invalid_contact_feedback(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            turn_decision=turn_decision,
            turn_understanding=turn_understanding,
            collection_result=collection_result,
        )
        if invalid_contact_feedback is not None:
            refreshed_profile = await self.host.user_service.get_user_profile(account_id)
            return invalid_contact_feedback, bool(str(invalid_contact_feedback).strip()), refreshed_profile

        return await self._finalize_unified_raw_response(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            response_to_clean=response_to_clean,
            ai_response=ai_response,
            turn_decision=turn_decision,
            turn_understanding=turn_understanding,
            collection_result=collection_result,
        )

    async def _maybe_override_invalid_contact_feedback(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        turn_decision: TurnDecision,
        turn_understanding: TurnUnderstandingResult,
        collection_result: Dict[str, Any],
    ) -> str | None:
        invalid_value = str(collection_result.get("invalid_contact_attempt") or "").strip()
        if not invalid_value:
            return None

        collected_fields = collection_result.get("all_fields", []) or []
        has_valid_contact_field = any(
            str(field_info.get("field") or "").strip() in {"phone", "wechat", "contact"}
            and str(field_info.get("value") or "").strip()
            for field_info in collected_fields
            if isinstance(field_info, dict)
        )
        if has_valid_contact_field:
            return None

        ask_field = str(getattr(turn_decision, "ask_field", "") or "").strip()
        primary_turn_type = str(getattr(turn_understanding, "primary_turn_type", "") or "").strip()
        subtype = str(getattr(turn_understanding, "subtype", "") or "").strip()
        in_contact_context = (
            ask_field == "contact"
            or primary_turn_type == "contact_answer"
            or subtype == "contact_context_reply"
            or self.host.contact_context_service.is_contact_context_active(user_profile)
        )
        if not in_contact_context:
            return None

        field = str(getattr(user_profile, "last_contact_request_type", "") or "").strip()
        if field not in {"phone", "wechat"}:
            field = "phone"

        return await self.host._build_validation_feedback(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            invalid_value=invalid_value,
            error_info={
                "code": "CONTACT_INVALID_FORMAT",
                "field": field,
                "detail": "invalid_format",
                "silent": False,
            },
        )

    async def _finalize_unified_raw_response(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        response_to_clean: str,
        ai_response: str,
        turn_decision: TurnDecision,
        turn_understanding: TurnUnderstandingResult,
        collection_result: Dict[str, Any],
    ) -> tuple[str, bool, UserProfile]:
        raw_response = str(ai_response or "")
        draft = self.host.unified_response_draft_service.build(raw_ai_response=raw_response)
        validation_result = self.host.unified_response_validation_service.validate(
            raw_ai_response=draft.raw_ai_response,
            infra_fail=not bool(str(ai_response or "").strip()) and bool(getattr(self.host, "_last_ai_failure_reason", None)),
            infra_fail_reason=getattr(self.host, "_last_ai_failure_reason", "") or "",
        )

        raw_mode = self._is_raw_response_mode_enabled()
        if raw_mode:
            display_text, removed_blocks = self.host.first_generation_delivery_service.extract_display_text(
                draft.raw_ai_response
            )
            rewritten_text, rewritten_removed_blocks = self.host.first_generation_delivery_service.extract_display_text(
                response_to_clean
            )
            cleaned_response, safe_cleaned = self.host.unified_response_safe_cleanup_service.cleanup(display_text)
            safe_cleaned = bool(safe_cleaned or removed_blocks)
            fallback_response = self._build_unified_fallback_response(
                validation_result=validation_result,
                user_profile=user_profile,
                user_message=user_message,
                turn_decision=turn_decision,
            )
            delivery = self.host.unified_response_delivery_service.deliver(
                draft=draft,
                validation_result=validation_result,
                cleaned_response=cleaned_response,
                safe_cleaned=safe_cleaned,
                fallback_response=fallback_response,
            )
            frozen_response = str(delivery.display_response or "").strip()
            frozen_response = self._maybe_prefer_contact_rewrite_in_raw_mode(
                frozen_response=frozen_response,
                rewritten_response=rewritten_text,
                user_profile=user_profile,
                user_message=user_message,
                turn_decision=turn_decision,
                turn_understanding=turn_understanding,
                collection_result=collection_result,
            )
            if frozen_response == rewritten_text and rewritten_removed_blocks:
                removed_blocks = list(dict.fromkeys([*removed_blocks, *rewritten_removed_blocks]))
            final_response = self._apply_alignment_guard_chain(
                response=frozen_response,
                user_profile=user_profile,
                user_message=user_message,
                turn_decision=turn_decision,
                collection_result=collection_result,
            )
            final_response = self._maybe_enforce_dense_intro_single_question_response(
                final_response=final_response,
                user_profile=user_profile,
                user_message=user_message,
                turn_decision=turn_decision,
            )
            final_response = self._maybe_enforce_contact_followup_response(
                user_profile=user_profile,
                final_response=final_response,
                user_message=user_message,
                turn_decision=turn_decision,
            )
            delivery_ok = bool(final_response)
            if delivery_ok:
                user_profile = await self.host._record_delivered_contact_ask_if_needed(
                    account_id,
                    user_profile,
                    user_message,
                    final_response,
                )

            record = self.host.unified_response_observability_service.build_record(
                draft=draft,
                delivery=delivery,
                validation_result=validation_result,
                cleaned_response=cleaned_response,
                extracted_fields_count=len((collection_result or {}).get("all_fields", []) or []),
                decision_after_collection=turn_decision,
                display_mutation_count=int(final_response != frozen_response),
                display_mutation_source="raw_mode_alignment_guard" if final_response != frozen_response else "",
                post_freeze_write_attempt=bool(final_response != frozen_response),
            )
            record["technical_blocks_removed"] = removed_blocks
            record["first_generation_only"] = True
            record["display_response"] = final_response
            record["final_display_response"] = final_response
            self.host._last_unified_generation_record = record
            self.host.unified_response_observability_service.log(
                account_id=account_id,
                record=self.host._last_unified_generation_record,
            )
            return final_response, delivery_ok, user_profile

        display_text, removed_blocks = self.host.first_generation_delivery_service.extract_display_text(
            draft.raw_ai_response
        )
        rewritten_text, rewritten_removed_blocks = self.host.first_generation_delivery_service.extract_display_text(
            response_to_clean
        )
        if rewritten_text:
            display_text = rewritten_text
            removed_blocks = list(dict.fromkeys([*removed_blocks, *rewritten_removed_blocks]))
        delivery = self.host.unified_response_delivery_service.deliver(
            draft=draft,
            validation_result=validation_result,
            cleaned_response=display_text,
            safe_cleaned=True,
            fallback_response="",
        )
        final_response = str(delivery.display_response or "").strip()

        final_response = self.host._enforce_question_budget_guard(
            final_response,
            user_profile=user_profile,
            user_message=user_message,
            turn_decision=turn_decision,
        )
        final_response = self.host._apply_priority_question_guard(
            final_response,
            turn_decision,
            user_message,
        )
        final_response = self.host._downgrade_premature_profile_summary(
            final_response,
            user_profile,
            collection_result=collection_result,
            ask_field=str(getattr(turn_decision, "ask_field", "") or "").strip(),
        )
        final_response = await self._maybe_repair_contact_completion_ending(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            final_response=final_response,
            collection_result=collection_result,
        )
        final_response = self._maybe_enforce_main_followup_alignment(
            user_profile=user_profile,
            user_message=user_message,
            final_response=final_response,
            turn_decision=turn_decision,
            collection_result=collection_result,
        )
        final_response = self._maybe_enforce_dense_intro_single_question_response(
            final_response=final_response,
            user_profile=user_profile,
            user_message=user_message,
            turn_decision=turn_decision,
        )
        final_response = self._maybe_eliminate_dangling_progress_hold(
            user_profile=user_profile,
            user_message=user_message,
            final_response=final_response,
            turn_decision=turn_decision,
            collection_result=collection_result,
        )
        delivery_ok = bool(final_response)
        final_response = self._maybe_enforce_contact_followup_response(
            user_profile=user_profile,
            final_response=final_response,
            user_message=user_message,
            turn_decision=turn_decision,
        )
        delivery_ok = bool(final_response)
        if delivery_ok:
            user_profile = await self.host._record_delivered_contact_ask_if_needed(
                account_id,
                user_profile,
                user_message,
                final_response,
            )

        record = self.host.unified_response_observability_service.build_record(
            draft=draft,
            delivery=delivery,
            validation_result=validation_result,
            cleaned_response=display_text,
            extracted_fields_count=len((collection_result or {}).get("all_fields", []) or []),
            decision_after_collection=turn_decision,
            display_mutation_count=int(final_response != str(delivery.display_response or "").strip()),
            display_mutation_source="legacy_finalize_chain" if final_response != str(delivery.display_response or "").strip() else "",
            post_freeze_write_attempt=bool(final_response != str(delivery.display_response or "").strip()),
        )
        record["technical_blocks_removed"] = removed_blocks
        record["first_generation_only"] = True
        record["display_response"] = final_response
        record["final_display_response"] = final_response
        self.host._last_unified_generation_record = record
        self.host.unified_response_observability_service.log(
            account_id=account_id,
            record=self.host._last_unified_generation_record,
        )
        return final_response, delivery_ok, user_profile

    def _build_unified_fallback_response(
        self,
        *,
        validation_result: Any,
        user_profile: UserProfile,
        user_message: str,
        turn_decision: TurnDecision,
    ) -> str:
        if not bool(getattr(validation_result, "should_fallback", False)):
            return ""
        if not getattr(turn_decision, "prioritize_user_question", False):
            ask_field = str(getattr(turn_decision, "ask_field", "") or "").strip()
            if ask_field:
                stable_followup = self._build_alignment_fallback_response(
                    user_profile=user_profile,
                    user_message=user_message,
                    ask_field=ask_field,
                    allow_medium_target=False,
                )
                if stable_followup:
                    return stable_followup
        reason = str(getattr(validation_result, "fallback_reason", "") or "").strip()
        if reason in {"ai_empty_response", "ai_infra_fail"}:
            return "刚刚这条没生成完整，你可以再发一句，我接着和你聊。"
        if reason == "invalid_ai_payload":
            return "我先把这条整理一下，我们继续聊。"
        return "我先换个更稳妥的说法，我们继续聊。"

    def _is_raw_response_mode_enabled(self) -> bool:
        checker = getattr(self.host, "_is_ai_raw_response_mode_enabled", None)
        if callable(checker):
            try:
                return bool(checker())
            except Exception:
                return True
        return True

    def _maybe_prefer_contact_rewrite_in_raw_mode(
        self,
        *,
        frozen_response: str,
        rewritten_response: str,
        user_profile: UserProfile,
        user_message: str,
        turn_decision: TurnDecision,
        turn_understanding: TurnUnderstandingResult,
        collection_result: Dict[str, Any],
    ) -> str:
        frozen_text = str(frozen_response or "").strip()
        rewritten_text = str(rewritten_response or "").strip()
        if not rewritten_text or rewritten_text == frozen_text:
            return frozen_text
        if getattr(turn_decision, "prioritize_user_question", False):
            return frozen_text

        ask_field = str(getattr(turn_decision, "ask_field", "") or "").strip()
        primary_turn_type = str(getattr(turn_understanding, "primary_turn_type", "") or "").strip()
        subtype = str(getattr(turn_understanding, "subtype", "") or "").strip()
        collected_fields = {
            str(item.get("field") or "").strip()
            for item in list((collection_result or {}).get("all_fields", []) or [])
            if isinstance(item, dict) and str(item.get("field") or "").strip()
        }
        has_invalid_contact_attempt = bool(str((collection_result or {}).get("invalid_contact_attempt") or "").strip())
        in_contact_turn = (
            ask_field == "contact"
            or bool(collected_fields & {"contact", "phone", "wechat"})
            or has_invalid_contact_attempt
            or primary_turn_type == "contact_answer"
            or subtype == "contact_context_reply"
            or self.host.contact_context_service.is_contact_context_active(user_profile)
        )
        if not in_contact_turn:
            return frozen_text

        rewritten_is_contactful = (
            ChatServiceContactTextService.response_mentions_phone_request(rewritten_text)
            or ChatServiceContactTextService.response_mentions_wechat_request(rewritten_text)
            or self.host._contains_contact_push_markers(rewritten_text)
        )
        if rewritten_is_contactful:
            return rewritten_text
        return frozen_text

    def _maybe_enforce_contact_followup_response(
        self,
        *,
        user_profile: UserProfile,
        final_response: str,
        user_message: str,
        turn_decision: TurnDecision,
    ) -> str:
        text = str(final_response or "").strip()
        if not text:
            return text
        if getattr(turn_decision, "prioritize_user_question", False):
            return text
        if not self.host._is_profile_collection_complete_or_exhausted(user_profile):
            return text
        if not getattr(user_profile, "phone_collected", False) or not getattr(user_profile, "phone", None):
            return text
        if getattr(user_profile, "wechat_collected", False) or getattr(user_profile, "rejected_wechat", False):
            return text

        try:
            next_action = self.host.contact_service.get_next_action(user_profile, user_message)
            action_value = getattr(next_action, "value", str(next_action))
        except Exception:
            action_value = "none"

        if action_value not in {"ask_wechat", "persuade_wechat"}:
            return text
        if ChatServiceContactTextService.response_mentions_wechat_request(text):
            return text

        return ChatServiceContactTextService.build_contact_followup_response(action_value, "phone")

    def _maybe_enforce_main_followup_alignment(
        self,
        *,
        user_profile: UserProfile,
        user_message: str,
        final_response: str,
        turn_decision: TurnDecision,
        collection_result: Dict[str, Any],
    ) -> str:
        text = str(final_response or "").strip()
        self._update_turn_alignment_obs(
            ask_field=str(getattr(turn_decision, "ask_field", "") or "").strip() or "-",
            asked_fields="-",
            ask_field_mismatch_detected=False,
            ask_field_mismatch_rewritten=False,
            reask_after_commit_detected=False,
        )
        if getattr(turn_decision, "prioritize_user_question", False):
            return text
        ask_field = str(getattr(turn_decision, "ask_field", "") or "").strip()
        self._update_turn_alignment_obs(ask_field=ask_field or "-")
        if not text or not ask_field:
            return text
        if ask_field == "contact":
            return self._maybe_enforce_contact_ask_alignment(
                user_profile=user_profile,
                user_message=user_message,
                final_response=text,
            )

        detect_asked = getattr(self.host, "_detect_asked_fields_in_response", None)
        detect_all_asked = getattr(self.host, "_detect_all_questioned_fields_in_response", None)
        if not callable(detect_asked) or not callable(detect_all_asked):
            return text

        asked_fields = set(detect_asked(text) or set()) | set(detect_all_asked(text) or set())
        asked_fields_display = ",".join(sorted(asked_fields)) or "-"
        self._update_turn_alignment_obs(asked_fields=asked_fields_display)
        collected_fields = {
            str(item.get("field") or "").strip()
            for item in list((collection_result or {}).get("all_fields", []) or [])
            if isinstance(item, dict) and str(item.get("field") or "").strip()
        }
        ask_field_collected = ask_field in collected_fields or (ask_field == "age" and "age_label" in collected_fields)
        reask_after_commit_detected = bool(ask_field_collected and ask_field in asked_fields)
        if reask_after_commit_detected:
            self._update_turn_alignment_obs(reask_after_commit_detected=True)

        allow_fields = {ask_field}
        if bool(getattr(turn_decision, "allow_medium_target", False)):
            try:
                policy_decision = self.host.collection_policy.decide(
                    user_profile,
                    user_message=user_message,
                    allow_contact_target=False,
                    allow_medium_target=True,
                    prioritize_user_question=False,
                    primary_move=str(getattr(turn_decision, "primary_move", "ack_and_ask") or "ack_and_ask"),
                )
                if str(getattr(policy_decision, "main_target", "") or "").strip() == ask_field:
                    side_target = str(getattr(policy_decision, "side_target", "") or "").strip()
                    if side_target and callable(getattr(self.host, "_is_allowed_main_side_pair", None)):
                        if self.host._is_allowed_main_side_pair(ask_field, side_target):
                            allow_fields.add(side_target)
            except Exception:
                pass

        if not asked_fields:
            has_progress = bool((collection_result.get("all_fields") or []))
            if has_progress:
                fallback = self._build_alignment_fallback_response(
                    user_profile=user_profile,
                    user_message=user_message,
                    ask_field=ask_field,
                    allow_medium_target=bool(getattr(turn_decision, "allow_medium_target", False)),
                )
                rewritten = self._style_preserving_fallback(
                    original_response=text,
                    fallback_response=fallback,
                )
                self._update_turn_alignment_obs(
                    ask_field_mismatch_detected=True,
                    ask_field_mismatch_rewritten=bool(rewritten and rewritten != text),
                )
                return rewritten
            return text

        if ask_field in asked_fields:
            return text

        if ask_field_collected and asked_fields <= allow_fields:
            return text

        disallowed_fields = asked_fields - allow_fields
        if not disallowed_fields:
            return text

        fallback = self._build_alignment_fallback_response(
            user_profile=user_profile,
            user_message=user_message,
            ask_field=ask_field,
            allow_medium_target=bool(getattr(turn_decision, "allow_medium_target", False)),
        )
        rewritten = self._style_preserving_fallback(
            original_response=text,
            fallback_response=fallback,
        )
        self._update_turn_alignment_obs(
            ask_field_mismatch_detected=True,
            ask_field_mismatch_rewritten=bool(rewritten and rewritten != text),
        )
        return rewritten

    def _maybe_enforce_contact_ask_alignment(
        self,
        *,
        user_profile: UserProfile,
        user_message: str,
        final_response: str,
    ) -> str:
        text = str(final_response or "").strip()
        if not text:
            return text
        if (
            ChatServiceContactTextService.response_mentions_phone_request(text)
            or ChatServiceContactTextService.response_mentions_wechat_request(text)
            or self.host._contains_contact_push_markers(text)
        ):
            return text

        try:
            next_action = self.host.contact_service.get_next_action(user_profile, user_message)
            action_value = getattr(next_action, "value", str(next_action))
        except Exception:
            action_value = "none"

        if action_value == "ask_wechat":
            return ChatServiceContactTextService.build_ask_wechat_fallback()
        if action_value == "persuade_wechat":
            return ChatServiceContactTextService.build_persuade_wechat_fallback()
        if action_value == "ask_phone":
            return "你要是方便的话，留个常用手机号就行。"
        if action_value == "persuade_phone":
            return ChatServiceContactTextService.build_phone_persuasion_fallback()
        return text

    def _maybe_eliminate_dangling_progress_hold(
        self,
        *,
        user_profile: UserProfile,
        user_message: str,
        final_response: str,
        turn_decision: TurnDecision,
        collection_result: Dict[str, Any],
    ) -> str:
        text = str(final_response or "").strip()
        if not text:
            return text

        ask_field = str(getattr(turn_decision, "ask_field", "") or "").strip()
        next_action = str(getattr(turn_decision, "next_action", "") or "").strip()
        target_field = ask_field or str(
            self.host._select_next_progress_target(user_profile, user_message=user_message) or ""
        ).strip()
        if not target_field:
            return text

        explicit_question_fields = (
            self.host._detect_asked_fields_in_response(text)
            | self.host._detect_all_questioned_fields_in_response(text)
        )
        hold_markers = (
            "这个我先放这儿",
            "继续往下说",
            "继续往下聊",
            "接着往下聊",
            "先顺着",
        )
        has_progress = bool((collection_result.get("all_fields") or []))
        if next_action == "confirm_divorce_status":
            has_progress = True

        if not has_progress and target_field != "contact":
            return text

        if next_action == "confirm_divorce_status":
            if target_field != "marital_status":
                target_field = "marital_status"
            if target_field not in explicit_question_fields or "离婚" not in text:
                return self.host._build_divorce_confirmation_response()
            return text

        if target_field in explicit_question_fields and not any(marker in text for marker in hold_markers):
            return text
        if not any(marker in text for marker in hold_markers) and not self.host._looks_like_low_information_model_reply(text):
            return text

        fallback = self.host._build_budget_guard_fallback_response(
            user_profile=user_profile,
            user_message=user_message,
            ask_field=target_field,
            allow_medium_target=bool(getattr(turn_decision, "allow_medium_target", False)),
        )
        return self.host._build_style_preserving_followup_response(
            original_response=text,
            fallback_response=fallback,
        )

    def _maybe_enforce_dense_intro_single_question_response(
        self,
        *,
        final_response: str,
        user_profile: UserProfile,
        user_message: str,
        turn_decision: TurnDecision,
    ) -> str:
        text = str(final_response or "").strip()
        if not text:
            return text
        if getattr(turn_decision, "prioritize_user_question", False):
            return text

        stage = str(getattr(turn_decision, "stage", "") or "").strip()
        dense_intro_like = stage == "opening"
        checker = getattr(self.host, "_looks_like_dense_intro_message_for_budget_guard", None)
        if callable(checker):
            try:
                dense_intro_like = dense_intro_like or bool(
                    checker(user_profile=user_profile, user_message=user_message)
                )
            except Exception:
                dense_intro_like = dense_intro_like or False
        if not dense_intro_like:
            return text

        re_mod = __import__("re")
        extract_question_segments = getattr(self.host, "_extract_explicit_question_segments", None)
        question_segments: list[str] = []
        if callable(extract_question_segments):
            try:
                question_segments = [
                    segment.strip()
                    for segment in (extract_question_segments(text) or [])
                    if str(segment or "").strip()
                ]
            except Exception:
                question_segments = []
        if not question_segments:
            question_segments = [
                segment.strip()
                for segment in re_mod.findall(r"[^。!！\n]*?[？?]", text)
                if segment.strip()
            ]

        prefix_clauses: list[str] = []
        first_question_clause = ""
        if len(question_segments) >= 2:
            first_question_clause = question_segments[0].strip()
            prefix_text = text
            first_question_index = text.find(first_question_clause)
            if first_question_index >= 0:
                prefix_text = text[:first_question_index]
            prefix_clauses = [
                clause.strip()
                for clause in re_mod.split(r"[。!！\n]+", prefix_text)
                if clause.strip()
            ]
        else:
            split_pattern = r"[。!！\n]+"
            clauses = [clause.strip() for clause in re_mod.split(split_pattern, text) if clause.strip()]
            if not clauses:
                return text

            question_like_clauses: list[str] = []
            for clause in clauses:
                detected_fields = set()
                detect_segment = getattr(self.host, "_detect_question_fields_in_segment", None)
                if callable(detect_segment):
                    try:
                        detected_fields = set(detect_segment(clause) or set())
                    except Exception:
                        detected_fields = set()
                looks_like_question = bool(
                    detected_fields
                    or "？" in clause
                    or "?" in clause
                    or "吗" in clause
                    or "呢" in clause
                    or "呀" in clause
                    or "方便" in clause
                    or "请问" in clause
                )
                if looks_like_question:
                    question_like_clauses.append(clause)
                    if not first_question_clause:
                        first_question_clause = clause
                    continue
                if not first_question_clause:
                    prefix_clauses.append(clause)

            if len(question_like_clauses) < 2 or not first_question_clause:
                return text

        collapsed_question = first_question_clause.strip()
        if collapsed_question and not any(collapsed_question.endswith(mark) for mark in ("？", "?", "。", "！", "!")):
            collapsed_question = f"{collapsed_question}？"
        collapsed_prefix = "。 ".join(
            part.rstrip("。！？!? ").strip()
            for part in prefix_clauses
            if str(part or "").strip()
        ).strip()
        collapsed_parts = [part for part in (collapsed_prefix, collapsed_question) if str(part or "").strip()]
        collapsed = "。 ".join(collapsed_parts).strip()
        return self.host._safe_clean_response(collapsed) if collapsed else text

    async def _maybe_repair_contact_completion_ending(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        final_response: str,
        collection_result: Dict[str, Any],
    ) -> str:
        text = str(final_response or "").strip()
        ending_info = dict(collection_result.get("ending_info") or {})
        scenario = str(ending_info.get("scenario") or "").strip()
        if scenario != "normal_complete":
            return text
        if not self.host._can_end_with_contact_completion(user_profile):
            return text

        expected_timeline = self.host.expectation_service.get_closing_timeline_text(user_profile)
        normalized = self.host.preparation_service._normalize_compact_text(text) if text else ""
        has_expected_timeline = expected_timeline in text
        contains_question = "？" in text or "?" in text
        banned_markers = (
            "我都记清楚",
            "记清楚啦",
            "我再跟你同步",
            "再跟你同步",
            "有合适的人选",
            "后面有合适的人选",
            "我记下了",
            "我记下来",
        )
        looks_like_valid_ending = (
            bool(text)
            and not contains_question
            and has_expected_timeline
            and not any(marker in text for marker in banned_markers)
        )
        if looks_like_valid_ending:
            return text

        fallback = self.host._get_contact_completion_ending_response(user_profile)
        regenerated = await self.host._generate_ai_ending_response(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            ending_info=ending_info,
            fallback_response=fallback,
        )
        regenerated = str(regenerated or "").strip()
        if not regenerated:
            return fallback

        regenerated_has_expected_timeline = expected_timeline in regenerated
        regenerated_contains_question = "？" in regenerated or "?" in regenerated
        regenerated_valid = (
            not regenerated_contains_question
            and regenerated_has_expected_timeline
            and not any(marker in regenerated for marker in banned_markers)
        )
        return regenerated if regenerated_valid else fallback

    def _apply_alignment_guard_chain(
        self,
        *,
        response: str,
        user_profile: UserProfile,
        user_message: str,
        turn_decision: TurnDecision,
        collection_result: Dict[str, Any],
    ) -> str:
        text = str(response or "").strip()
        if not text:
            return text
        ask_field = str(getattr(turn_decision, "ask_field", "") or "").strip()

        enforce_budget_guard = getattr(self.host, "_enforce_question_budget_guard", None)
        if callable(enforce_budget_guard) and ask_field:
            try:
                text = str(
                    enforce_budget_guard(
                        text,
                        user_profile=user_profile,
                        user_message=user_message,
                        turn_decision=turn_decision,
                    )
                    or ""
                ).strip()
            except Exception:
                pass

        apply_priority_guard = getattr(self.host, "_apply_priority_question_guard", None)
        if callable(apply_priority_guard):
            try:
                text = str(apply_priority_guard(text, turn_decision, user_message) or "").strip()
            except Exception:
                pass

        text = self._maybe_enforce_main_followup_alignment(
            user_profile=user_profile,
            user_message=user_message,
            final_response=text,
            turn_decision=turn_decision,
            collection_result=collection_result,
        )
        return str(text or "").strip()

    def _build_alignment_fallback_response(
        self,
        *,
        user_profile: UserProfile,
        user_message: str,
        ask_field: str,
        allow_medium_target: bool,
    ) -> str:
        builder = getattr(self.host, "_build_budget_guard_fallback_response", None)
        if not callable(builder):
            return ""
        try:
            return str(
                builder(
                    user_profile=user_profile,
                    user_message=user_message,
                    ask_field=ask_field,
                    allow_medium_target=allow_medium_target,
                )
                or ""
            ).strip()
        except Exception:
            return ""

    def _style_preserving_fallback(
        self,
        *,
        original_response: str,
        fallback_response: str,
    ) -> str:
        if not str(fallback_response or "").strip():
            return str(original_response or "").strip()
        style_builder = getattr(self.host, "_build_style_preserving_followup_response", None)
        if not callable(style_builder):
            return str(fallback_response or "").strip()
        try:
            return str(
                style_builder(
                    original_response=original_response,
                    fallback_response=fallback_response,
                )
                or ""
            ).strip() or str(fallback_response or "").strip()
        except Exception:
            return str(fallback_response or "").strip()

    def _reset_turn_alignment_obs(self) -> None:
        self.host._last_turn_alignment_obs = {
            "ask_field": "-",
            "asked_fields": "-",
            "ask_field_mismatch_detected": False,
            "ask_field_mismatch_rewritten": False,
            "reask_after_commit_detected": False,
        }

    def _update_turn_alignment_obs(self, **kwargs: Any) -> None:
        current = getattr(self.host, "_last_turn_alignment_obs", None)
        if not isinstance(current, dict):
            self._reset_turn_alignment_obs()
            current = getattr(self.host, "_last_turn_alignment_obs", None)
        if not isinstance(current, dict):
            return
        current.update(kwargs)

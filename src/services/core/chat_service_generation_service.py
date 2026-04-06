import time
from typing import Any, Dict

from src.models.user_profile import UserProfile
from src.modules.conversation.domain.turn_decision import TurnDecision
from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingResult
from src.services.core.chat_service_models import (
    CollectionPhaseOutcome,
    GenerationCollectionPhaseOutcome,
)


class ChatServiceGenerationService:
    def __init__(self, host: Any) -> None:
        self.host = host

    async def generate_turn_response_text(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        main_prompt: str,
        turn_decision: TurnDecision,
        conversation_context: Dict[str, Any],
    ) -> tuple[str, bool, str]:
        opening_intent_detection_enabled = self.host._should_run_opening_intent_detection(
            conversation_context,
            user_profile,
        ) and turn_decision.response_channel == "model"
        self.host._last_opening_intent_signal = None
        self.host._last_unified_generation_record = None
        ai_response = await self.host._call_ai(main_prompt, account_id, user_message)
        infra_fail = False
        infra_fail_reason = ""
        if not ai_response:
            infra_fail = True
            infra_fail_reason = getattr(self.host, "_last_ai_failure_reason", None) or "ai_empty_response"
            self.host._last_opening_intent_signal = None
        elif turn_decision.response_channel == "model":
            self.host._last_opening_intent_signal = None
        else:
            self.host._last_opening_intent_signal = None
        return ai_response, infra_fail, infra_fail_reason

    async def process_collection_phase(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        extracted_data: Dict[str, Any],
        extraction_meta: Dict[str, Any],
        user_message: str,
        message_count: int,
        understanding_result: TurnUnderstandingResult,
        conversation_context: Dict[str, Any],
        turn_decision: TurnDecision,
        ai_response: str,
    ) -> CollectionPhaseOutcome:
        contact_gate_before = self.host.collection_policy.can_enter_contact(user_profile)
        profile_result = await self.host.profile_collection_coordinator.process_collection(
            account_id,
            user_profile,
            extracted_data,
            user_message,
            extraction_meta=extraction_meta,
            turn_id=message_count + 1,
            understanding_result=understanding_result,
        )
        collection_result = profile_result.collection_result
        extracted_fields_count = len(collection_result.get("all_fields", []))

        for field_info in collection_result.get("all_fields", []):
            if field_info.get("field") == "partner_requirement":
                latest_profile = await self.host.user_service.get_user_profile(account_id)
                latest_profile.close_active_ask("partner_requirement")
                await self.host.user_service.save_user_profile(account_id, latest_profile)
                user_profile = latest_profile
                await self.host.input_fallback_service.reset_confirm_count(account_id)
                break

        user_profile = await self.host.user_service.get_user_profile(account_id)
        refreshed_decision = turn_decision
        response_channel = turn_decision.response_channel
        refreshed_ai_response = ai_response
        if turn_decision.response_channel == "model":
            refreshed_ai_response, refreshed_decision = await self.host.refresh_turn_decision_after_collection(
                ai_response=ai_response,
                account_id=account_id,
                user_message=user_message,
                user_profile=user_profile,
                conversation_context=conversation_context,
                understanding_result=understanding_result,
                previous_turn_decision=turn_decision,
                collection_result=collection_result,
            )
            response_channel = refreshed_decision.response_channel
        _ = self.host.profile_collection_coordinator.build_contact_decision(user_profile, user_message)
        return CollectionPhaseOutcome(
            user_profile=user_profile,
            collection_result=collection_result,
            ai_response=refreshed_ai_response,
            turn_decision=refreshed_decision,
            response_channel=response_channel,
            extracted_fields_count=extracted_fields_count,
            contact_gate_before=contact_gate_before,
        )

    async def run_generation_collection_phase(
        self,
        *,
        account_id: str,
        user_profile: UserProfile,
        user_message: str,
        dialog_id: str,
        main_prompt: str,
        last_response: str,
        message_count: int,
        understanding_result: TurnUnderstandingResult,
        conversation_context: Dict[str, Any],
        turn_decision: TurnDecision,
    ) -> GenerationCollectionPhaseOutcome:
        phase_begin = time.perf_counter()
        ai_response, infra_fail, infra_fail_reason = await self.host.generate_turn_response_text(
            account_id=account_id,
            user_profile=user_profile,
            user_message=user_message,
            main_prompt=main_prompt,
            turn_decision=turn_decision,
            conversation_context=conversation_context,
        )
        ai_call_ms = int((time.perf_counter() - phase_begin) * 1000)

        phase_begin = time.perf_counter()
        extracted_data, extraction_meta = await self.host.extract_and_merge_generated_fields(
            ai_response=ai_response,
            user_message=user_message,
            last_response=last_response,
            user_profile=user_profile,
            understanding_result=understanding_result,
            infra_fail=infra_fail,
        )
        extract_fuse_ms = int((time.perf_counter() - phase_begin) * 1000)

        phase_begin = time.perf_counter()
        collection_phase = await self.host.process_collection_phase(
            account_id=account_id,
            user_profile=user_profile,
            extracted_data=extracted_data,
            extraction_meta=extraction_meta,
            user_message=user_message,
            message_count=message_count,
            understanding_result=understanding_result,
            conversation_context=conversation_context,
            turn_decision=turn_decision,
            ai_response=ai_response,
        )
        collection_process_ms = int((time.perf_counter() - phase_begin) * 1000)

        preset_payload = await self.host.maybe_build_preset_response_payload(
            account_id=account_id,
            user_profile=collection_phase.user_profile,
            user_message=user_message,
            dialog_id=dialog_id,
            collection_result=collection_phase.collection_result,
        )
        return GenerationCollectionPhaseOutcome(
            user_profile=collection_phase.user_profile,
            ai_response=collection_phase.ai_response,
            infra_fail=infra_fail,
            infra_fail_reason=infra_fail_reason,
            collection_result=collection_phase.collection_result,
            turn_decision=collection_phase.turn_decision,
            response_channel=collection_phase.response_channel,
            extracted_fields_count=collection_phase.extracted_fields_count,
            contact_gate_before=collection_phase.contact_gate_before,
            preset_payload=preset_payload,
            ai_call_ms=ai_call_ms,
            extract_fuse_ms=extract_fuse_ms,
            collection_process_ms=collection_process_ms,
        )

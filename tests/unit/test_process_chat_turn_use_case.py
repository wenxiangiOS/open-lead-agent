import pytest

from src.modules.conversation.application.process_chat_turn import ProcessChatTurnUseCase
from src.models.requests import ChatRequest
from src.models.user_profile import UserProfile
from src.services.core.chat_service_models import AlreadyEndedPreparation, PreGenerationResolutionMeta


class _EndedUserService:
    def __init__(self):
        self.profile = UserProfile(account_id="u_ended")
        self.profile.conversation_ended = True

    async def get_user_profile(self, account_id):
        return self.profile

    async def save_user_profile(self, account_id, profile):
        self.profile = profile


class _EndedDialogueManager:
    def __init__(self, recent_responses=None):
        self.recent_responses = list(recent_responses or [])

    async def get_message_count(self, account_id):
        return 3

    async def get_conversation_context(self, account_id):
        return {"recent_responses": list(self.recent_responses), "message_count": 3}


class _EndedFallbackService:
    async def reset_nonsense_count(self, account_id):
        return None


class _EndedEndingService:
    def get_ending_response(self, scenario_name):
        assert scenario_name == "already_ended"
        return "行，那先聊到这儿。"


class _EndedChatService:
    def __init__(self, recent_responses=None):
        self.user_service = _EndedUserService()
        self.dialogue_manager = _EndedDialogueManager(recent_responses=recent_responses)
        self.input_fallback_service = _EndedFallbackService()
        self.ending_service = _EndedEndingService()
        self.updated = None

    @staticmethod
    def _sanitize_robotic_tone(response):
        return response

    async def _build_chat_response(
        self,
        account_id,
        user_profile,
        response,
        collection_result,
        dialog_id,
        field_ask_count_before=None,
        response_route=None,
    ):
        return {
            "success": True,
            "response": response,
            "dialogId": dialog_id,
            "collected_info": {"contact": "未留"},
            "meta": {"ending": collection_result.get("ending_info", {})},
        }

    async def _update_conversation_state(self, account_id, question, final_response, raw_response, track_asked_fields=False):
        self.updated = (account_id, question, final_response, raw_response, track_asked_fields)

    async def maybe_build_already_ended_payload(
        self,
        *,
        account_id,
        user_profile,
        user_message,
        dialog_id,
        is_new_user_session,
    ):
        if is_new_user_session:
            return None
        recent_responses = list(self.dialogue_manager.recent_responses)
        base_response = self.ending_service.get_ending_response("already_ended")
        normalized = str(user_message or "").strip().lower()
        if normalized in {"好", "好的", "嗯", "嗯嗯", "ok", "okay", "收到", "行", "知道了", "好哒", "好的呢"}:
            if recent_responses[-2:] == [base_response, "嗯嗯"] or recent_responses[-2:] == [base_response, "好呀"]:
                final_response = ""
            elif recent_responses[-1:] == [base_response]:
                final_response = "好呀"
            elif recent_responses[-1:] in (["嗯嗯"], ["好呀"], ["收到啦"]):
                final_response = ""
            else:
                final_response = base_response
        else:
            final_response = base_response

        await self._update_conversation_state(
            account_id,
            user_message,
            final_response,
            final_response,
            track_asked_fields=False,
        )
        payload = await self._build_chat_response(
            account_id,
            user_profile,
            final_response,
            {"all_fields": [], "ending_info": {"scenario": "already_ended"}},
            dialog_id,
            {},
            response_route="already_ended",
        )
        return AlreadyEndedPreparation(
            route_name="already_ended",
            final_response=final_response,
            payload=payload,
        )

    def build_error_response(self, error, dialog_id, error_code=None, details=None):
        return {
            "success": False,
            "response": error,
            "dialogId": dialog_id,
            "error_code": error_code,
            "details": details,
        }


class _ModelDialogueManager:
    def update_user_sex(self, user_profile):
        return None

    async def get_message_count(self, account_id):
        return 0

    async def get_conversation_context(self, account_id):
        return {"recent_responses": [], "message_count": 0}


class _ModelUserService:
    def __init__(self):
        self.profile = UserProfile(account_id="u_model")

    async def get_user_profile(self, account_id):
        return self.profile

    async def save_user_profile(self, account_id, profile):
        self.profile = profile


class _ModelExtractionService:
    @staticmethod
    def _parse_age(text):
        return None


class _ModelChatService:
    def __init__(self):
        self.user_service = _ModelUserService()
        self.dialogue_manager = _ModelDialogueManager()
        self.input_fallback_service = _EndedFallbackService()
        self.extraction_service = _ModelExtractionService()
        self.response_payload = None
        self.state_updates = []

    async def maybe_build_already_ended_payload(self, **kwargs):
        return None

    async def prepare_turn_execution(self, **kwargs):
        class _Understanding:
            def to_dict(self):
                return {"primary_turn_type": "profile_answer"}

        class _Decision:
            prioritize_user_question = False
            primary_move = "ack_and_ask"
            in_repair_mode = False
            response_channel = "model"

            @staticmethod
            def to_log_dict():
                return {"response_channel": "model", "primary_move": "ack_and_ask"}

        profile = self.user_service.profile
        return type(
            "_Prep",
            (),
            {
                "understanding": _Understanding(),
                "decision_profile": profile,
                "turn_decision": _Decision(),
                "response_channel": "model",
                "pre_generation_resolution": PreGenerationResolutionMeta(
                    source="contextual_short_reply_backfill",
                    resolved_fields=["location"],
                    transition_reason="contextual_short_reply_backfill",
                ),
            },
        )()

    async def maybe_build_pre_generation_short_circuit_payload(self, **kwargs):
        return None, None, kwargs["user_profile"]

    async def handle_refusal_detection(self, user_message, account_id, user_profile):
        return None

    async def maybe_build_quick_faq_payload(self, **kwargs):
        return None

    async def consume_bridge_back_prefix(self, **kwargs):
        return ""

    def build_generation_prompt(self, **kwargs):
        return "prompt"

    async def run_generation_collection_phase(self, **kwargs):
        profile = kwargs["user_profile"]
        turn_decision = kwargs["turn_decision"]
        return type(
            "_GenerationPhase",
            (),
            {
                "user_profile": profile,
                "collection_result": {"all_fields": []},
                "ai_response": "AI原文",
                "turn_decision": turn_decision,
                "response_channel": "model",
                "extracted_fields_count": 0,
                "contact_gate_before": False,
                "infra_fail": False,
                "infra_fail_reason": "",
                "preset_payload": None,
                "ai_call_ms": 1,
                "extract_fuse_ms": 1,
                "collection_process_ms": 1,
            },
        )()

    async def build_enhanced_response_to_clean(self, **kwargs):
        return kwargs["ai_response"]

    async def finalize_generated_response(self, **kwargs):
        return "最终展示", True, kwargs["user_profile"]

    async def sync_post_delivery_state(self, **kwargs):
        return kwargs["final_response"], kwargs["user_profile"]

    async def build_final_turn_payload(self, **kwargs):
        self.response_payload = {
            "success": True,
            "response": kwargs["final_response"],
            "dialogId": kwargs["dialog_id"],
            "meta": {"ai_response_unified_generation": {"final_display_response": kwargs["final_response"]}},
        }
        return self.response_payload


class _QuickFaqDialogueManager(_ModelDialogueManager):
    def __init__(self, recent_responses=None, message_count=4):
        self._recent_responses = list(recent_responses or [])
        self._message_count = message_count

    async def get_message_count(self, account_id):
        return self._message_count

    async def get_conversation_context(self, account_id):
        return {"recent_responses": list(self._recent_responses), "message_count": self._message_count}


class _QuickFaqChatService(_ModelChatService):
    def __init__(self, *, response_text: str, recent_responses=None, message_count=4):
        super().__init__()
        self.dialogue_manager = _QuickFaqDialogueManager(recent_responses=recent_responses, message_count=message_count)
        self.quick_faq_response_text = response_text
        self.quick_faq_called = 0
        self.generation_called = 0

    async def prepare_turn_execution(self, **kwargs):
        class _Understanding:
            primary_turn_type = "faq_concern"
            subtype = "info_collection_why"

            def to_dict(self):
                return {"primary_turn_type": "faq_concern", "subtype": "info_collection_why"}

        class _Decision:
            prioritize_user_question = True
            primary_move = "answer_then_pause"
            in_repair_mode = False
            response_channel = "quick_faq"

            @staticmethod
            def to_log_dict():
                return {
                    "response_channel": "quick_faq",
                    "primary_move": "answer_then_pause",
                    "prioritize_user_question": True,
                }

        profile = self.user_service.profile
        return type(
            "_Prep",
            (),
            {
                "understanding": _Understanding(),
                "decision_profile": profile,
                "turn_decision": _Decision(),
                "response_channel": "quick_faq",
                "pre_generation_resolution": None,
            },
        )()

    async def maybe_build_quick_faq_payload(self, **kwargs):
        self.quick_faq_called += 1
        return {
            "success": True,
            "response": self.quick_faq_response_text,
            "dialogId": kwargs["dialog_id"],
            "meta": {},
        }

    async def run_generation_collection_phase(self, **kwargs):
        self.generation_called += 1
        return await super().run_generation_collection_phase(**kwargs)


class _ResumeAfterFaqChatService(_ModelChatService):
    def __init__(self):
        super().__init__()
        self.dialogue_manager = _QuickFaqDialogueManager(
            recent_responses=["本科学历挺好的~你现在的月收入大概在什么范围呀？"],
            message_count=4,
        )
        profile = self.user_service.profile
        profile.sex = "女"
        profile.age = 35
        profile.location = "深圳"
        profile.education = "本科"
        profile.occupation = "IT"
        profile.marital_status = "单身"
        for field in ["sex", "age", "location", "education", "occupation", "marital_status"]:
            profile.collection_progress[field] = True
        profile.last_asked_field = "monthly_income"
        self.quick_faq_called = 0
        self.generation_called = 0

    async def prepare_turn_execution(self, **kwargs):
        user_message = str(kwargs.get("user_message") or "")
        profile = self.user_service.profile

        if "清晰" in user_message:
            class _Understanding:
                primary_turn_type = "faq_concern"
                subtype = "info_collection_why"

                def to_dict(self):
                    return {"primary_turn_type": "faq_concern", "subtype": "info_collection_why"}

            class _Decision:
                prioritize_user_question = True
                primary_move = "answer_then_pause"
                in_repair_mode = False
                response_channel = "quick_faq"

                @staticmethod
                def to_log_dict():
                    return {
                        "response_channel": "quick_faq",
                        "primary_move": "answer_then_pause",
                        "prioritize_user_question": True,
                    }

            return type(
                "_Prep",
                (),
                {
                    "understanding": _Understanding(),
                    "decision_profile": profile,
                    "turn_decision": _Decision(),
                    "response_channel": "quick_faq",
                    "pre_generation_resolution": None,
                },
            )()

        class _Understanding:
            primary_turn_type = "confirmation"
            subtype = "weak_confirmation"

            def to_dict(self):
                return {"primary_turn_type": "confirmation", "subtype": "weak_confirmation"}

        class _Decision:
            prioritize_user_question = False
            primary_move = "light_followup"
            in_repair_mode = False
            response_channel = "model"

            @staticmethod
            def to_log_dict():
                return {
                    "response_channel": "model",
                    "primary_move": "light_followup",
                    "ask_field": "monthly_income",
                }

        return type(
            "_Prep",
            (),
            {
                "understanding": _Understanding(),
                "decision_profile": profile,
                "turn_decision": _Decision(),
                "response_channel": "model",
                "pre_generation_resolution": None,
            },
        )()

    async def maybe_build_quick_faq_payload(self, **kwargs):
        self.quick_faq_called += 1
        turn_decision = kwargs.get("turn_decision")
        if str(getattr(turn_decision, "response_channel", "") or "").strip() != "quick_faq":
            return None
        profile = self.user_service.profile
        profile.resume_profile_target = "monthly_income"
        profile.resume_profile_mode = "collect_profile"
        return {
            "success": True,
            "response": "这个我先说清楚，主要是怕后面把你的情况理解偏了。",
            "dialogId": kwargs["dialog_id"],
            "meta": {},
        }

    def build_generation_prompt(self, **kwargs):
        return "resume-monthly-income"

    async def run_generation_collection_phase(self, **kwargs):
        self.generation_called += 1
        profile = kwargs["user_profile"]
        turn_decision = kwargs["turn_decision"]
        return type(
            "_GenerationPhase",
            (),
            {
                "user_profile": profile,
                "collection_result": {"all_fields": []},
                "ai_response": "那我接着问下，你现在的月收入大概在什么范围呀？",
                "turn_decision": turn_decision,
                "response_channel": "model",
                "extracted_fields_count": 0,
                "contact_gate_before": False,
                "infra_fail": False,
                "infra_fail_reason": "",
                "preset_payload": None,
                "ai_call_ms": 1,
                "extract_fuse_ms": 1,
                "collection_process_ms": 1,
            },
        )()

    async def finalize_generated_response(self, **kwargs):
        profile = kwargs["user_profile"]
        profile.resume_profile_target = None
        profile.resume_profile_mode = None
        return "那我接着问下，你现在的月收入大概在什么范围呀？", True, profile


class _ShortCircuitModelChatService(_ModelChatService):
    async def maybe_build_pre_generation_short_circuit_payload(self, **kwargs):
        return (
            "divorce_incomplete",
            {
                "success": True,
                "response": "这边先到这里。",
                "dialogId": kwargs["dialog_id"],
                "meta": {"ending": {"scenario": "divorce_incomplete"}},
            },
            kwargs["user_profile"],
        )

    async def _update_conversation_state(self, account_id, question, final_response, raw_response, track_asked_fields=False):
        self.state_updates.append((account_id, question, final_response, raw_response, track_asked_fields))

    def build_error_response(self, error, dialog_id, error_code=None, details=None):
        return {
            "success": False,
            "response": error,
            "dialogId": dialog_id,
            "error_code": error_code,
            "details": details,
        }


def test_sync_payload_response_keeps_matching_response_unchanged():
    use_case = ProcessChatTurnUseCase(chat_service=object())

    payload = {
        "success": True,
        "response": "完整回复",
        "dialogId": "dlg_sync_same",
        "meta": {},
    }

    synced = use_case._sync_payload_response(payload, "完整回复")

    assert synced["response"] == "完整回复"
    assert "response_synced" not in synced["meta"]


@pytest.mark.asyncio
async def test_execute_attaches_pre_generation_resolution_meta_to_payload():
    chat_service = _ModelChatService()
    use_case = ProcessChatTurnUseCase(chat_service=chat_service)

    payload = await use_case.execute(
        ChatRequest(
            question="在南京呢",
            accountId="u_model",
            dialogId="dlg_pre_gen_meta",
        )
    )

    assert payload["success"] is True
    assert payload["response"] == "最终展示"
    assert payload["meta"]["pre_generation_resolution"] == {
        "source": "contextual_short_reply_backfill",
        "resolved_fields": ["location"],
        "transition_reason": "contextual_short_reply_backfill",
    }


@pytest.mark.asyncio
async def test_execute_attaches_pre_generation_resolution_meta_to_short_circuit_payload():
    use_case = ProcessChatTurnUseCase(_ShortCircuitModelChatService())

    payload = await use_case.execute(
        ChatRequest(
            question="还没办好",
            accountId="u_model",
            dialogId="dlg_pre_gen_short",
            sex=None,
            timestamp=None,
        )
    )

    assert payload["meta"]["route"] == "divorce_incomplete"
    assert payload["meta"]["pre_generation_resolution"] == {
        "source": "contextual_short_reply_backfill",
        "resolved_fields": ["location"],
        "transition_reason": "contextual_short_reply_backfill",
    }


def test_sync_payload_response_overrides_payload_with_final_response():
    use_case = ProcessChatTurnUseCase(chat_service=object())

    payload = {
        "success": True,
        "response": "半句",
        "dialogId": "dlg_sync_fix",
        "meta": {},
    }

    synced = use_case._sync_payload_response(payload, "完整回复")

    assert synced["response"] == "完整回复"
    assert synced["meta"]["response_synced"] is True


def test_execute_returns_already_ended_response_without_reopening_conversation():
    import asyncio

    chat_service = _EndedChatService()
    use_case = ProcessChatTurnUseCase(chat_service=chat_service)

    payload = asyncio.run(
        use_case.execute(
            ChatRequest(
                question="好",
                accountId="u_ended",
                dialogId="dlg_ended",
            )
        )
    )

    assert payload["success"] is True
    assert payload["response"] == "行，那先聊到这儿。"
    assert payload["dialogId"] == "dlg_ended"
    assert "collected_info" in payload
    assert payload["meta"]["route"] == "already_ended"
    assert chat_service.updated[-1] is False


def test_execute_uses_short_ack_for_repeated_low_info_confirmation_after_end():
    import asyncio

    chat_service = _EndedChatService(recent_responses=["行，那先聊到这儿。"])
    use_case = ProcessChatTurnUseCase(chat_service=chat_service)

    payload = asyncio.run(
        use_case.execute(
            ChatRequest(
                question="好的",
                accountId="u_ended",
                dialogId="dlg_ended_repeat",
            )
        )
    )

    assert payload["success"] is True
    assert payload["response"] in {"嗯嗯", "好呀", "收到啦"}
    assert payload["meta"]["route"] == "already_ended"


def test_execute_turns_silent_after_repeated_low_info_confirmation_after_end():
    import asyncio

    chat_service = _EndedChatService(recent_responses=["行，那先聊到这儿。", "嗯嗯"])
    use_case = ProcessChatTurnUseCase(chat_service=chat_service)

    payload = asyncio.run(
        use_case.execute(
            ChatRequest(
                question="好的",
                accountId="u_ended",
                dialogId="dlg_ended_silent",
            )
        )
    )

    assert payload["success"] is True
    assert payload["response"] == ""
    assert payload["meta"]["route"] == "already_ended"


def test_execute_model_path_keeps_final_payload_response_synced():
    import asyncio

    chat_service = _ModelChatService()
    use_case = ProcessChatTurnUseCase(chat_service=chat_service)

    payload = asyncio.run(
        use_case.execute(
            ChatRequest(
                question="我在深圳",
                accountId="u_model",
                dialogId="dlg_model",
            )
        )
    )

    assert payload["success"] is True
    assert payload["response"] == "最终展示"
    assert payload["dialogId"] == "dlg_model"
    assert payload["meta"]["route"] == "model"
    assert payload["meta"]["ai_response_unified_generation"]["final_display_response"] == "最终展示"


@pytest.mark.asyncio
async def test_execute_returns_quick_faq_payload_without_falling_through_generation():
    chat_service = _QuickFaqChatService(
        response_text="这个我先说清楚，主要是怕后面把你的情况理解偏了。",
        recent_responses=["本科学历挺好的~你现在的月收入大概在什么范围呀？"],
        message_count=4,
    )
    use_case = ProcessChatTurnUseCase(chat_service=chat_service)

    payload = await use_case.execute(
        ChatRequest(
            question="为啥要问这么清晰呢",
            accountId="u_quick_faq",
            dialogId="dlg_quick_faq",
        )
    )

    assert payload["success"] is True
    assert payload["response"] == "这个我先说清楚，主要是怕后面把你的情况理解偏了。"
    assert payload["meta"]["route"] == "quick_faq"
    assert payload["meta"]["turn_understanding"] == {
        "primary_turn_type": "faq_concern",
        "subtype": "info_collection_why",
    }
    assert chat_service.quick_faq_called == 1
    assert chat_service.generation_called == 0


@pytest.mark.asyncio
async def test_execute_model_route_still_runs_after_quick_faq_turn():
    quick_faq_service = _QuickFaqChatService(
        response_text="这个我先说清楚，主要是怕后面把你的情况理解偏了。",
        recent_responses=["本科学历挺好的~你现在的月收入大概在什么范围呀？"],
        message_count=4,
    )
    use_case = ProcessChatTurnUseCase(chat_service=quick_faq_service)

    quick_payload = await use_case.execute(
        ChatRequest(
            question="为啥要问这么清晰呢",
            accountId="u_quick_faq_resume",
            dialogId="dlg_quick_faq_resume_1",
        )
    )
    assert quick_payload["meta"]["route"] == "quick_faq"

    model_service = _ModelChatService()
    model_service.user_service.profile.account_id = "u_quick_faq_resume"
    model_use_case = ProcessChatTurnUseCase(chat_service=model_service)

    model_payload = await model_use_case.execute(
        ChatRequest(
            question="好的",
            accountId="u_quick_faq_resume",
            dialogId="dlg_quick_faq_resume_2",
        )
    )

    assert model_payload["success"] is True
    assert model_payload["meta"]["route"] == "model"
    assert model_payload["response"] == "最终展示"


@pytest.mark.asyncio
async def test_execute_restores_monthly_income_after_quick_faq_confirmation():
    chat_service = _ResumeAfterFaqChatService()
    use_case = ProcessChatTurnUseCase(chat_service=chat_service)

    faq_payload = await use_case.execute(
        ChatRequest(
            question="为啥要问这么清晰呢",
            accountId="u_resume_after_faq_e2e",
            dialogId="dlg_resume_after_faq_1",
        )
    )

    assert faq_payload["success"] is True
    assert faq_payload["meta"]["route"] == "quick_faq"
    assert "理解偏了" in faq_payload["response"]
    assert chat_service.user_service.profile.resume_profile_target == "monthly_income"
    assert chat_service.quick_faq_called == 1
    assert chat_service.generation_called == 0

    resume_payload = await use_case.execute(
        ChatRequest(
            question="好的",
            accountId="u_resume_after_faq_e2e",
            dialogId="dlg_resume_after_faq_2",
        )
    )

    assert resume_payload["success"] is True
    assert resume_payload["meta"]["route"] == "model"
    assert "月收入" in resume_payload["response"]
    assert "电话" not in resume_payload["response"]
    assert chat_service.generation_called == 1
    assert chat_service.user_service.profile.resume_profile_target is None

from typing import Any

ASK_GUARD_CORE_FIELDS = {"sex", "age", "education", "occupation", "location", "marital_status"}
ASK_GUARD_MEDIUM_FIELDS = {"monthly_income", "partner_requirement"}


class ChatServiceTurnTextPolicyService:
    def __init__(self, host: Any) -> None:
        self.host = host

    @staticmethod
    def _preferred_side_target(main_target: str | None, side_target: str | None) -> str | None:
        main = str(main_target or "").strip()
        resolved = str(side_target or "").strip()
        if main == "education":
            return "marital_status"
        if main == "location":
            return "marital_status"
        if main == "marital_status":
            return "partner_requirement"
        if resolved:
            return resolved
        if main == "occupation":
            return "monthly_income"
        return resolved or None

    def apply_humanlike_turn_structure_policy(
        self,
        response: str,
        user_profile,
        user_message: str = "",
        *,
        allow_medium_target: bool = True,
    ) -> str:
        text = str(response or "").strip()
        if not text or user_profile.conversation_ended:
            return text

        asked_fields = self.host._detect_asked_fields_in_response(text)
        if not asked_fields:
            return text

        recent_asked_fields = list(getattr(user_profile, "recent_asked_fields", []) or [])
        last_asked_field = recent_asked_fields[-1] if recent_asked_fields else None

        if (
            last_asked_field
            and last_asked_field in (ASK_GUARD_CORE_FIELDS | ASK_GUARD_MEDIUM_FIELDS)
            and last_asked_field in asked_fields
        ):
            policy_decision = self.host.collection_policy.decide(
                user_profile,
                user_message=user_message,
                allow_contact_target=False,
                allow_medium_target=allow_medium_target,
            )
            return self.host._build_interleaving_seed_for_model_rewrite(
                user_profile,
                user_message,
                main_target=policy_decision.main_target,
                preferred_side_target=self._preferred_side_target(
                    policy_decision.main_target,
                    policy_decision.side_target,
                ),
                allow_medium_target=allow_medium_target,
            )

        recent_core_streak = self.host._get_recent_core_streak(user_profile)
        asks_core_only = bool(asked_fields & ASK_GUARD_CORE_FIELDS) and not bool(
            asked_fields & ASK_GUARD_MEDIUM_FIELDS
        )
        single_core_asked_field = (
            next(iter(asked_fields & ASK_GUARD_CORE_FIELDS))
            if len(asked_fields & ASK_GUARD_CORE_FIELDS) == 1
            else None
        )
        policy_decision = self.host.collection_policy.decide(
            user_profile,
            user_message=user_message,
            allow_contact_target=False,
            allow_medium_target=allow_medium_target,
        )
        interleave_main_target = str(
            single_core_asked_field or policy_decision.main_target or ""
        ).strip()
        if asks_core_only and interleave_main_target in {"education", "location"}:
            return self.host._build_interleaving_seed_for_model_rewrite(
                user_profile,
                user_message,
                main_target=interleave_main_target,
                preferred_side_target="marital_status",
                allow_medium_target=allow_medium_target,
            )
        if (
            asks_core_only
            and interleave_main_target in {"education", "occupation"}
            and self.host._should_allow_interleaving_followup(
                user_profile,
                interleave_main_target,
                self._preferred_side_target(
                    interleave_main_target,
                    policy_decision.side_target,
                ),
                allow_medium_target=allow_medium_target,
            )
        ):
            return self.host._build_interleaving_seed_for_model_rewrite(
                user_profile,
                user_message,
                main_target=interleave_main_target,
                preferred_side_target=self._preferred_side_target(
                    interleave_main_target,
                    policy_decision.side_target,
                ),
                allow_medium_target=allow_medium_target,
            )

        if recent_core_streak >= 3 and asks_core_only and self.host._should_allow_interleaving_followup(
            user_profile,
            interleave_main_target,
            self._preferred_side_target(
                interleave_main_target,
                policy_decision.side_target,
            ),
            allow_medium_target=allow_medium_target,
        ):
            return self.host._build_interleaving_seed_for_model_rewrite(
                user_profile,
                user_message,
                main_target=interleave_main_target,
                preferred_side_target=self._preferred_side_target(
                    interleave_main_target,
                    policy_decision.side_target,
                ),
                allow_medium_target=allow_medium_target,
            )

        return text

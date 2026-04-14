from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from src.models.user_profile import UserProfile
from src.modules.conversation.domain.turn_decision import TurnDecision
from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingResult


@dataclass
class ResumeAfterFaqPlan:
    field: Optional[str]
    source: Optional[str] = None


@dataclass
class FollowupFieldPlan:
    main_target: Optional[str]
    side_target: Optional[str]


class FollowupPlanningLayer:
    """统一处理字段追问和 FAQ 后恢复主线。"""

    def __init__(self, policy=None) -> None:
        self.policy = policy

    def choose_side_target(
        self,
        *,
        profile: UserProfile,
        main_target: Optional[str],
        user_message: str = "",
        message_count: int = 0,
        allow_medium_target: bool = True,
        understanding_result: Optional[TurnUnderstandingResult] = None,
    ) -> Optional[str]:
        if self.policy is None:
            return None
        if not allow_medium_target:
            return None
        if main_target == "contact":
            return None

        remaining_core_fields = [
            field for field in self.policy.get_uncovered_core_fields(profile) if field != main_target
        ]
        if remaining_core_fields and not self.policy._allow_early_side_target(  # noqa: SLF001
            profile,
            main_target=main_target,
            user_message=user_message,
            message_count=message_count,
            understanding_result=understanding_result,
        ):
            return None
        if message_count and message_count <= 4:
            if not self.policy._has_profile_context_signal(  # noqa: SLF001
                user_message,
                understanding_result=understanding_result,
            ):
                return None

        cue_order = self.policy._get_profile_context_cue_order(  # noqa: SLF001
            user_message,
            understanding_result=understanding_result,
        )
        best_field: Optional[str] = None
        best_score = -1
        for field in ("monthly_income", "marital_status", "partner_requirement"):
            score = self.policy._score_side_target_candidate(  # noqa: SLF001
                profile,
                field=field,
                main_target=main_target,
                user_message=user_message,
                message_count=message_count,
                cue_order=cue_order,
            )
            if score > best_score:
                best_score = score
                best_field = field

        return best_field if best_score > 0 else None

    def choose_followup_targets(
        self,
        *,
        profile: UserProfile,
        can_enter_contact: bool,
        allow_contact_target: bool,
        allow_medium_target: bool,
        user_message: str = "",
        message_count: int = 0,
        understanding_result: Optional[TurnUnderstandingResult] = None,
    ) -> FollowupFieldPlan:
        main_target = self.choose_main_target(
            profile=profile,
            can_enter_contact=can_enter_contact,
            allow_contact_target=allow_contact_target,
            user_message=user_message,
            message_count=message_count,
            understanding_result=understanding_result,
        )
        side_target = self.choose_side_target(
            profile=profile,
            main_target=main_target,
            user_message=user_message,
            message_count=message_count,
            allow_medium_target=allow_medium_target,
            understanding_result=understanding_result,
        )
        return FollowupFieldPlan(main_target=main_target, side_target=side_target)

    def choose_main_target(
        self,
        *,
        profile: UserProfile,
        can_enter_contact: bool,
        allow_contact_target: bool,
        user_message: str = "",
        message_count: int = 0,
        understanding_result: Optional[TurnUnderstandingResult] = None,
    ) -> Optional[str]:
        if self.policy is None:
            return None

        contextual_core_target = self.policy._get_contextual_core_target(  # noqa: SLF001
            profile,
            user_message=user_message,
            message_count=message_count,
            understanding_result=understanding_result,
        )
        if contextual_core_target and self.policy.can_actively_ask(profile, contextual_core_target):
            return contextual_core_target

        for field in self.policy._get_priority_order(profile):  # noqa: SLF001
            if field == "contact":
                if not allow_contact_target or not can_enter_contact:
                    continue
            if field != "contact" and self.policy.is_field_covered(profile, field):
                continue
            if self.policy.can_actively_ask(profile, field):
                return field

        return None

    def resolve_resume_after_faq(
        self,
        *,
        understanding: TurnUnderstandingResult,
        turn_decision: TurnDecision,
        user_profile: UserProfile,
        decision_profile: Optional[UserProfile],
        user_message: str,
        last_response: str,
        resolve_interrupted_followup_field: Callable[..., Optional[str]],
        is_field_covered: Callable[[UserProfile, str], bool],
    ) -> ResumeAfterFaqPlan:
        if not getattr(understanding, "post_answer_reentry", False):
            return ResumeAfterFaqPlan(field=None)
        if turn_decision.ask_field and not turn_decision.prioritize_user_question:
            return ResumeAfterFaqPlan(field=None)

        candidate_profiles = []
        if decision_profile is not None:
            candidate_profiles.append(("decision_profile", decision_profile))
        candidate_profiles.append(("user_profile", user_profile))

        def _needs_resume(profile: UserProfile, field: Optional[str]) -> bool:
            candidate = str(field or "").strip()
            if not candidate or candidate == "contact":
                return False
            medium_fields = set(getattr(self.policy, "MEDIUM_FIELDS", []) or []) if self.policy is not None else {
                "monthly_income",
                "partner_requirement",
            }
            if candidate in medium_fields:
                if self.policy is not None:
                    return not self.policy.is_collected(profile, candidate)
                return not bool(str(getattr(profile, candidate, "") or "").strip())
            return not is_field_covered(profile, candidate)

        for label, profile in candidate_profiles:
            interrupted = resolve_interrupted_followup_field(
                profile,
                last_response=last_response,
                fallback_user_message=user_message,
            )
            if _needs_resume(profile, interrupted):
                return ResumeAfterFaqPlan(field=interrupted, source=f"{label}.last_asked_field")

            explicit_target = str(getattr(profile, "resume_profile_target", "") or "").strip()
            if _needs_resume(profile, explicit_target):
                return ResumeAfterFaqPlan(field=explicit_target, source=f"{label}.resume_profile_target")

        return ResumeAfterFaqPlan(field=None)

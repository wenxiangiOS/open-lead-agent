from src.models.user_profile import UserProfile
from src.modules.conversation.domain.turn_decision import TurnDecision
from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingResult
from src.modules.conversation_understanding.domain.followup_planning_layer import (
    FollowupPlanningLayer,
)
from src.modules.profile_collection.domain.profile_collection_policy import ProfileCollectionPolicy


def test_followup_planning_layer_restores_monthly_income_after_faq_confirmation():
    planner = FollowupPlanningLayer()
    profile = UserProfile(account_id="u_followup_resume")
    profile.set_last_asked_field("monthly_income", 4)

    plan = planner.resolve_resume_after_faq(
        understanding=TurnUnderstandingResult(primary_turn_type="confirmation", post_answer_reentry=True),
        turn_decision=TurnDecision(intent="confirmation", prioritize_user_question=True),
        user_profile=profile,
        decision_profile=None,
        user_message="好的",
        last_response="我知道你会在意问得太细这件事，我们会严格保密的。",
        resolve_interrupted_followup_field=lambda *_args, **_kwargs: "monthly_income",
        is_field_covered=lambda _profile, field: field != "monthly_income",
    )

    assert plan.field == "monthly_income"
    assert plan.source == "user_profile.last_asked_field"


def test_profile_collection_policy_side_target_selection_is_routed_by_followup_planner():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_followup_side")
    profile.sex = "女"
    profile.age = 35
    profile.location = "深圳"
    profile.occupation = "IT"
    for field in ("sex", "age", "location", "occupation"):
        profile.collection_progress[field] = True

    side_target = policy.get_side_target(
        profile,
        main_target="education",
        user_message="深圳，做IT",
        message_count=3,
    )

    assert side_target in {"monthly_income", "marital_status"}


def test_profile_collection_policy_main_target_selection_is_routed_by_followup_planner():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_followup_main")
    profile.collection_progress["sex"] = True
    profile.sex = "女"

    main_target = policy.get_main_target(
        profile,
        can_enter_contact=False,
        allow_contact_target=False,
        user_message="我在深圳做IT",
        message_count=2,
    )

    assert main_target == "occupation"


def test_followup_planning_layer_returns_main_and_side_targets_together():
    policy = ProfileCollectionPolicy()
    planner = policy.followup_planning_layer
    profile = UserProfile(account_id="u_followup_bundle")

    plan = planner.choose_followup_targets(
        profile=profile,
        can_enter_contact=False,
        allow_contact_target=False,
        allow_medium_target=True,
        user_message="我在深圳",
        message_count=0,
    )

    assert plan.main_target == "occupation"
    assert plan.side_target == "marital_status"


def test_profile_collection_policy_prefers_unified_understanding_for_contextual_main_target():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_followup_unified_main")
    profile.collection_progress["sex"] = True
    profile.sex = "女"
    understanding = TurnUnderstandingResult(
        primary_turn_type="faq_concern",
        subtype="fee",
        resolved_slots={"location": "深圳龙华", "occupation": "在编教师"},
    )

    main_target = policy.get_main_target(
        profile,
        can_enter_contact=False,
        allow_contact_target=False,
        user_message="怎么收费呢先了解下",
        message_count=2,
        understanding_result=understanding,
    )

    assert main_target == "occupation"


def test_followup_planning_layer_uses_unified_understanding_for_early_side_target_gate():
    policy = ProfileCollectionPolicy()
    profile = UserProfile(account_id="u_followup_unified_side")
    profile.sex = "女"
    profile.age = 30
    profile.location = "深圳"
    profile.occupation = "教师"
    for field in ("sex", "age", "location", "occupation"):
        profile.collection_progress[field] = True
    understanding = TurnUnderstandingResult(
        primary_turn_type="faq_concern",
        subtype="fee",
        resolved_slots={"location": "深圳龙华", "occupation": "在编教师"},
    )

    side_target = policy.get_side_target(
        profile,
        main_target="education",
        user_message="怎么收费呢先了解下",
        message_count=3,
        understanding_result=understanding,
    )

    assert side_target in {"monthly_income", "marital_status"}

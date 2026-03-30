"""Profile collection policy unit tests."""

from src.models.user_profile import UserProfile
from src.services.collection.profile_collection_policy import ProfileCollectionPolicy


class TestProfileCollectionPolicy:
    """Test updated coverage/profile/contact policy."""

    def setup_method(self):
        self.policy = ProfileCollectionPolicy()

    @staticmethod
    def _mark_collected(profile: UserProfile, *fields: str):
        for field in fields:
            profile.collection_progress[field] = True
            setattr(profile, field, getattr(profile, field, None) or field)

    def test_main_target_starts_from_core_fields(self):
        profile = UserProfile(account_id="u1")

        decision = self.policy.decide(profile, user_message="你好")

        assert decision.main_target == "sex"
        assert decision.next_mode == "collect_core"
        assert decision.can_enter_contact is False

    def test_core_main_order_allows_small_variation_after_sex(self):
        profile_a = UserProfile(account_id="u_a")
        profile_b = UserProfile(account_id="u_b")
        profile_a.collection_progress["sex"] = True
        profile_b.collection_progress["sex"] = True
        profile_a.sex = "男"
        profile_b.sex = "男"

        target_a = self.policy.get_main_target(profile_a, can_enter_contact=False, allow_contact_target=False)
        target_b = self.policy.get_main_target(profile_b, can_enter_contact=False, allow_contact_target=False)

        assert target_a in {"age", "location", "education"}
        assert target_b in {"age", "location", "education"}

    def test_core_field_is_covered_after_two_attempts_even_if_not_collected(self):
        profile = UserProfile(account_id="u1")
        profile.field_ask_count["age"] = 2

        assert self.policy.is_core_field_covered(profile, "age") is True

    def test_medium_field_is_covered_after_one_attempt_even_if_not_collected(self):
        profile = UserProfile(account_id="u1")
        profile.field_ask_count["partner_requirement"] = 1

        assert self.policy.is_medium_field_covered(profile, "partner_requirement") is True

    def test_coverage_not_complete_when_medium_field_never_asked(self):
        profile = UserProfile(account_id="u1")
        self._mark_collected(profile, "sex", "age", "location", "education", "occupation")
        profile.field_ask_count["marital_status"] = 1
        profile.field_ask_count["monthly_income"] = 1

        assert self.policy.is_coverage_complete(profile) is False
        assert self.policy.get_uncovered_medium_fields(profile) == ["partner_requirement"]

    def test_collect_medium_forces_partner_requirement_when_core_covered(self):
        profile = UserProfile(account_id="u1")
        self._mark_collected(profile, "sex", "age", "location", "education", "occupation")
        profile.field_ask_count["marital_status"] = 1
        profile.field_ask_count["monthly_income"] = 1

        decision = self.policy.decide(profile, user_message="是的", message_count=6)

        assert decision.next_mode == "collect_medium"
        assert decision.main_target == "partner_requirement"
        assert decision.forced_cover_target == "partner_requirement"
        assert decision.allow_contact_push is False

    def test_contact_requires_coverage_and_minimum_profile_success(self):
        profile = UserProfile(account_id="u1")
        self._mark_collected(profile, "sex", "age", "location")
        profile.field_ask_count["education"] = 2
        profile.field_ask_count["occupation"] = 2
        profile.field_ask_count["marital_status"] = 1
        profile.field_ask_count["partner_requirement"] = 1
        profile.field_ask_count["monthly_income"] = 1

        decision = self.policy.decide(profile, user_message="嗯", message_count=7)

        assert decision.coverage_passed is True
        assert decision.profile_sufficient is True
        assert decision.can_enter_contact is True

    def test_contact_blocked_when_coverage_done_but_profile_insufficient(self):
        profile = UserProfile(account_id="u1")
        self._mark_collected(profile, "sex", "age")
        profile.field_ask_count["location"] = 2
        profile.field_ask_count["education"] = 2
        profile.field_ask_count["occupation"] = 2
        profile.field_ask_count["marital_status"] = 1
        profile.field_ask_count["partner_requirement"] = 1
        profile.field_ask_count["monthly_income"] = 1

        decision = self.policy.decide(profile, user_message="嗯", message_count=7)

        assert decision.coverage_passed is True
        assert decision.profile_sufficient is False
        assert decision.next_mode == "open_profile_repair"
        assert decision.allow_contact_push is False

    def test_contact_instruction_allowed_after_all_gates_pass(self):
        profile = UserProfile(account_id="u1")
        self._mark_collected(profile, "sex", "age", "location")
        profile.field_ask_count["education"] = 2
        profile.field_ask_count["occupation"] = 2
        profile.field_ask_count["marital_status"] = 1
        profile.field_ask_count["partner_requirement"] = 1
        profile.field_ask_count["monthly_income"] = 1

        assert self.policy.should_allow_contact_instruction(profile, "ASK_PHONE") is True

    def test_contact_instruction_blocked_before_coverage_ready(self):
        profile = UserProfile(account_id="u1")
        self._mark_collected(profile, "sex", "age", "location", "education", "occupation")

        assert self.policy.should_allow_contact_instruction(profile, "ASK_PHONE") is False

    def test_opening_with_location_and_occupation_prefers_low_pressure_missing_core(self):
        profile = UserProfile(account_id="u_opening_profile")

        decision = self.policy.decide(
            profile,
            user_message="我是深圳的，我做IT",
            message_count=0,
        )

        assert decision.main_target in {"age", "education", "sex"}

    def test_opening_with_location_prefers_occupation_with_income_side_target(self):
        profile = UserProfile(account_id="u_opening_location")

        decision = self.policy.decide(
            profile,
            user_message="我是深圳的",
            message_count=0,
        )

        assert decision.main_target == "occupation"
        assert decision.side_target == "monthly_income"

    def test_followup_with_education_allows_early_marital_side_target(self):
        profile = UserProfile(account_id="u_followup_education_marital")
        profile.sex = "男"
        profile.collection_progress["sex"] = True

        decision = self.policy.decide(
            profile,
            user_message="本科",
            message_count=2,
        )

        assert decision.main_target in {"age", "location", "occupation", "education"}
        if decision.main_target == "occupation":
            assert decision.side_target in {"monthly_income", "marital_status", "partner_requirement"}

    def test_education_does_not_side_ask_partner_requirement_even_when_allowed(self):
        profile = UserProfile(account_id="u_education_no_partner_side")
        profile.sex = "男"
        profile.age = 36
        profile.location = "深圳"
        profile.occupation = "IT"
        profile.monthly_income = "6万"
        for field in ["sex", "age", "location", "occupation", "monthly_income"]:
            profile.collection_progress[field] = True

        decision = self.policy.decide(
            profile,
            user_message="it，大概6万",
            message_count=4,
        )

        assert decision.main_target == "education"
        assert decision.side_target == "partner_requirement"

    def test_latest_location_cue_on_followup_prefers_occupation_over_global_order(self):
        profile = UserProfile(account_id="u_latest_location")

        decision = self.policy.decide(
            profile,
            user_message="男的呢，在深圳",
            message_count=2,
        )

        assert decision.main_target == "occupation"

    def test_latest_location_and_occupation_opening_prefers_low_pressure_core(self):
        profile = UserProfile(account_id="u_latest_location_occupation")

        decision = self.policy.decide(
            profile,
            user_message="90后，深圳，做IT",
            message_count=0,
        )

        assert decision.main_target in {"age", "education", "sex"}

    def test_cost_control_light_mode_after_repeated_non_cooperation(self):
        profile = UserProfile(account_id="u1")
        profile.non_cooperation_turns = 3

        decision = self.policy.decide(profile, user_message="嗯", message_count=8)

        assert decision.engagement_mode == "light"
        assert decision.next_mode == "low_pressure_chat"

    def test_turn_quality_blocks_contact_push_on_faq_turn(self):
        profile = UserProfile(account_id="u1")
        self._mark_collected(profile, "sex", "age", "location")
        profile.field_ask_count["education"] = 2
        profile.field_ask_count["occupation"] = 2
        profile.field_ask_count["marital_status"] = 1
        profile.field_ask_count["partner_requirement"] = 1
        profile.field_ask_count["monthly_income"] = 1

        decision = self.policy.decide(
            profile,
            user_message="怎么收费",
            message_count=7,
            prioritize_user_question=True,
            primary_move="answer_then_pause",
        )

        assert decision.can_enter_contact is True
        assert decision.turn_quality_passed is False
        assert decision.allow_contact_push is False
        assert decision.next_mode == "contact_hold"

    def test_ongoing_contact_flow_freezes_profile_collection(self):
        profile = UserProfile(account_id="u1")
        self._mark_collected(profile, "sex", "age", "location", "education", "occupation")
        profile.field_ask_count["marital_status"] = 1
        profile.phone_ask_count = 1

        decision = self.policy.decide(profile, user_message="嗯", message_count=8)

        assert decision.next_mode == "contact_flow"
        assert decision.main_target == "contact"
        assert decision.forced_cover_target is None
        assert decision.reason == "ongoing_contact_flow_freeze_profile_collection"

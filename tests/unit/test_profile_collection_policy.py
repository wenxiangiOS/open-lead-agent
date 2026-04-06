"""Profile collection policy unit tests."""

from src.models.user_profile import UserProfile
from src.modules.conversation.domain.turn_understanding_models import TurnUnderstandingResult
from src.modules.profile_collection.domain.profile_collection_policy import ProfileCollectionPolicy


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

    def test_can_enter_contact_requires_monthly_income_even_when_other_medium_fields_are_ready(self):
        profile = UserProfile(account_id="u_contact_income_gate")
        self._mark_collected(profile, "sex", "age", "location", "education", "occupation", "marital_status", "partner_requirement")

        assert self.policy.can_enter_contact(profile) is False

        profile.monthly_income = "8万"
        profile.collection_progress["monthly_income"] = True

        assert self.policy.can_enter_contact(profile) is True

    def test_opening_with_location_and_occupation_prefers_low_pressure_missing_core(self):
        profile = UserProfile(account_id="u_opening_profile")

        decision = self.policy.decide(
            profile,
            user_message="我是深圳的，我做IT",
            message_count=0,
        )

        assert decision.main_target == "occupation"
        assert decision.side_target == "monthly_income"

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

    def test_education_prefers_marital_status_side_target_even_when_partner_requirement_allowed(self):
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
        assert decision.side_target == "marital_status"

    def test_monthly_income_can_attach_to_other_core_field_after_occupation_collected(self):
        profile = UserProfile(account_id="u_income_dynamic_host")
        profile.sex = "女"
        profile.age = 35
        profile.location = "深圳"
        profile.occupation = "IT"
        for field in ["sex", "age", "location", "occupation"]:
            profile.collection_progress[field] = True

        side_target = self.policy.get_side_target(
            profile,
            main_target="education",
            user_message="深圳，做IT",
            message_count=3,
        )

        assert side_target in {"monthly_income", "marital_status"}

    def test_monthly_income_falls_back_to_other_core_host_when_partner_requirement_unavailable(self):
        profile = UserProfile(account_id="u_income_location_host")
        profile.sex = "女"
        profile.age = 33
        profile.education = "本科"
        profile.occupation = "运营"
        for field in ["sex", "age", "education", "occupation"]:
            profile.collection_progress[field] = True
        profile.field_ask_count["partner_requirement"] = 1

        side_target = self.policy.get_side_target(
            profile,
            main_target="location",
            user_message="目前在深圳",
            message_count=4,
        )

        assert side_target == "monthly_income"

    def test_latest_location_cue_on_followup_prefers_occupation_over_global_order(self):
        profile = UserProfile(account_id="u_latest_location")

        decision = self.policy.decide(
            profile,
            user_message="男的呢，在深圳",
            message_count=2,
        )

        assert decision.main_target == "occupation"

    def test_location_and_age_with_preference_still_prefers_occupation_before_education(self):
        profile = UserProfile(account_id="u_location_age_prefers_work")

        decision = self.policy.decide(
            profile,
            user_message="我来自深圳，今年35岁，想找一个深圳的女生",
            message_count=1,
        )

        assert decision.main_target == "occupation"

    def test_occupation_prefers_monthly_income_side_target_over_marital_status(self):
        profile = UserProfile(account_id="u_occ_income_side")
        profile.sex = "男"
        profile.age = 35
        profile.location = "深圳"
        profile.education = "本科"
        for field in ("sex", "age", "location", "education"):
            profile.collection_progress[field] = True

        decision = self.policy.decide(
            profile,
            user_message="本科",
            message_count=2,
        )

        assert decision.main_target == "occupation"
        assert decision.side_target == "monthly_income"

    def test_latest_location_and_occupation_opening_prefers_low_pressure_core(self):
        profile = UserProfile(account_id="u_latest_location_occupation")

        decision = self.policy.decide(
            profile,
            user_message="90后，深圳，做IT",
            message_count=0,
        )

        assert decision.main_target == "occupation"
        assert decision.side_target == "monthly_income"

    def test_contextual_core_target_keeps_age_when_birth_year_bucket_is_pending(self):
        profile = UserProfile(account_id="u_pending_birth_year_age")
        profile.sex = "女"
        profile.collection_progress["sex"] = True
        profile.pending_birth_year_bucket = "90后"
        profile.birth_year_confirmation_closed = False
        profile.age_label = "90后"
        profile.age = 36
        profile.collection_progress["age"] = False

        target = self.policy._get_contextual_core_target(  # noqa: SLF001
            profile,
            user_message="90后",
            message_count=2,
        )

        assert target == "age"

    def test_contact_refusal_keeps_contact_flow_enabled(self):
        profile = UserProfile(account_id="u_contact_refusal_policy")
        profile.sex = "女"
        profile.age = 28
        profile.location = "深圳"
        profile.education = "本科"
        profile.occupation = "IT"
        profile.marital_status = "单身"
        profile.monthly_income = "7万"
        profile.partner_requirement = "成熟稳重"
        profile.partner_gender_preference = "男"
        for field in ("sex", "age", "location", "education", "occupation", "marital_status", "monthly_income", "partner_requirement"):
            profile.collection_progress[field] = True
        profile.collection_progress["partner_gender_preference"] = True
        profile.phone_ask_count = 1

        understanding = TurnUnderstandingResult(
            primary_turn_type="refusal_boundary_complaint",
            subtype="contact_refusal",
            answer_first=True,
            confidence=0.9,
            context_ack_type="contact_refusal",
        )

        decision = self.policy.decide(
            profile,
            user_message="不方便",
            message_count=6,
            understanding_result=understanding,
        )

        assert decision.allow_contact_target is True
        assert decision.primary_move in {"ack_and_ask", "light_followup"}

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

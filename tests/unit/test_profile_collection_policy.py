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

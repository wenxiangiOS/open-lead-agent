"""Profile collection policy unit tests."""

from src.models.user_profile import UserProfile
from src.services.collection.profile_collection_policy import ProfileCollectionPolicy


class TestProfileCollectionPolicy:
    """Test profile collection routing policy."""

    def setup_method(self):
        self.policy = ProfileCollectionPolicy()

    def test_main_target_prefers_core_fields(self):
        profile = UserProfile(account_id="u1")

        decision = self.policy.decide(profile, user_message="你好")

        assert decision.main_target == "sex"
        assert decision.side_target is None
        assert decision.can_enter_contact is False

    def test_main_target_skips_to_next_core_when_collected(self):
        profile = UserProfile(account_id="u1")
        profile.collection_progress["sex"] = True
        profile.sex = "男"
        profile.collection_progress["age"] = True
        profile.age = 28

        decision = self.policy.decide(profile, user_message="我在杭州")

        assert decision.main_target == "location"

    def test_low_priority_fields_never_become_main_target(self):
        profile = UserProfile(account_id="u1")
        profile.collection_progress["sex"] = True
        profile.collection_progress["age"] = True
        profile.collection_progress["location"] = True
        profile.collection_progress["education"] = True
        profile.collection_progress["occupation"] = True
        profile.collection_progress["marital_status"] = True
        profile.skipped_fields["contact"] = True

        decision = self.policy.decide(profile, user_message="我身高180")

        assert decision.main_target is None
        assert "height" not in decision.missing_fields
        assert "weight" not in decision.missing_fields
        assert "last_name" not in decision.missing_fields

    def test_partner_requirement_can_be_side_target_after_age(self):
        profile = UserProfile(account_id="u1")
        profile.collection_progress["sex"] = True
        profile.sex = "女"

        decision = self.policy.decide(profile, user_message="我28岁")

        assert decision.main_target == "age"
        assert decision.side_target == "partner_requirement"

    def test_monthly_income_can_be_side_target_after_contact_collected(self):
        profile = UserProfile(account_id="u1")
        for field in ["sex", "age", "location", "education", "occupation", "marital_status", "contact"]:
            profile.collection_progress[field] = True

        decision = self.policy.decide(profile, user_message="收入这块还行")

        assert decision.main_target is None
        assert decision.side_target == "monthly_income"

    def test_no_side_target_when_contact_becomes_primary_goal(self):
        profile = UserProfile(account_id="u1")
        profile.collection_progress["sex"] = True
        profile.collection_progress["age"] = True
        profile.collection_progress["location"] = True
        profile.collection_progress["education"] = True

        decision = self.policy.decide(profile, user_message="我做运营")

        assert decision.main_target == "occupation"
        assert decision.side_target is None

    def test_can_enter_contact_when_four_core_or_quasi_fields_ready(self):
        profile = UserProfile(account_id="u1")
        for field in ["sex", "age", "location", "education"]:
            profile.collection_progress[field] = True

        assert self.policy.can_enter_contact(profile) is True

    def test_can_enter_contact_when_minimum_required_combination_ready(self):
        profile = UserProfile(account_id="u1")
        for field in ["age", "location", "marital_status"]:
            profile.collection_progress[field] = True
        profile.collection_progress["occupation"] = True

        assert self.policy.can_enter_contact(profile) is True

    def test_contact_instruction_blocked_before_ready(self):
        profile = UserProfile(account_id="u1")

        allowed = self.policy.should_allow_contact_instruction(profile, "ASK_PHONE")

        assert allowed is False

    def test_contact_instruction_allowed_once_contact_flow_started(self):
        profile = UserProfile(account_id="u1")
        profile.phone_ask_count = 1

        allowed = self.policy.should_allow_contact_instruction(profile, "PERSUADE_PHONE")

        assert allowed is True

    def test_main_target_respects_field_cooldown(self, monkeypatch):
        profile = UserProfile(account_id="u1")
        profile.collection_progress["sex"] = True
        profile.sex = "男"
        profile.recent_asked_fields = ["age"]
        monkeypatch.setenv("MQ_FIELD_ASK_COOLDOWN_TURNS", "2")

        decision = self.policy.decide(profile, user_message="我喜欢深圳女生")

        assert decision.main_target != "age"

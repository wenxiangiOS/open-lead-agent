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

    def test_partner_requirement_does_not_preempt_core_mainline_after_age(self):
        profile = UserProfile(account_id="u1")
        profile.collection_progress["sex"] = True
        profile.sex = "女"

        decision = self.policy.decide(profile, user_message="我28岁")

        assert decision.main_target == "age"
        assert decision.side_target is None

    def test_marital_status_does_not_preempt_core_mainline_after_age(self):
        profile = UserProfile(account_id="u1")
        profile.collection_progress["sex"] = True
        profile.sex = "男"
        profile.close_active_ask("partner_requirement")

        decision = self.policy.decide(profile, user_message="我29岁")

        assert decision.main_target == "age"
        assert decision.side_target is None

    def test_partner_requirement_can_be_side_target_during_occupation_stage(self):
        profile = UserProfile(account_id="u1")
        for field in ["sex", "age", "location", "education"]:
            profile.collection_progress[field] = True

        decision = self.policy.decide(profile, user_message="我做运营")

        assert decision.main_target == "occupation"
        assert decision.side_target == "partner_requirement"

    def test_marital_status_precedes_monthly_income_during_occupation_stage(self):
        profile = UserProfile(account_id="u1")
        for field in ["sex", "age", "location", "education"]:
            profile.collection_progress[field] = True
        profile.close_active_ask("partner_requirement")

        decision = self.policy.decide(profile, user_message="我做运营")

        assert decision.main_target == "occupation"
        assert decision.side_target == "marital_status"

    def test_monthly_income_can_be_side_target_after_occupation_when_partner_and_marital_closed(self):
        profile = UserProfile(account_id="u1")
        for field in ["sex", "age", "location", "education"]:
            profile.collection_progress[field] = True
        profile.close_active_ask("partner_requirement")
        profile.close_active_ask("marital_status")

        decision = self.policy.decide(profile, user_message="我做运营")

        assert decision.main_target == "occupation"
        assert decision.side_target == "monthly_income"

    def test_marital_status_ask_limit_is_one(self):
        profile = UserProfile(account_id="u1")
        profile.field_ask_count["marital_status"] = 1

        assert self.policy.can_actively_ask(profile, "marital_status") is False

    def test_medium_field_becomes_passive_only_after_active_ask_closed(self):
        profile = UserProfile(account_id="u1")
        profile.close_active_ask("partner_requirement")

        assert self.policy.can_actively_ask(profile, "partner_requirement") is False
        assert self.policy.can_passively_extract_only(profile, "partner_requirement") is True

    def test_monthly_income_becomes_passive_only_after_active_ask_closed(self):
        profile = UserProfile(account_id="u1")
        profile.close_active_ask("monthly_income")

        assert self.policy.can_actively_ask(profile, "monthly_income") is False
        assert self.policy.can_passively_extract_only(profile, "monthly_income") is True

    def test_should_block_preference_ask_when_partner_requirement_collected(self):
        profile = UserProfile(account_id="u1")
        profile.collection_progress["partner_requirement"] = True
        profile.partner_requirement = "更看重年龄段"

        assert self.policy.should_block_preference_ask(profile, "") is True

    def test_should_block_preference_ask_when_partner_requirement_active_ask_closed(self):
        profile = UserProfile(account_id="u1")
        profile.close_active_ask("partner_requirement")

        assert self.policy.should_block_preference_ask(profile, "") is True

    def test_closed_medium_field_will_not_become_side_target(self):
        profile = UserProfile(account_id="u1")
        profile.collection_progress["sex"] = True
        profile.sex = "女"
        profile.close_active_ask("partner_requirement")

        decision = self.policy.decide(profile, user_message="我28岁")

        assert decision.side_target is None

    def test_medium_fields_blocked_for_faq_turn(self):
        profile = UserProfile(account_id="u1")
        profile.collection_progress["sex"] = True
        profile.sex = "女"

        decision = self.policy.decide(
            profile,
            user_message="怎么收费",
            allow_medium_target=False,
            prioritize_user_question=True,
            primary_move="answer_then_pause",
        )

        assert decision.side_target is None

    def test_medium_fields_blocked_during_contact_flow(self):
        profile = UserProfile(account_id="u1")
        profile.collection_progress["sex"] = True
        profile.sex = "女"
        profile.phone_ask_count = 1

        blocked = self.policy.should_block_medium_fields_for_turn(
            profile,
            user_message="嗯",
            allow_contact_target=True,
        )

        assert blocked is True

    def test_no_side_target_when_contact_becomes_primary_goal(self):
        """Phase 2 调整：当核心字段即将收集完毕时，partner_requirement 可作为顺带目标

        根据 spec "偏好轻聊"要求，在 occupation 阶段可以顺带问偏好。
        ASK_LIMITS 限制了 partner_requirement 只能主动问 1 次，不会反复开问。
        """
        profile = UserProfile(account_id="u1")
        profile.collection_progress["sex"] = True
        profile.collection_progress["age"] = True
        profile.collection_progress["location"] = True
        profile.collection_progress["education"] = True

        decision = self.policy.decide(profile, user_message="我做运营")

        assert decision.main_target == "occupation"
        # Phase 2: partner_requirement 可以作为顺带目标
        assert decision.side_target == "partner_requirement"

    def test_cannot_enter_contact_without_location_and_background(self):
        profile = UserProfile(account_id="u1")
        for field in ["sex", "age", "education", "marital_status"]:
            profile.collection_progress[field] = True

        assert self.policy.can_enter_contact(profile) is False

    def test_can_enter_contact_when_location_background_and_core_ready(self):
        profile = UserProfile(account_id="u1")
        for field in ["sex", "age", "location", "education", "occupation"]:
            profile.collection_progress[field] = True

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

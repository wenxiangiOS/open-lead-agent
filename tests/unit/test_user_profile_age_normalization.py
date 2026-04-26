from src.models.user_profile import UserProfile


def test_normalize_age_keeps_post_90_bucket_as_non_precise_age():
    normalized = UserProfile.normalize_age("90后")
    assert normalized is None


def test_normalize_age_does_not_treat_post_90_bucket_as_90_years_old():
    normalized = UserProfile.normalize_age("90后")
    assert normalized is None


def test_normalize_age_supports_birth_year_with_suffix():
    normalized = UserProfile.normalize_age("1998年")
    assert normalized == 28


def test_user_profile_to_dict_keeps_age_label_and_extraction_evidence():
    profile = UserProfile(account_id="u1")
    profile.age = 36
    profile.age_label = "90后"
    profile.set_extraction_evidence(
        field_name="age",
        value=36,
        source_text="90后",
        turn_id=3,
        confidence=0.9,
        source="rule",
    )

    data = profile.to_dict()
    restored = UserProfile.from_dict(data)

    assert data["age_label"] == "90后"
    assert "age" in data["extraction_evidence"]
    assert restored.age_label == "90后"
    assert restored.extraction_evidence["age"]["turn_id"] == 3


def test_update_field_age_label_specific_year_syncs_age_value():
    profile = UserProfile(account_id="u_age_label_sync")
    profile.age = 36
    profile.age_label = "90后"

    assert profile.update_field("age_label", "98年") is True
    assert profile.age_label == "98年"
    assert profile.age == 28
    assert profile.pending_birth_year_bucket in {None, ""}

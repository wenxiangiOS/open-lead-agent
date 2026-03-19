from scripts.run_random_user_simulation import (
    Persona,
    TurnRecord,
    SessionResult,
    _analyze,
    _check_profile_fields_with_expected_sex,
    _infer_expected_profile_from_turns,
)


def _build_persona() -> Persona:
    return Persona(
        sex="女",
        age_bucket="90后",
        location="深圳",
        education="本科",
        occupation="运营",
        preference="成熟稳重",
        faq_prob=0.1,
        joking_prob=0.1,
        defensive_prob=0.1,
        contact_willingness="phone",
    )


def test_infer_expected_profile_from_turns_extracts_explicit_fields():
    turns = [
        TurnRecord(
            index=1,
            user="我是女生，28岁，在深圳，本科，运营，单身，想找成熟稳重的",
            assistant="",
            latency_s=0.1,
            perf={},
        ),
        TurnRecord(
            index=2,
            user="电话17688654321，微信wx123456",
            assistant="",
            latency_s=0.1,
            perf={},
        ),
    ]

    expected = _infer_expected_profile_from_turns(turns)

    assert expected["sex"] == "女"
    assert expected["age"] == "28"
    assert expected["location"] == "深圳"
    assert expected["education"] == "本科"
    assert expected["occupation"] == "运营"
    assert expected["marital_status"] == "单身"
    assert expected["phone"] == "17688654321"
    assert expected["wechat"] == "wx123456"


def test_check_profile_fields_flags_wrong_explicitly_stated_values():
    turns = [
        TurnRecord(
            index=1,
            user="我是女生，28岁，在深圳，本科，运营，单身",
            assistant="",
            latency_s=0.1,
            perf={},
        ),
        TurnRecord(
            index=2,
            user="我微信wx123456",
            assistant="",
            latency_s=0.1,
            perf={},
        ),
    ]
    profile = {
        "sex": "女",
        "age": 28,
        "location": "广州",
        "education": "本科",
        "occupation": "产品",
        "marital_status": "单身",
        "wechat": "wx999999",
        "contact": "已留联系",
    }

    checks, failures = _check_profile_fields_with_expected_sex(
        _build_persona(),
        profile,
        turns,
        expected_sex="女",
    )

    failed_names = {check["name"] for check in checks if not check["passed"]}
    assert "location_matches_user_stated" in failed_names
    assert "occupation_matches_user_stated" in failed_names
    assert "wechat_matches_user_stated" in failed_names
    assert failures


def test_analyze_exposes_humanlike_and_extraction_panels():
    turns = [
        TurnRecord(
            index=1,
            user="怎么收费",
            assistant="我先问下你在哪里工作生活呀",
            latency_s=1.2,
            perf={"ai_call": 0.8, "total": 1.2},
            failures=["faq_not_answered_first"],
        )
    ]
    result = SessionResult(
        session_id="s1",
        scenario_id="case1",
        category="faq",
        tags=["critical"],
        persona=_build_persona(),
        turns=turns,
        final_profile={"location": "广州"},
        field_checks=[
            {"name": "location_matches_user_stated", "passed": False, "expected": "深圳", "actual": "广州", "note": ""},
            {"name": "location_truthy", "passed": True, "expected": "non-empty", "actual": "广州", "note": ""},
        ],
        field_failures=["location_matches_user_stated: expected='深圳', actual='广州'"],
        policy_checks=[
            {"name": "no_consecutive_same_field_ask", "passed": False, "expected": 0, "actual": 1, "note": ""},
        ],
        policy_failures=["no_consecutive_same_field_ask: expected=0, actual=1"],
        duration_s=1.2,
    )

    analysis = _analyze([result], template_threshold=0.18)

    assert "humanlike_quality" in analysis
    assert "extraction_accuracy" in analysis
    assert analysis["humanlike_quality"]["failed_checks"] >= 2
    assert analysis["extraction_accuracy"]["failed_checks"] == 1
    assert analysis["extraction_accuracy"]["exact_match_failures"] == 1

from scripts.run_random_user_simulation import (
    Persona,
    TurnRecord,
    SessionResult,
    _analyze,
    _build_workload,
    _check_policy_rules,
    _check_turn,
    _check_profile_fields_with_expected_sex,
    _extract_explicit_partner_requirement,
    _infer_expected_sex_from_turns,
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


def test_extract_explicit_partner_requirement_handles_height_and_age_limit_preference():
    assert _extract_explicit_partner_requirement("身高高挑，不要超过30岁") == "高挑，不要超过30岁"


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
        "sex": "男",
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
    assert "sex_self_declare_missed" in failed_names
    assert failures


def test_check_profile_fields_flags_unexpected_conversation_end_when_profile_should_continue():
    turns = [
        TurnRecord(
            index=1,
            user="我是男的，90后，深圳",
            assistant="",
            latency_s=0.1,
            perf={},
        ),
        TurnRecord(
            index=2,
            user="身高高挑，不要超过30岁",
            assistant="",
            latency_s=0.1,
            perf={},
        ),
    ]
    profile = {
        "sex": "男",
        "age": 36,
        "age_label": "90后",
        "location": "深圳",
        "partner_requirement": "高挑，不要超过30岁",
        "conversation_ended": True,
    }

    checks, failures = _check_profile_fields_with_expected_sex(
        _build_persona(),
        profile,
        turns,
        expected_sex="男",
    )

    failed_names = {check["name"] for check in checks if not check["passed"]}
    assert "unexpected_conversation_end" in failed_names
    assert failures


def test_check_profile_fields_accepts_age_label_for_bucket_style_age():
    turns = [
        TurnRecord(
            index=1,
            user="我是女生，90后，在深圳，本科，运营，单身",
            assistant="",
            latency_s=0.1,
            perf={},
        ),
    ]
    profile = {
        "sex": "女",
        "age": 36,
        "age_label": "90后",
        "location": "深圳",
        "education": "本科",
        "occupation": "运营",
        "marital_status": "单身",
        "contact": "未留",
    }

    checks, _ = _check_profile_fields_with_expected_sex(
        _build_persona(),
        profile,
        turns,
        expected_sex="女",
    )

    age_check = next(check for check in checks if check["name"] == "age_matches_user_stated")
    assert age_check["passed"] is True

    consistency_check = next(check for check in checks if check["name"] == "age_label_int_inconsistent")
    assert consistency_check["passed"] is True


def test_check_profile_fields_flags_age_label_and_age_inconsistent():
    turns = [
        TurnRecord(
            index=1,
            user="我是女生，90后，在深圳，本科，运营，单身",
            assistant="",
            latency_s=0.1,
            perf={},
        ),
    ]
    profile = {
        "sex": "女",
        "age": 90,
        "age_label": "90后",
        "location": "深圳",
        "education": "本科",
        "occupation": "运营",
        "marital_status": "单身",
        "contact": "未留",
    }

    checks, _ = _check_profile_fields_with_expected_sex(
        _build_persona(),
        profile,
        turns,
        expected_sex="女",
    )
    consistency_check = next(check for check in checks if check["name"] == "age_label_int_inconsistent")
    assert consistency_check["passed"] is False


def test_infer_expected_sex_from_turns_accepts_inline_self_declare():
    sex = _infer_expected_sex_from_turns(["我是女生在深圳工作", "本科"])
    assert sex == "女"


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


def test_check_turn_flags_contact_transition_abrupt_without_transition_phrase():
    failures = _check_turn(
        user="单身呢",
        assistant="方便留个电话吗？后续有合适的人选时联系你～",
        previous_assistant="收到～是做IT相关工作的呀，我顺带确认下，你现在是单身状态在认真了解脱单吗？",
        latency_s=1.5,
        turn_index=5,
    )
    assert "contact_transition_abrupt" in failures


def test_check_turn_allows_contact_followup_after_user_provides_phone_value():
    failures = _check_turn(
        user="17688987654",
        assistant="你的电话我记下啦，要是你微信方便的话，也可以留一个～",
        previous_assistant="后续有合适的人选第一时间联系你哦。",
        latency_s=1.5,
        turn_index=8,
    )
    assert "contact_transition_abrupt" not in failures


def test_policy_rules_capture_ack_overuse_and_field_interleaving_quality():
    turns = [
        TurnRecord(index=1, user="你好", assistant="收到啦，我记下了～你是男生还是女生呀？", latency_s=1.0, perf={}),
        TurnRecord(index=2, user="男的", assistant="收到啦，我记下了～那你今年多大呀？", latency_s=1.0, perf={}),
        TurnRecord(index=3, user="90后", assistant="收到啦，我记下了～你是什么学历呀？", latency_s=1.0, perf={}),
        TurnRecord(index=4, user="本科", assistant="收到啦，我记下了～你做什么工作呀？", latency_s=1.0, perf={}),
    ]
    checks, failures = _check_policy_rules(turns)
    failed_names = {check["name"] for check in checks if not check["passed"]}

    assert "ack_overuse" in failed_names
    assert "field_interleaving_quality" in failed_names
    assert failures


def test_check_turn_flags_clarification_not_answered_when_user_requests_explanation():
    failures = _check_turn(
        user="匹配点是啥意思",
        assistant="我们先不连着问资料，你也可以先说说你更在意的匹配点。",
        previous_assistant="我们先不连着问资料，你也可以先说说你更在意的匹配点。",
        latency_s=1.2,
        turn_index=6,
    )
    assert "clarification_not_answered" in failures
    assert "same_fallback_repeat_loop" in failures


def test_check_turn_does_not_flag_nonsense_for_valid_phone_like_input():
    failures = _check_turn(
        user="17688654321",
        assistant="方便留个电话吗？后续有合适的人选时联系你～",
        previous_assistant="你好呀～",
        latency_s=1.2,
        turn_index=2,
    )
    assert "nonsense_not_guided" not in failures


def test_check_turn_accepts_nonsense_guidance_with_meitai_mingbai_marker():
    failures = _check_turn(
        user="qweqwe123123",
        assistant="哈哈我没太明白你发的内容是什么意思哦~你可以换个说法吗？",
        previous_assistant="你在哪个城市生活呀？",
        latency_s=1.2,
        turn_index=3,
    )
    assert "nonsense_not_guided" not in failures


def test_check_turn_recognizes_contact_transition_with_ziliao_chabuduo_phrase():
    failures = _check_turn(
        user="单身",
        assistant="资料我这边先了解得差不多啦～方便留个电话吗？后续有合适的人选时联系你～",
        previous_assistant="那你现在是单身状态在认真了解吗？",
        latency_s=1.8,
        turn_index=10,
    )
    assert "contact_transition_abrupt" not in failures


def test_check_turn_invalid_wechat_retry_uses_inline_wechat_candidate():
    failures = _check_turn(
        user="那我微信wx_12",
        assistant="要是你电话方便的话，也可以留一个，后面联系会更及时些～",
        previous_assistant="你方便的话直接发我微信号就行～",
        latency_s=1.2,
        turn_index=3,
    )
    assert "invalid_wechat_not_retried" in failures


def test_check_turn_flags_preference_misclassified_as_fake_info():
    failures = _check_turn(
        user="身高高挑，不要超过30岁",
        assistant="哈哈，这个信息有点意思😊 不过我们还是要认真对待相亲这件事的～如果你是真心想找对象，请告诉我真实的信息哦！",
        previous_assistant="顺带聊聊你的偏好吧，你更看重对方哪几点呀？",
        latency_s=1.8,
        turn_index=5,
    )

    assert "preference_misclassified_as_fake_info" in failures


def test_build_workload_cover_scenarios_preserves_explicit_message_boundaries(monkeypatch):
    from argparse import Namespace
    import random

    scenario = {
        "id": "demo_preference_case",
        "category": "field_collection",
        "tags": ["critical"],
        "messages": ["你好", "身高高挑，不要超过30岁"],
    }
    monkeypatch.setattr(
        "scripts.run_random_user_simulation._load_coverage_scenarios",
        lambda _args: [scenario],
    )

    args = Namespace(
        cover_scenarios=True,
        min_turns=6,
        max_turns=12,
    )

    workload = _build_workload(args, random.Random(42))

    assert workload[0]["turns"] == ["你好", "身高高挑，不要超过30岁"]

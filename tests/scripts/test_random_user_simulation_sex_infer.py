from scripts.run_random_user_simulation import _infer_expected_sex_from_turns


def test_sex_infer_only_accepts_explicit_self_declare():
    assert _infer_expected_sex_from_turns(["找男生"]) is None
    assert _infer_expected_sex_from_turns(["想找女生，最好同城"]) is None
    assert _infer_expected_sex_from_turns(["我是女生"]) == "女"
    assert _infer_expected_sex_from_turns(["我男的"]) == "男"
    assert _infer_expected_sex_from_turns(["本人是女"]) == "女"


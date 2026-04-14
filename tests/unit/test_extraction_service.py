from types import SimpleNamespace

import pytest

from src.models.user_profile import UserProfile
from src.services.data.extraction_service import ExtractionService


class _FakeUserService:
    def __init__(self):
        self.profiles = {}

    async def get_user_profile(self, account_id):
        return self.profiles.setdefault(account_id, UserProfile(account_id=account_id))

    async def save_user_profile(self, account_id, profile):
        self.profiles[account_id] = profile
        return True

    async def update_user_profile_field(self, account_id, field_name, value):
        profile = await self.get_user_profile(account_id)
        success = profile.update_field(field_name, value)
        if success:
            self.profiles[account_id] = profile
        return success


def test_normalize_extracted_value_filters_placeholder_values():
    assert ExtractionService._normalize_extracted_value("值") is None
    assert ExtractionService._normalize_extracted_value("值/null") is None
    assert ExtractionService._normalize_extracted_value("null（电话号码）") is None
    assert ExtractionService._normalize_extracted_value("程序员") == "程序员"


def test_normalize_extracted_value_filters_valuenull_variant():
    """测试 '值null' 占位符变体（无斜杠）被正确过滤"""
    # AI 可能误抄模板内容，返回 "值null" 而不是 "值/null"
    assert ExtractionService._normalize_extracted_value("值null") is None
    assert ExtractionService._normalize_extracted_value("值Null") is None
    assert ExtractionService._normalize_extracted_value("值NULL") is None
    # 其他"值"开头的短占位符也应该被过滤
    assert ExtractionService._normalize_extracted_value("值xxx") is None
    assert ExtractionService._normalize_extracted_value("值示例") is None
    # 正常的职业名称应该保留
    assert ExtractionService._normalize_extracted_value("工程师") == "工程师"
    assert ExtractionService._normalize_extracted_value("教师") == "教师"


def test_normalize_occupation_value_strips_particle_and_noisy_prefix():
    assert ExtractionService._normalize_occupation_value("做美容吧") == "美容"
    assert ExtractionService._normalize_occupation_value("恶美容吧") == "美容"
    assert ExtractionService._normalize_occupation_value("是u做新能源") == "新能源"
    assert ExtractionService._normalize_occupation_value("现在是做程序员") == "程序员"
    assert ExtractionService._normalize_occupation_value("it") == "IT"
    assert ExtractionService._normalize_occupation_value("admin") == "行政"
    assert ExtractionService._normalize_occupation_value("做it的") == "IT"
    assert ExtractionService._normalize_occupation_value("产品这块") == "产品"
    assert ExtractionService._normalize_occupation_value("搞运营的") == "运营"
    assert ExtractionService._normalize_occupation_value("做医美这行") == "医美"
    assert ExtractionService._normalize_occupation_value("干hr") == "HR"
    assert ExtractionService._normalize_occupation_value("做qa测试") == "QA"
    assert ExtractionService._normalize_occupation_value("行政前台") == "行政"
    assert ExtractionService._normalize_occupation_value("hrbp") == "HR"
    assert ExtractionService._normalize_occupation_value("产品运营") == "产品运营"
    assert ExtractionService._normalize_occupation_value("电商运营") == "电商运营"
    assert ExtractionService._normalize_occupation_value("做ui设计") == "UI"
    assert ExtractionService._normalize_occupation_value("UI设计师") == "UI"
    assert ExtractionService._normalize_occupation_value("做qa测试工程师") == "QA"
    assert ExtractionService._normalize_occupation_value("行政人事") == "行政"
    assert ExtractionService._normalize_occupation_value("产品经理") == "产品"
    assert ExtractionService._normalize_occupation_value("运营助理") == "运营"
    assert ExtractionService._normalize_occupation_value("前端开发") == "前端开发"
    assert ExtractionService._normalize_occupation_value("前端工程师") == "前端开发"
    assert ExtractionService._normalize_occupation_value("后端开发") == "后端开发"
    assert ExtractionService._normalize_occupation_value("后端工程师") == "后端开发"
    assert ExtractionService._normalize_occupation_value("财会") == "财务"
    assert ExtractionService._normalize_occupation_value("医护") == "医护"


def test_has_explicit_self_update_signal_accepts_additional_education_variants():
    assert ExtractionService._has_explicit_self_update_signal("education", "我专升本")
    assert ExtractionService._has_explicit_self_update_signal("education", "在读博")
    assert ExtractionService._has_explicit_self_update_signal("education", "博士后")


def test_extract_deterministic_self_field_candidates_supports_linked_education_phrase():
    extracted = ExtractionService._extract_deterministic_self_field_candidates(  # noqa: SLF001
        "深圳龙华在编女教师，找同老家在深圳，一样本科"
    )

    assert extracted["education"] == "本科"


def test_extract_deterministic_self_field_candidates_does_not_parse_trailing_question_fragment_as_occupation():
    extracted = ExtractionService._extract_deterministic_self_field_candidates(  # noqa: SLF001
        "找对象 女生找男朋友，目前在深圳未婚单身，本科学历，我自己收入不高一年18左右，找起码180+，90后工作稳定就行 暂时就 怎么多了"
    )

    assert extracted.get("occupation") is None
    assert extracted.get("sex") == "女"
    assert extracted.get("location") == "深圳"
    assert extracted.get("education") == "本科"


def test_remove_unspoken_partner_requirement_content_strips_trailing_repair_noise():
    cleaned = ExtractionService._remove_unspoken_inferred_partner_requirement_content(  # noqa: SLF001
        "90后工作稳定就行 暂时就 怎么多了",
        "找对象 女生找男朋友，目前在深圳未婚单身，本科学历，我自己收入不高一年18左右，找起码180+，90后工作稳定就行 暂时就 怎么多了",
    )

    assert cleaned == "90后工作稳定就行"


def test_low_quality_self_field_gate_rejects_question_fragments_and_dirty_education():
    assert ExtractionService._is_low_quality_self_field_value(
        "occupation",
        "可以",
        user_message="可以啊 机构是吗 资源怎么样啊",
        scope="self",
    )
    assert ExtractionService._is_low_quality_self_field_value(
        "location",
        "香港",
        user_message="香港有不",
        scope="self",
    )
    assert ExtractionService._is_low_quality_self_field_value(
        "education",
        "新能本科",
        user_message="本科，单身",
        scope="self",
    )


def test_extract_age_label_keeps_post_90s_bucket():
    assert ExtractionService._extract_age_label("90后") == "90后"
    assert ExtractionService._extract_age_label("我是95后") == "95后"
    assert ExtractionService._extract_age_label("28岁") is None


def test_derive_age_label_from_meta_prefers_structured_self_evidence_over_full_message():
    assert (
        ExtractionService._derive_age_label_from_meta(
            age_value="31",
            extraction_meta={
                "age": {"source_span": "95年", "scope": "self"},
                "age_label": {"derived_value": "95年", "scope": "self"},
            },
        )
        == "95年"
    )


def test_parse_age_handles_post_2000_bucket():
    service = ExtractionService(_FakeUserService())
    assert service._parse_age("00后") == 26


def test_parse_age_handles_post_90s_bucket():
    service = ExtractionService(_FakeUserService())
    assert service._parse_age("90后") == 36


def test_parse_age_handles_birth_year_with_suffix():
    service = ExtractionService(_FakeUserService())
    assert service._parse_age("1998年") == 28


def test_parse_age_ignores_wechat_like_identifier():
    service = ExtractionService(_FakeUserService())
    assert service._parse_age("wx235345345") is None


def test_extract_partner_requirement_from_user_message_preserves_negation():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "不超过30岁，身高至少160，温柔的"
    )

    assert extracted == "年龄不超过30岁，身高至少160，温柔"


def test_extract_partner_requirement_from_user_message_captures_qizhi_preference():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "本科，看中对方气质吧"
    )

    assert extracted == "气质"


def test_extract_partner_requirement_from_user_message_keeps_height_and_looks_preferences():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "温柔，不要低于160，漂亮点的，其他没有了"
    )

    assert extracted == "温柔，身高不低于160，漂亮点"


def test_extract_partner_requirement_from_user_message_excludes_pure_gender_preference():
    assert ExtractionService._extract_partner_requirement_from_user_message("想找男生") is None
    assert ExtractionService._extract_partner_requirement_from_user_message("找个男朋友") is None
    assert ExtractionService._extract_partner_requirement_from_user_message("喜欢女生") is None


def test_extract_partner_requirement_from_user_message_keeps_trait_when_gender_preference_is_present():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "找个男朋友，成熟稳重一点"
    )

    assert extracted == "成熟稳重"


def test_extract_partner_requirement_from_user_message_captures_partner_age_range_expression():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "89年的想找个上下3岁的男朋友"
    )

    assert extracted == "年龄上下3岁"


def test_extract_partner_requirement_from_user_message_captures_shenzhen_second_gen_preference():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "93年女生找深二代男朋友"
    )

    assert extracted == "深二代"


def test_extract_partner_requirement_from_user_message_captures_composite_opening_preferences():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "深圳有不 想了解看看96年能接受4岁上下年龄差，喜欢笑就更好了卡身高174+最好不要同财务行业 自己跟跟倾向于稳定行业男生可以匹配不"
    )

    assert extracted == "年龄上下4岁，爱笑，身高174cm以上，不要同财务行业，稳定行业"


def test_extract_partner_requirement_from_user_message_captures_rich_mixed_intro_preferences():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "南山女生找男盆友，就是93未婚找未婚，卡学历身高，起码本科或者以上，比较倾向于大厂程序员，自己也是从事互联网有不"
    )

    assert extracted == "未婚，学历本科及以上，大厂程序员"


def test_extract_partner_requirement_from_user_message_supports_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "深圳女生，自己互联网，想找港男，本科起步，程序员最好"
    )

    assert extracted == "香港，学历本科及以上，程序员"


def test_normalize_partner_requirement_part_collapses_match_region_object_phrase():
    assert ExtractionService._normalize_partner_requirement_part("希望匹配香港地区的对象") == "香港"


def test_extract_partner_requirement_from_user_message_supports_compact_intro_partner_preferences():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "90 护士 本科 找同医疗体系比自己大都可以同在深圳发展，最好本地"
    )

    assert extracted == "同医疗体系，同在深圳发展，本地优先，比自己大"


def test_extract_partner_requirement_from_user_message_preserves_partner_age_bucket_in_compact_intro():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "95想找90后都可以有不"
    )

    assert extracted == "90后"


def test_extract_partner_requirement_from_user_message_preserves_rich_preferences_with_age_bucket():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "90后，看重稳重，成熟，身高要180以上，然后多金"
    )

    assert extracted is not None
    assert "90后" in extracted
    assert ("身高180cm以上" in extracted) or ("身高至少180" in extracted)
    assert "多金" in extracted
    assert "成熟稳重" in extracted


def test_extract_partner_requirement_from_user_message_supports_linked_education_phrase():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "深圳龙华在编女教师，找同老家在深圳，一样本科"
    )

    assert extracted == "学历本科及以上"


def test_extract_partner_preference_subslots_supports_linked_education_phrase():
    extracted = ExtractionService._extract_partner_preference_subslots("一样本科")  # noqa: SLF001

    assert extracted["partner_pref_education"] == "学历本科及以上"


def test_extract_partner_preference_subslots_does_not_leak_self_occupation_into_partner_industry():
    extracted = ExtractionService._extract_partner_preference_subslots(  # noqa: SLF001
        "深圳龙华在编女教师，找同老家在深圳 最好深户 有房有车，一样本科，不要92"
    )

    assert extracted["partner_pref_location"] == "深圳"
    assert extracted["partner_pref_education"] == "学历本科及以上"
    assert "partner_pref_industry" not in extracted


def test_resolve_partner_requirement_from_message_prefers_structured_subslots():
    resolved = ExtractionService._resolve_partner_requirement_from_message(  # noqa: SLF001
        "想找深圳，本科及以上",
        allow_legacy_fallback=False,
    )

    assert resolved == "深圳，学历本科及以上"


def test_resolve_partner_requirement_from_message_disables_legacy_fallback_by_default():
    resolved = ExtractionService._resolve_partner_requirement_from_message(  # noqa: SLF001
        "温柔吧",
        allow_legacy_fallback=False,
    )

    assert resolved is None


def test_resolve_partner_requirement_from_message_allows_legacy_fallback_when_enabled():
    resolved = ExtractionService._resolve_partner_requirement_from_message(  # noqa: SLF001
        "温柔吧",
        allow_legacy_fallback=True,
    )

    assert resolved == "温柔"


def test_resolve_partner_requirement_from_message_keeps_unstructured_tail_in_mixed_intro():
    resolved = ExtractionService._resolve_partner_requirement_from_message(  # noqa: SLF001
        "可以哒 深圳龙华在编女教师，河南人 165/104，找同老家在深圳 最好深户 有房有车，一样本科，不要92 可以直接电话联系这边13526783627 对啦怎么收费呢先了解下",
        allow_legacy_fallback=True,
    )

    assert resolved == "同老家在深圳，学历本科及以上，最好深户，有房有车，不要92"


def test_compose_structured_partner_preference_text_builds_display_from_subslots():
    profile = SimpleNamespace(
        partner_pref_age="90后",
        partner_pref_age_relation="比自己大",
        partner_pref_location="深圳",
        partner_pref_locality="同城优先",
        partner_pref_height="身高175cm以上",
        partner_pref_education="本科及以上",
        partner_pref_industry="程序员",
        partner_pref_personality="成熟稳重",
        partner_pref_income="收入过万",
        partner_pref_other="无特别要求",
    )

    assert (
        ExtractionService._compose_structured_partner_preference_text(profile)
        == "90后，比自己大，深圳，同城优先，身高175cm以上，本科及以上，程序员，成熟稳重，收入过万，无特别要求"
    )


def test_compose_partner_requirement_from_subslots_prefers_structured_parts_but_keeps_unstructured_tail():
    subslots = {
        "partner_pref_location": "深圳",
        "partner_pref_education": "学历本科及以上",
    }

    assert (
        ExtractionService._compose_partner_requirement_from_subslots(
            subslots,
            "深圳，最好深户，有房有车，学历本科及以上",
        )
        == "深圳，学历本科及以上，最好深户，有房有车"
    )


def test_extract_partner_requirement_from_user_message_supports_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175往上，30左右，月入别太低"
    )

    assert extracted == "身高175cm以上，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_looser_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "一米七五以上，三十出头，收入别太拉垮"
    )

    assert extracted == "身高175cm以上，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_even_looser_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "一米七五朝上，三十来岁，收入别太低就行"
    )

    assert extracted == "身高175cm以上，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_nonstandard_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "一米七五打底，三十上下，收入过得去就行"
    )

    assert extracted == "身高175cm以上，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_even_more_scattered_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "一米七五左右，三十多点，收入差不多就行"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_spoken_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "身高差不多175，30出头，收入别太寒碜"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175差不多，三十郎当岁，收入别太难看"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_extra_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下，三十好几，收入看得过去就行"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_more_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下浮动，三十冒头，收入说得过去就行"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_soft_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "一米七五上下都行，三十左右都可，收入能看就行"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_more_soft_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "身高175左右都成，30上下都行，收入过得去就成"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_variant_more_soft_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175左右都可以，30左右都行，收入差不离就行"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_extra_variant_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175附近，30来岁也行，收入别太磕碜"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_latest_extra_variant_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下差不多，30来岁左右，收入别太埋汰"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_latest_slang_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175差不离，30左右上下，收入别太拉胯"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_more_extra_variant_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175前后，30来岁都成，收入别太埋汰"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下都可，30来岁上下，收入过得去就好"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下都成，30来岁上下都行，收入说得过去就好"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_latest_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下都OK，30来岁上下都可，收入别太说不过去"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_more_latest_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下都ok啦，30来岁上下都成，收入别太拿不出手"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_next_more_latest_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下都ok的，30来岁上下也成，收入别太掉价"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_followup_latest_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下也行，30来岁也都行，收入别太上不了台面"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_latest_followup_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下都还行，30来岁也可以，收入别太寒酸"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_next_followup_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下差不太多，30来岁差不多，收入别太捉襟见肘"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_another_followup_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下大差不差，30来岁上下差不多，收入别太拮据"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_more_another_followup_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下凑合，30来岁还行，收入别太紧巴"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_more_more_another_followup_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下过得去，30来岁还成，收入别太磕巴"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_next_more_more_another_followup_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下说得过去，30来岁说得过去，收入别太寒碜吧"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_final_followup_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下没毛病，30来岁问题不大，收入别太磕碜吧"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_post_final_followup_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下没啥问题，30来岁没啥问题，收入别太掉面儿"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_after_post_final_followup_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下还过得去，30来岁还过得去，收入别太上不得台面"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_last_followup_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下马马虎虎，30来岁马马虎虎，收入别太寒掺"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_really_last_followup_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下也还行，30来岁也还行，收入别太没法看"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_true_last_followup_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下不赖，30来岁不赖，收入别太磕搀"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_actual_last_followup_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下将就，30来岁将就，收入别太寒碜着"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_actual_real_last_followup_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下还凑合，30来岁还凑合，收入别太跌份"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_next_actual_real_last_followup_even_newer_fragmented_numeric_colloquial_variants():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下也凑合，30来岁也凑合，收入别太寒伧"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_structured_numeric_partner_preference_for_bare_height_plus():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "想找一个175+的，30左右，收入别太低"
    )

    assert extracted == "身高175cm以上，年龄30左右，收入别太低"


def test_extract_partner_requirement_from_user_message_supports_structured_numeric_partner_preference_for_bare_numeric_operands():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "想找175以上的，30+的，月入2w+的"
    )

    assert extracted == "身高175cm以上，年龄30以上，收入2万以上"


def test_extract_partner_requirement_from_user_message_supports_structured_numeric_partner_preference_for_explicit_operand_phrases():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "想找175往上的，30左右的，收入过万的"
    )

    assert extracted == "身高175cm以上，年龄30左右，收入1万以上"


def test_extract_partner_requirement_from_user_message_supports_structured_numeric_partner_preference_for_explicit_around_and_income_bound_phrases():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "想找175左右的，30上下的，收入2万以上的"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入2万以上"


def test_extract_partner_requirement_from_user_message_extracts_structured_numeric_partner_preference_semantics():
    semantics = ExtractionService._extract_structured_numeric_partner_preference_semantics(
        "想找175以上的，30+的，月入2w+的"
    )

    assert semantics == [
        {"pos": 2, "field": "height", "operator": "lower_bound", "value": "175"},
        {"pos": 9, "field": "age", "operator": "lower_bound", "value": "30"},
        {"pos": 14, "field": "income", "operator": "lower_bound", "value": "2万"},
    ]


def test_extract_partner_requirement_from_user_message_extracts_structured_numeric_partner_preference_semantics_from_colloquial_aliases():
    semantics = ExtractionService._extract_structured_numeric_partner_preference_semantics(
        "想找175差不多的，三十来岁的，收入过得去就行"
    )

    assert semantics == [
        {"pos": 2, "field": "height", "operator": "around", "value": "175"},
        {"pos": 10, "field": "age", "operator": "around", "value": "30"},
        {"pos": 16, "field": "income", "operator": "not_too_low", "value": ""},
    ]


def test_extract_partner_requirement_from_user_message_extracts_structured_numeric_partner_preference_semantics_with_conversational_tails():
    semantics = ExtractionService._extract_structured_numeric_partner_preference_semantics(
        "想找175左右都可以，30上下都行，收入过得去就好"
    )

    assert semantics == [
        {"pos": 2, "field": "height", "operator": "around", "value": "175"},
        {"pos": 11, "field": "age", "operator": "around", "value": "30"},
        {"pos": 18, "field": "income", "operator": "not_too_low", "value": ""},
    ]


def test_extract_partner_requirement_from_user_message_uses_structured_numeric_alias_bridge():
    extracted = ExtractionService._extract_partner_requirement_from_user_message(
        "175上下都OK，三十出头，收入过得去就行"
    )

    assert extracted == "身高175cm左右，年龄30左右，收入别太低"


def test_partner_age_range_expression_does_not_count_as_user_underage_signal():
    service = ExtractionService(_FakeUserService())

    assert service._looks_like_partner_age_range_expression("89年的想找个上下3岁的男朋友") is True


def test_analyze_numeric_semantics_distinguishes_self_age_and_partner_age_gap():
    service = ExtractionService(_FakeUserService())

    analysis = service.analyze_numeric_semantics("我今年36，然后想找一个和我上下相差3岁的，最好在深圳")

    assert analysis["self_age_candidates"] == [36]
    assert analysis["partner_age_gap_candidates"] == [3]
    assert analysis["has_multiple_age_roles"] is True


def test_analyze_numeric_semantics_distinguishes_income_height_and_contact_candidates():
    service = ExtractionService(_FakeUserService())

    analysis = service.analyze_numeric_semantics("我36，月薪2万，身高160cm，电话13800138000")

    assert analysis["self_age_candidates"] == [36]
    assert analysis["income_candidates"] == ["2万"]
    assert "160" in analysis["height_candidates"] or "160cm" in analysis["height_candidates"]
    assert analysis["contact_candidates"]
    assert analysis["has_multiple_numeric_roles"] is True


def test_analyze_numeric_semantics_captures_income_range_and_approx_forms():
    service = ExtractionService(_FakeUserService())

    analysis = service.analyze_numeric_semantics("收入区间2万到3万，一年18-25左右，大概两万上下")

    assert any("2万到3万" in candidate for candidate in analysis["income_candidates"])
    assert any("18-25" in candidate for candidate in analysis["income_candidates"])
    assert any("两万上下" in candidate for candidate in analysis["income_candidates"])


def test_govern_role_consistent_fields_drops_partner_income_from_self_income():
    service = ExtractionService(_FakeUserService())

    governed = service.govern_role_consistent_fields(
        extracted_fields={"monthly_income": "2w+", "partner_requirement": "收入2万以上"},
        user_message="想找月入2w+的男生",
    )

    assert "monthly_income" not in governed
    assert governed["partner_requirement"] == "收入2万以上"


def test_govern_role_consistent_fields_keeps_location_and_income_when_both_asked():
    service = ExtractionService(_FakeUserService())
    profile = UserProfile(account_id="u_govern_multi")
    profile.last_asked_field = "location"
    profile.last_asked_side_field = "monthly_income"

    governed = service.govern_role_consistent_fields(
        extracted_fields={"location": "深圳", "monthly_income": "20k+"},
        user_message="深圳，20k+",
        user_profile=profile,
        last_response="那你现在常住在哪座城市呀？方便的话也可以说下大概的月收入哦。",
    )

    assert governed["location"] == "深圳"
    assert governed["monthly_income"] == "20k+"


def test_govern_role_consistent_fields_repairs_self_location_when_partner_preference_leaks_in():
    service = ExtractionService(_FakeUserService())

    governed = service.govern_role_consistent_fields(
        extracted_fields={"location": "香港"},
        user_message="深圳女生 想找香港的都可以",
    )

    assert governed["location"] == "深圳"


def test_govern_role_consistent_fields_repairs_self_education_when_partner_preference_leaks_in():
    service = ExtractionService(_FakeUserService())

    governed = service.govern_role_consistent_fields(
        extracted_fields={"education": "本科"},
        user_message="我硕士，想找本科以上的程序员",
    )

    assert governed["education"] == "硕士"


def test_govern_role_consistent_fields_repairs_self_occupation_when_partner_preference_leaks_in():
    service = ExtractionService(_FakeUserService())

    governed = service.govern_role_consistent_fields(
        extracted_fields={"occupation": "找同医疗体系比自己大都可以同在深圳发展"},
        user_message="90 护士 本科 找同医疗体系比自己大都可以同在深圳发展，最好本地",
    )

    assert governed["occupation"] == "护士"


def test_govern_role_consistent_fields_drops_partner_scoped_location_without_self_candidate():
    service = ExtractionService(_FakeUserService())

    governed = service.govern_role_consistent_fields(
        extracted_fields={"location": "香港"},
        user_message="想找香港的都可以",
        extraction_meta={"location": {"scope": "partner", "source_span": "香港"}},
    )

    assert "location" not in governed


def test_is_low_quality_self_field_value_rejects_feedback_and_location_like_occupation_values():
    assert ExtractionService._is_low_quality_self_field_value("occupation", "听不错", user_message="听不错")
    assert ExtractionService._is_low_quality_self_field_value("occupation", "就是深圳南山呢", user_message="就是深圳南山呢")


@pytest.mark.anyio
async def test_process_extracted_data_allows_trailing_punct_sex_self_intro():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_trailing_punct_sex")

    await service.process_extracted_data(
        "user_trailing_punct_sex",
        profile,
        {"sex": "男"},
        user_message="男的，",
    )

    refreshed = await user_service.get_user_profile("user_trailing_punct_sex")
    assert refreshed.sex == "男"


@pytest.mark.anyio
async def test_process_extracted_data_skips_age_write_when_message_is_income_statement():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_income_not_age")

    await service.process_extracted_data(
        "user_income_not_age",
        profile,
        {"age": "20"},
        user_message="我月薪20万",
    )

    refreshed = await user_service.get_user_profile("user_income_not_age")
    assert refreshed.age is None
    assert refreshed.age_under_limit is False


@pytest.mark.anyio
async def test_process_extracted_data_accepts_income_write_for_income_statement():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_income_write")

    await service.process_extracted_data(
        "user_income_write",
        profile,
        {"monthly_income": "2万"},
        user_message="我月薪2万",
    )

    refreshed = await user_service.get_user_profile("user_income_write")
    assert refreshed.monthly_income == "2万"


@pytest.mark.anyio
async def test_process_extracted_data_accepts_first_income_write_without_current_value_crash():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_income_first_write")

    await service.process_extracted_data(
        "user_income_first_write",
        profile,
        {"monthly_income": "20+"},
        user_message="20+",
    )

    refreshed = await user_service.get_user_profile("user_income_first_write")
    assert refreshed.monthly_income == "20+"


@pytest.mark.anyio
async def test_process_extracted_data_keeps_rich_partner_requirement_and_gender_preference():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_rich_partner_requirement")

    await service.process_extracted_data(
        "user_rich_partner_requirement",
        profile,
        {
            "sex": "女",
            "partner_requirement": "未婚，学历本科及以上，身高有要求，倾向大厂程序员",
        },
        user_message="南山女生找男朋友，93年未婚找未婚，起码本科或者以上，比较倾向于大厂程序员，自己也是从事互联网",
    )

    refreshed = await user_service.get_user_profile("user_rich_partner_requirement")
    assert refreshed.sex == "女"
    assert refreshed.partner_gender_preference == "男"
    assert refreshed.partner_requirement == "未婚，学历本科及以上，身高有要求，倾向大厂程序员"


@pytest.mark.anyio
async def test_process_extracted_data_keeps_self_sex_for_mixed_intro_with_benyou_variant():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_benyou_mixed_intro")

    await service.process_extracted_data(
        "user_benyou_mixed_intro",
        profile,
        {"sex": "女"},
        user_message="南山女生找男盆友，93未婚找未婚，起码本科或者以上，比较倾向于大厂程序员，自己也是从事互联网有不",
    )

    refreshed = await user_service.get_user_profile("user_benyou_mixed_intro")
    assert refreshed.sex == "女"


@pytest.mark.anyio
async def test_process_extracted_data_detects_mixed_self_intro_with_location_preference():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)

    assert (
        service._looks_like_mixed_self_intro_with_location_preference(
            "深圳女生想找香港的男生，93年未婚，自己做互联网"
        )
        is True
    )


@pytest.mark.anyio
async def test_process_extracted_data_allows_self_occupation_in_mixed_intro_with_partner_preference():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_mixed_intro_occupation")

    await service.process_extracted_data(
        "user_mixed_intro_occupation",
        profile,
        {"occupation": "互联网相关"},
        user_message="南山女生找男朋友，93年未婚，比较倾向于大厂程序员，自己也是从事互联网",
    )

    refreshed = await user_service.get_user_profile("user_mixed_intro_occupation")
    assert refreshed.occupation == "互联网相关"


@pytest.mark.anyio
async def test_process_extracted_data_allows_affirmative_sex_confirmation_with_last_response():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_affirmative_confirm_sex")

    await service.process_extracted_data(
        "user_affirmative_confirm_sex",
        profile,
        {"sex": "男"},
        user_message="是的",
        last_response="我再确认下，你这边是男生对吧？",
    )

    refreshed = await user_service.get_user_profile("user_affirmative_confirm_sex")
    assert refreshed.sex == "男"


@pytest.mark.anyio
async def test_process_extracted_data_allows_soft_guess_gender_confirmation_with_embedded_answer():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_soft_guess_confirm_sex")

    await service.process_extracted_data(
        "user_soft_guess_confirm_sex",
        profile,
        {"sex": "女"},
        user_message="是的呢女生，89年的",
        last_response="想找合适的男生对吧，我先记下来啦~你应该是女孩子吧？对啦你具体是80几年出生的呀？",
    )

    refreshed = await user_service.get_user_profile("user_soft_guess_confirm_sex")
    assert refreshed.sex == "女"


@pytest.mark.anyio
async def test_process_extracted_data_allows_affirmative_sex_confirmation_with_pending_state():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_affirmative_pending_sex")
    profile.pending_sex_confirmation = "男"
    await user_service.save_user_profile("user_affirmative_pending_sex", profile)

    await service.process_extracted_data(
        "user_affirmative_pending_sex",
        profile,
        {"sex": "男"},
        user_message="是的",
    )

    refreshed = await user_service.get_user_profile("user_affirmative_pending_sex")
    assert refreshed.sex == "男"
    assert refreshed.pending_sex_confirmation is None


@pytest.mark.anyio
async def test_process_extracted_data_allows_correction_style_sex_write():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_correction_sex")

    await service.process_extracted_data(
        "user_correction_sex",
        profile,
        {"sex": "男"},
        user_message="上面不是说了是男生吗？",
    )

    refreshed = await user_service.get_user_profile("user_correction_sex")
    assert refreshed.sex == "男"


@pytest.mark.anyio
async def test_process_extracted_data_clears_stale_age_label_when_user_provides_exact_age():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_age")
    profile.age = 36
    profile.age_label = "90后"
    profile.collection_progress["age"] = True
    profile.collection_progress["age_label"] = True
    await user_service.save_user_profile("user_age", profile)

    await service.process_extracted_data("user_age", profile, {"age": "28岁"}, user_message="我28岁")

    refreshed = await user_service.get_user_profile("user_age")
    assert refreshed.age == 28
    assert refreshed.age_label is None


@pytest.mark.anyio
async def test_process_extracted_data_does_not_backfill_partner_bucket_into_self_age_label():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_self_partner_age_scope")

    await service.process_extracted_data(
        "user_self_partner_age_scope",
        profile,
        {"age": "31", "partner_requirement": "90后都可以"},
        user_message="95想找90后都可以有不",
        extraction_meta={
            "age": {
                "source": "rule",
                "confidence": 0.9,
                "source_text": "95想找90后都可以有不",
                "source_span": "95年",
                "scope": "self",
            },
            "age_label": {
                "source": "derived",
                "confidence": 0.92,
                "source_text": "95年",
                "source_span": "95年",
                "scope": "self",
                "derived_value": "95年",
                "derived_from": "age",
            },
            "partner_requirement": {
                "source": "rule",
                "confidence": 0.9,
                "source_text": "95想找90后都可以有不",
                "source_span": "90后都可以",
                "scope": "partner",
            },
        },
    )

    refreshed = await user_service.get_user_profile("user_self_partner_age_scope")
    assert refreshed.age == 31
    assert refreshed.age_label == "95年"


@pytest.mark.asyncio
async def test_process_extracted_data_rejects_low_quality_occupation_value_in_faq_like_message():
    service = ExtractionService(_FakeUserService())
    profile = UserProfile(account_id="user_low_quality_occ")
    service.user_service.profiles["user_low_quality_occ"] = profile

    result = await service.process_extracted_data(
        "user_low_quality_occ",
        profile,
        {"occupation": "可以"},
        user_message="可以啊 机构是吗 资源怎么样啊",
        extraction_meta={"occupation": {"scope": "self", "source_text": "可以啊 机构是吗 资源怎么样啊"}},
    )

    refreshed = await service.user_service.get_user_profile("user_low_quality_occ")
    assert result["collected"] is False
    assert refreshed.occupation is None


@pytest.mark.asyncio
async def test_process_extracted_data_allows_high_quality_value_to_override_low_quality_stable_value():
    service = ExtractionService(_FakeUserService())
    profile = UserProfile(account_id="user_override_low_quality")
    profile.occupation = "可以"
    profile.collection_progress["occupation"] = True
    service.user_service.profiles["user_override_low_quality"] = profile

    result = await service.process_extracted_data(
        "user_override_low_quality",
        profile,
        {"occupation": "产品"},
        user_message="我做产品",
        extraction_meta={"occupation": {"scope": "self", "source_text": "我做产品"}},
    )

    refreshed = await service.user_service.get_user_profile("user_override_low_quality")
    assert result["collected"] is True
    assert refreshed.occupation == "产品"


@pytest.mark.asyncio
async def test_process_extracted_data_partner_requirement_prefers_structured_message_compose_when_model_value_is_partial():
    service = ExtractionService(_FakeUserService())
    profile = UserProfile(account_id="user_partner_req_structured_priority")
    service.user_service.profiles["user_partner_req_structured_priority"] = profile

    result = await service.process_extracted_data(
        "user_partner_req_structured_priority",
        profile,
        {"partner_requirement": "学历本科及以上"},
        user_message="找深圳，本科及以上",
        extraction_meta={
            "partner_requirement": {
                "scope": "partner",
                "source": "llm",
                "source_text": "找深圳，本科及以上",
            }
        },
    )

    refreshed = await service.user_service.get_user_profile("user_partner_req_structured_priority")
    assert result["collected"] is True
    normalized_parts = {
        str(part).strip()
        for part in str(refreshed.partner_requirement or "").split("，")
        if str(part).strip()
    }
    assert normalized_parts == {"深圳", "学历本科及以上"}
    assert refreshed.partner_pref_location == "深圳"
    assert refreshed.partner_pref_education == "学历本科及以上"


@pytest.mark.asyncio
async def test_process_extracted_data_rejects_faq_scope_self_field_write():
    service = ExtractionService(_FakeUserService())
    profile = UserProfile(account_id="user_faq_scope")
    service.user_service.profiles["user_faq_scope"] = profile

    result = await service.process_extracted_data(
        "user_faq_scope",
        profile,
        {"location": "香港"},
        user_message="香港有不",
        extraction_meta={"location": {"scope": "faq", "source_text": "香港有不"}},
    )

    refreshed = await service.user_service.get_user_profile("user_faq_scope")
    assert result["collected"] is False
    assert refreshed.location is None


@pytest.mark.asyncio
async def test_process_extracted_data_derives_partner_preference_subslots_from_requirement():
    service = ExtractionService(_FakeUserService())
    profile = UserProfile(account_id="user_partner_pref_structured")
    service.user_service.profiles["user_partner_pref_structured"] = profile

    result = await service.process_extracted_data(
        "user_partner_pref_structured",
        profile,
        {"partner_requirement": "90后都可以，香港优先"},
        user_message="90后都可以，香港优先",
        extraction_meta={"partner_requirement": {"scope": "partner", "source_text": "90后都可以，香港优先"}},
    )

    refreshed = await service.user_service.get_user_profile("user_partner_pref_structured")
    assert result["collected"] is True
    assert refreshed.partner_requirement == "90后都可以，香港优先"
    assert refreshed.partner_pref_age == "90后"
    assert refreshed.partner_pref_location == "香港"


@pytest.mark.asyncio
async def test_process_extracted_data_derives_richer_partner_preference_subslots_from_requirement():
    service = ExtractionService(_FakeUserService())
    profile = UserProfile(account_id="user_partner_pref_rich_structured")
    service.user_service.profiles["user_partner_pref_rich_structured"] = profile

    result = await service.process_extracted_data(
        "user_partner_pref_rich_structured",
        profile,
        {"partner_requirement": "同医疗体系，同在深圳发展，本地优先，比自己大"},
        user_message="同医疗体系，同在深圳发展，本地优先，比自己大",
        extraction_meta={
            "partner_requirement": {
                "scope": "partner",
                "source_text": "同医疗体系，同在深圳发展，本地优先，比自己大",
            }
        },
    )

    refreshed = await service.user_service.get_user_profile("user_partner_pref_rich_structured")
    assert result["collected"] is True
    assert refreshed.partner_pref_industry == "同医疗体系"
    assert refreshed.partner_pref_location == "深圳"
    assert refreshed.partner_pref_locality == "本地优先"
    assert refreshed.partner_pref_age_relation == "比自己大"


@pytest.mark.asyncio
async def test_process_extracted_data_composes_partner_requirement_from_structured_subslots_only():
    service = ExtractionService(_FakeUserService())
    profile = UserProfile(account_id="user_partner_pref_compose_only")
    service.user_service.profiles["user_partner_pref_compose_only"] = profile

    result = await service.process_extracted_data(
        "user_partner_pref_compose_only",
        profile,
        {
            "partner_pref_location": "深圳",
            "partner_pref_education": "学历本科及以上",
        },
        user_message="深圳，本科及以上",
        extraction_meta={
            "partner_pref_location": {"scope": "partner", "source_text": "深圳"},
            "partner_pref_education": {"scope": "partner", "source_text": "本科及以上"},
        },
    )

    refreshed = await service.user_service.get_user_profile("user_partner_pref_compose_only")
    assert result["collected"] is True
    assert refreshed.partner_pref_location == "深圳"
    assert refreshed.partner_pref_education == "学历本科及以上"
    assert refreshed.partner_requirement == "深圳，学历本科及以上"


@pytest.mark.asyncio
async def test_process_extracted_data_composes_partner_requirement_from_subslots_and_user_message_tail():
    service = ExtractionService(_FakeUserService())
    profile = UserProfile(account_id="user_partner_pref_compose_message_tail")
    service.user_service.profiles["user_partner_pref_compose_message_tail"] = profile

    result = await service.process_extracted_data(
        "user_partner_pref_compose_message_tail",
        profile,
        {
            "partner_pref_location": "深圳",
            "partner_pref_education": "学历本科及以上",
        },
        user_message="可以哒 深圳龙华在编女教师，河南人 165/104，找同老家在深圳 最好深户 有房有车，一样本科，不要92 可以直接电话联系这边13526783627 对啦怎么收费呢先了解下",
        extraction_meta={
            "partner_pref_location": {"scope": "partner", "source_text": "同老家在深圳"},
            "partner_pref_education": {"scope": "partner", "source_text": "一样本科"},
        },
    )

    refreshed = await service.user_service.get_user_profile("user_partner_pref_compose_message_tail")
    assert result["collected"] is True
    assert refreshed.partner_pref_location == "深圳"
    assert refreshed.partner_pref_education == "学历本科及以上"
    assert refreshed.partner_requirement == "同老家在深圳，学历本科及以上，最好深户，有房有车，不要92"


@pytest.mark.asyncio
async def test_process_extracted_data_composes_partner_requirement_from_subslots_without_losing_existing_tail():
    service = ExtractionService(_FakeUserService())
    profile = UserProfile(
        account_id="user_partner_pref_compose_existing_tail",
        partner_requirement="最好深户，有房有车",
    )
    profile.collection_progress["partner_requirement"] = True
    service.user_service.profiles["user_partner_pref_compose_existing_tail"] = profile

    result = await service.process_extracted_data(
        "user_partner_pref_compose_existing_tail",
        profile,
        {
            "partner_pref_location": "深圳",
            "partner_pref_education": "学历本科及以上",
        },
        user_message="深圳，学历本科及以上，最好深户，有房有车",
        extraction_meta={
            "partner_pref_location": {"scope": "partner", "source_text": "深圳"},
            "partner_pref_education": {"scope": "partner", "source_text": "学历本科及以上"},
        },
    )

    refreshed = await service.user_service.get_user_profile("user_partner_pref_compose_existing_tail")
    assert result["collected"] is True
    assert refreshed.partner_requirement == "深圳，学历本科及以上，最好深户，有房有车"


@pytest.mark.anyio
async def test_process_extracted_data_skips_age_write_for_contact_like_numeric_message():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_contact_like_age_guard")

    result = await service.process_extracted_data(
        "user_contact_like_age_guard",
        profile,
        {"age": "18"},
        user_message="1879987654",
    )

    refreshed = await user_service.get_user_profile("user_contact_like_age_guard")
    assert result["collected"] is False
    assert refreshed.age is None
    assert refreshed.age_under_limit is False


@pytest.mark.anyio
async def test_process_extracted_data_allows_real_age_when_age_semantics_are_explicit():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_real_age_guard")

    result = await service.process_extracted_data(
        "user_real_age_guard",
        profile,
        {"age": "18"},
        user_message="我今年18岁",
    )

    assert result["collected"] is True
    assert result["under_limit"] is True


@pytest.mark.anyio
async def test_process_extracted_data_does_not_pollute_occupation_with_partner_requirement():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_preference")

    await service.process_extracted_data(
        "user_preference",
        profile,
        {
            "education": "本科",
            "occupation": "看对方气质吧",
            "partner_requirement": "看重对方气质",
        },
        user_message="本科，看中对方气质吧",
    )

    refreshed = await user_service.get_user_profile("user_preference")
    assert refreshed.education == "本科"
    assert refreshed.partner_requirement == "气质"
    assert refreshed.occupation is None


@pytest.mark.anyio
async def test_process_extracted_data_opening_mixed_intro_blocks_relationship_and_income_age_pollution():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_opening_mixed_intro_pollution_guard")

    message = "找对象 女生找男朋友，目前在深圳未婚单身，本科学历，我自己收入不高一年18左右，找起码180+，90后工作稳定就行 暂时就"

    await service.process_extracted_data(
        "user_opening_mixed_intro_pollution_guard",
        profile,
        {
            "sex": "女",
            "location": "深圳",
            "education": "本科",
            "marital_status": "未婚单身",
            "monthly_income": "年薪18万左右",
            "partner_requirement": "身高180cm以上、90后、工作稳定的男生",
        },
        user_message=message,
        extraction_meta={
            "partner_requirement": {
                "scope": "partner",
                "source": "llm",
                "source_text": message,
            }
        },
    )

    refreshed = await user_service.get_user_profile("user_opening_mixed_intro_pollution_guard")
    assert refreshed.occupation is None
    assert "年龄18左右" not in str(refreshed.partner_requirement or "")
    assert "找对象" not in str(refreshed.partner_requirement or "")
    assert "女生找男朋友" not in str(refreshed.partner_requirement or "")


@pytest.mark.anyio
async def test_process_extracted_data_keeps_explicit_occupation_when_same_turn_also_contains_preference():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_occ_and_pref")

    await service.process_extracted_data(
        "user_occ_and_pref",
        profile,
        {
            "occupation": "IT",
            "partner_requirement": "温柔",
        },
        user_message="做it，看中对方温柔",
    )

    refreshed = await user_service.get_user_profile("user_occ_and_pref")
    assert refreshed.occupation == "IT"
    assert refreshed.partner_requirement == "温柔"


@pytest.mark.anyio
async def test_process_extracted_data_normalizes_noisy_occupation_value_before_save():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_occ_noise")

    await service.process_extracted_data(
        "user_occ_noise",
        profile,
        {
            "occupation": "恶美容吧",
            "monthly_income": "7万左右",
        },
        user_message="做美容吧，7万左右",
    )

    refreshed = await user_service.get_user_profile("user_occ_noise")
    assert refreshed.occupation == "美容"
    assert refreshed.monthly_income == "7万左右"


@pytest.mark.anyio
async def test_process_extracted_data_merges_partner_requirement_without_overwriting_longer_model_value():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_partner_merge")

    await service.process_extracted_data(
        "user_partner_merge",
        profile,
        {"partner_requirement": "温柔，身高不低于160，长相漂亮，无其他要求"},
        user_message="温柔，不要低于160，漂亮点的，其他没有了",
    )

    refreshed = await user_service.get_user_profile("user_partner_merge")
    assert refreshed.partner_requirement == "温柔，身高不低于160，长相漂亮，无其他要求，漂亮点"


@pytest.mark.anyio
async def test_process_extracted_data_does_not_mix_education_into_partner_requirement_when_same_turn_contains_both():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_partner_education_mix")

    await service.process_extracted_data(
        "user_partner_education_mix",
        profile,
        {
            "education": "本科",
            "partner_requirement": "本科，苗条漂亮，身高至少160",
        },
        user_message="本科，苗条，漂亮，至少160",
    )

    refreshed = await user_service.get_user_profile("user_partner_education_mix")
    assert refreshed.education == "本科"
    assert refreshed.partner_requirement == "苗条漂亮，身高至少160"


@pytest.mark.anyio
async def test_process_extracted_data_keeps_self_education_and_marital_status_in_mixed_intro():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_mixed_intro_edu_marital")

    await service.process_extracted_data(
        "user_mixed_intro_edu_marital",
        profile,
        {
            "sex": "女",
            "education": "本科",
            "marital_status": "未婚",
            "partner_requirement": "未婚，学历本科及以上",
        },
        user_message="深圳女生，93年未婚，自己本科，想找未婚、本科及以上的男生",
    )

    refreshed = await user_service.get_user_profile("user_mixed_intro_edu_marital")
    assert refreshed.sex == "女"
    assert refreshed.education == "本科"
    assert refreshed.marital_status == "未婚"
    assert refreshed.partner_gender_preference == "男"
    assert refreshed.partner_requirement == "未婚，学历本科及以上"


@pytest.mark.anyio
async def test_process_extracted_data_hydrates_linked_education_phrase_into_self_and_partner_fields():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_linked_education_phrase")

    await service.process_extracted_data(
        "user_linked_education_phrase",
        profile,
        {
            "occupation": "在编教师",
        },
        user_message="深圳龙华在编女教师，找同老家在深圳，一样本科",
    )

    refreshed = await user_service.get_user_profile("user_linked_education_phrase")
    assert refreshed.sex == "女"
    assert refreshed.education == "本科"
    assert refreshed.partner_pref_education == "学历本科及以上"


@pytest.mark.anyio
async def test_process_extracted_data_does_not_pollute_self_fields_from_partner_only_preference():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_partner_only_scope")

    await service.process_extracted_data(
        "user_partner_only_scope",
        profile,
        {
            "location": "香港",
            "education": "本科",
            "marital_status": "未婚",
            "partner_requirement": "香港，未婚，学历本科及以上",
            "partner_gender_preference": "男",
        },
        user_message="想找香港的未婚男生，本科及以上就行",
    )

    refreshed = await user_service.get_user_profile("user_partner_only_scope")
    assert refreshed.location is None
    assert refreshed.education is None
    assert refreshed.marital_status is None
    assert refreshed.partner_gender_preference == "男"
    assert refreshed.partner_requirement == "香港，未婚，学历本科及以上"


@pytest.mark.anyio
async def test_process_extracted_data_does_not_trigger_age_under_limit_from_income_context():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_income_ctx_age_guard")

    await service.process_extracted_data(
        "user_income_ctx_age_guard",
        profile,
        {
            "age": "20",
            "location": "深圳",
            "monthly_income": "年薪税后大概20左右",
        },
        user_message="深圳南山呢，现在年薪税后大概20左右",
    )

    refreshed = await user_service.get_user_profile("user_income_ctx_age_guard")
    assert refreshed.location == "深圳"
    assert refreshed.monthly_income == "年薪税后大概20左右"
    assert refreshed.age is None
    assert refreshed.age_under_limit is False


@pytest.mark.anyio
async def test_process_extracted_data_drops_unspoken_zodiac_inference_from_partner_requirement():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_partner_req_no_zodiac")

    await service.process_extracted_data(
        "user_partner_req_no_zodiac",
        profile,
        {"partner_requirement": "属蛇的深二代男朋友"},
        user_message="93年女生找深二代男朋友",
    )

    refreshed = await user_service.get_user_profile("user_partner_req_no_zodiac")
    assert refreshed.partner_requirement == "深二代"


@pytest.mark.anyio
async def test_process_extracted_data_does_not_set_occupation_inference_candidate_from_partner_requirement():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_occ_candidate")

    await service.process_extracted_data(
        "user_occ_candidate",
        profile,
        {"partner_requirement": "不要同财务行业，稳定行业"},
        user_message="最好不要同财务行业，倾向稳定行业男生",
    )

    refreshed = await user_service.get_user_profile("user_occ_candidate")
    assert refreshed.partner_requirement == "不要同财务行业，稳定行业"
    assert refreshed.occupation_inference_candidate is None
    assert "occupation_inference_candidate" not in refreshed.extraction_evidence


def test_infer_occupation_candidate_from_partner_requirement_prefers_explicit_self_industry():
    candidate, confidence, reason = ExtractionService._infer_occupation_candidate_from_partner_requirement(
        "我自己做财务相关，最好不要找同行"
    )

    assert candidate == "财务"
    assert confidence == 0.93
    assert reason == "explicit_self_industry"


@pytest.mark.anyio
async def test_process_extracted_data_clears_occupation_inference_candidate_after_explicit_occupation():
    user_service = _FakeUserService()
    service = ExtractionService(user_service)
    profile = await user_service.get_user_profile("user_occ_candidate_clear")
    profile.occupation_inference_candidate = "财务"
    await user_service.save_user_profile("user_occ_candidate_clear", profile)

    await service.process_extracted_data(
        "user_occ_candidate_clear",
        profile,
        {"occupation": "IT"},
        user_message="我做it",
    )

    refreshed = await user_service.get_user_profile("user_occ_candidate_clear")
    assert refreshed.occupation == "IT"
    assert refreshed.occupation_inference_candidate is None

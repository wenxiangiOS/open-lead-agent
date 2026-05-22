from src.collection.confirmation import PendingConfirmation
from src.faq import FAQMatch
from src.policy import TurnPriorityPolicy
from src.templates.config import ContactMethodConfig, FAQConfig, FieldConfig
from src.understanding import TurnSemanticFrame


def _policy() -> TurnPriorityPolicy:
    return TurnPriorityPolicy()


def _field(key: str = "age") -> FieldConfig:
    return FieldConfig(key=key, label=key)


def _contact(key: str = "phone") -> ContactMethodConfig:
    return ContactMethodConfig(key=key, label=key)


def _faq(intent: str = "pricing") -> FAQMatch:
    return FAQMatch(
        item=FAQConfig(
            intent=intent,
            keywords=["收费"],
            answer="基础咨询通常可以免费。",
            continue_collection=True,
        ),
        matched_keyword="收费",
    )


def test_pending_confirmation_has_highest_turn_priority():
    priority = _policy().decide(
        semantic_frame=TurnSemanticFrame(intents=["faq", "contact_intent"]),
        faq_match=_faq(),
        pending_confirmation=PendingConfirmation(
            field_key="age",
            proposed_value="30",
            current_value=None,
            reason="low_confidence",
        ),
        next_field=_field(),
        contact_method=_contact(),
        early_closing_ready=True,
    )

    assert priority.task == "pending_confirmation"


def test_question_or_concern_outranks_contact_and_profile_collection():
    priority = _policy().decide(
        semantic_frame=TurnSemanticFrame(
            intents=["faq", "contact_intent"],
            turn_mode="dense_intro",
            no_reask_fields=["sex", "age", "location"],
        ),
        faq_match=_faq(),
        pending_confirmation=None,
        next_field=_field("occupation"),
        contact_method=_contact("wechat"),
        early_closing_ready=False,
    )

    assert priority.task == "answer_question"
    assert priority.reason == "faq:pricing"


def test_completed_contact_flow_closes_before_asking_another_contact_method():
    priority = _policy().decide(
        semantic_frame=TurnSemanticFrame(intents=["contact_intent"]),
        faq_match=None,
        pending_confirmation=None,
        next_field=None,
        contact_method=_contact("wechat"),
        early_closing_ready=True,
    )

    assert priority.task == "closing"


def test_contact_capture_is_used_when_ready_and_no_higher_priority_task_exists():
    priority = _policy().decide(
        semantic_frame=TurnSemanticFrame(intents=["contact_intent"]),
        faq_match=None,
        pending_confirmation=None,
        next_field=_field("partner_requirement"),
        contact_method=_contact("phone"),
        early_closing_ready=False,
    )

    assert priority.task == "contact_capture"
    assert priority.reason == "semantic:contact_intent"


def test_profile_collection_is_default_when_no_interrupting_task_exists():
    priority = _policy().decide(
        semantic_frame=TurnSemanticFrame(intents=["profile"]),
        faq_match=None,
        pending_confirmation=None,
        next_field=_field("age"),
        contact_method=None,
        early_closing_ready=False,
    )

    assert priority.task == "profile_collection"

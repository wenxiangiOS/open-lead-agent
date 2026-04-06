from src.services.core.first_generation_delivery_service import FirstGenerationDeliveryService


def test_first_generation_delivery_service_strips_technical_blocks_only():
    service = FirstGenerationDeliveryService()

    display, removed = service.extract_display_text(
        '<opening_intent>{"intent":"opening_profile_provided"}</opening_intent>\n'
        "好的呀，你现在常住哪个城市呀？\n"
        "<extract>\n所在地:null\n</extract>"
    )

    assert display == "好的呀，你现在常住哪个城市呀？"
    assert removed == ["opening_intent", "extract"]


def test_first_generation_delivery_service_keeps_plain_text_unchanged():
    service = FirstGenerationDeliveryService()

    display, removed = service.extract_display_text("原来是做IT相关的呀，这个收入水平还挺不错的~你现在是什么学历呀？")

    assert display == "原来是做IT相关的呀，这个收入水平还挺不错的~你现在是什么学历呀？"
    assert removed == []

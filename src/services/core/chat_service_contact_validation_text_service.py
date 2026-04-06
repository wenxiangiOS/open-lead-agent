class ChatServiceContactValidationTextService:
    @staticmethod
    def build_contact_validation_retry_fallback(*, field: str, attempt: int, detail: str) -> str:
        normalized_field = "wechat" if field == "wechat" else "phone"
        normalized_detail = str(detail or "").lower()

        if normalized_field == "phone":
            if attempt <= 1:
                if "soft_region_mismatch_hk" in normalized_detail:
                    return "这个号码看着像香港那边常用的联系方式，如果这是你平时常用的，也可以直接留这个。"
                if "too_long" in normalized_detail:
                    return "这个号码我看着位数有点多，你再核对一下常用手机号发我就行。"
                if "too_short" in normalized_detail:
                    return "这个号码我看着像是还差一位，你再确认一下常用手机号发我就行。"
                return "这个号码我看着格式有点不太对，你再核对一下常用手机号发我就行。"
            if attempt == 2:
                return "这个号码还是有点对不上，你再发一遍常用手机号给我就行，后面联系你也更顺。"
            return "这个号码还是不太对，你核对好常用手机号再发我就行。"

        if normalized_field == "wechat":
            if "length" in normalized_detail or "short" in normalized_detail or attempt <= 1:
                return "这个微信号看着像是没发完整，你直接重新发个常用微信给我就行。"
            if attempt == 2:
                return "这个微信号格式还是有点不对，你再发一遍常用微信给我就行。"
            return "这个微信号还是不太对，你核对好常用微信再发我就行。"

        return ""

    @staticmethod
    def build_contact_invalid_input_close_response(contact_type: str) -> str:
        if contact_type == "wechat":
            variants = [
                "这边我先不反复追着问微信了，等你方便的时候再发我就行。",
                "微信这块我先放一放，后面你方便的话再补给我就好。",
                "那我先不在微信这条上打转了，等你方便的时候再发也行。",
            ]
        else:
            variants = [
                "这边我先不反复追着问电话了，等你方便的时候再发我就行。",
                "电话这块我先放一放，后面你方便的话再补给我就好。",
                "那我先不在电话这条上打转了，等你方便的时候再发也行。",
            ]
        return variants[0]

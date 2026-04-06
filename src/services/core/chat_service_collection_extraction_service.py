from typing import Any, Dict, Optional


class ChatServiceCollectionExtractionService:
    def __init__(self, host: Any) -> None:
        self.host = host

    async def run_extraction(
        self,
        *,
        account_id: str,
        user_profile,
        extracted_data: Dict[str, Any],
        user_message: str,
        extraction_meta: Optional[Dict[str, Dict[str, Any]]] = None,
        turn_id: Optional[int] = None,
    ) -> tuple[str, Dict[str, Any], Any]:
        last_response = await self.host.dialogue_manager.get_last_response(account_id) or ""
        guarded_extracted_data = self.host.turn_understanding_service._apply_extraction_guards(  # noqa: SLF001
            extracted_data,
            user_message,
            last_response=last_response,
        )
        collection_result = await self.host.extraction_service.process_extracted_data(
            account_id,
            user_profile,
            guarded_extracted_data,
            user_message=user_message,
            last_response=last_response,
            extraction_meta=extraction_meta,
            turn_id=turn_id,
        )
        refreshed_user_profile = await self.host.user_service.get_user_profile(account_id)
        return last_response, collection_result, refreshed_user_profile

"""健康检查响应数据构建。Operational health payload helpers."""

from src.llm import LLMSettings
from src.templates import get_active_template


def health_payload() -> dict:
    template = get_active_template()
    llm = LLMSettings.from_env()
    return {
        "status": "ok",
        "service": "open-lead-agent",
        "template_id": template.template.id,
        "llm_provider": llm.provider,
        "llm_model": llm.model,
    }

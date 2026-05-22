"""模板加载、校验、脚手架模块导出。Template utilities exports."""

from src.templates.config import TemplateConfig, get_active_template
from src.templates.guided import (
    GuidedFAQ,
    GuidedTemplateAnswers,
    GuidedTemplateOptions,
    create_guided_template,
    parse_comma_list,
    parse_faq_lines,
)
from src.templates.scaffold import (
    TemplateScaffoldOptions,
    TemplateScaffoldResult,
    create_template_scaffold,
)
from src.templates.validation import (
    TemplateValidationIssue,
    TemplateValidationReport,
    format_validation_report,
    validate_template_config,
)

__all__ = [
    "TemplateConfig",
    "TemplateScaffoldOptions",
    "TemplateScaffoldResult",
    "TemplateValidationIssue",
    "TemplateValidationReport",
    "GuidedFAQ",
    "GuidedTemplateAnswers",
    "GuidedTemplateOptions",
    "create_template_scaffold",
    "create_guided_template",
    "format_validation_report",
    "get_active_template",
    "parse_comma_list",
    "parse_faq_lines",
    "validate_template_config",
]

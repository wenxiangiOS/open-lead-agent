"""模板运行前校验，提前发现配置错误。Template validation checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from src.templates.config import FieldConfig, TemplateConfig

IssueSeverity = Literal["error", "warning"]


@dataclass(frozen=True)
class TemplateValidationIssue:
    severity: IssueSeverity
    code: str
    path: str
    message: str
    suggestion: str = ""

    def public_dict(self) -> dict[str, str]:
        data = {
            "severity": self.severity,
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }
        if self.suggestion:
            data["suggestion"] = self.suggestion
        return data


@dataclass(frozen=True)
class TemplateValidationReport:
    template_id: str
    issues: list[TemplateValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def errors(self) -> list[TemplateValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[TemplateValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    def public_dict(self) -> dict[str, object]:
        return {
            "template_id": self.template_id,
            "ok": self.ok,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [issue.public_dict() for issue in self.issues],
        }


def validate_template_config(template: TemplateConfig) -> TemplateValidationReport:
    issues: list[TemplateValidationIssue] = []
    _validate_field_keys(template, issues)
    _validate_field_settings(template, issues)
    _validate_field_routing(template, issues)
    _validate_field_permissions(template, issues)
    _validate_contact(template, issues)
    _validate_compliance(template, issues)
    _validate_faq(template, issues)
    _validate_rag(template, issues)
    _validate_prompt_setup(template, issues)
    return TemplateValidationReport(template_id=template.template.id, issues=issues)


def format_validation_report(report: TemplateValidationReport) -> str:
    status = "OK" if report.ok else "FAILED"
    lines = [
        f"Template validation: {status}",
        f"template: {report.template_id}",
        f"errors: {len(report.errors)}, warnings: {len(report.warnings)}",
    ]
    if not report.issues:
        lines.append("No issues found.")
        return "\n".join(lines)

    for issue in report.issues:
        prefix = "ERROR" if issue.severity == "error" else "WARN"
        lines.append(f"- [{prefix}] {issue.code} at {issue.path}: {issue.message}")
        if issue.suggestion:
            lines.append(f"  suggestion: {issue.suggestion}")
    return "\n".join(lines)


def _validate_field_keys(
    template: TemplateConfig,
    issues: list[TemplateValidationIssue],
) -> None:
    _add_duplicate_key_issues(
        issues,
        [(field.key, f"fields.{field.key}") for field in template.fields],
        code="duplicate_field_key",
        message="Field keys must be unique.",
    )
    _add_duplicate_key_issues(
        issues,
        [(method.key, f"contact.methods.{method.key}") for method in template.contact.methods],
        code="duplicate_contact_key",
        message="Contact method keys must be unique.",
    )

    field_keys = {field.key for field in template.fields}
    contact_keys = {method.key for method in template.contact.methods}
    overlap = sorted(field_keys & contact_keys)
    for key in overlap:
        issues.append(
            TemplateValidationIssue(
                severity="error",
                code="field_contact_key_conflict",
                path=key,
                message="A profile field and a contact method use the same key.",
                suggestion=(
                    "Rename one of them so saved profile values do not overwrite each other."
                ),
            )
        )


def _validate_field_settings(
    template: TemplateConfig,
    issues: list[TemplateValidationIssue],
) -> None:
    supported_risks = {"low", "normal", "medium", "high", "strict"}
    for field_config in template.fields:
        path = f"fields.{field_config.key}"
        if field_config.risk not in supported_risks:
            issues.append(
                TemplateValidationIssue(
                    severity="warning",
                    code="unknown_field_risk",
                    path=f"{path}.risk",
                    message=f"Unknown field risk level: {field_config.risk}.",
                    suggestion="Use low, normal, medium, high, or strict.",
                )
            )
        if field_config.ask_limit < 0:
            issues.append(
                TemplateValidationIssue(
                    severity="error",
                    code="negative_ask_limit",
                    path=f"{path}.ask_limit",
                    message="ask_limit cannot be negative.",
                    suggestion=(
                        "Use 0 for passive-only fields, or a positive number for active collection."
                    ),
                )
            )
        if field_config.required and field_config.ask_limit <= 0:
            issues.append(
                TemplateValidationIssue(
                    severity="warning",
                    code="required_field_never_asked",
                    path=f"{path}.ask_limit",
                    message="This field is required but cannot be actively asked.",
                    suggestion="Set ask_limit to at least 1, or mark the field as optional.",
                )
            )
        if field_config.ask_limit > 0 and not field_config.ask.strip():
            issues.append(
                TemplateValidationIssue(
                    severity="warning",
                    code="missing_field_ask",
                    path=f"{path}.ask",
                    message="This field can be actively asked but has no example ask text.",
                    suggestion=(
                        "Add a natural ask sentence to help fallback mode and documentation."
                    ),
                )
            )
        if field_config.type == "enum" and not field_config.options:
            issues.append(
                TemplateValidationIssue(
                    severity="warning",
                    code="enum_without_options",
                    path=f"{path}.options",
                    message="Enum fields work better when options are configured.",
                    suggestion=(
                        "Add common values, or change type to text if the value is open-ended."
                    ),
                )
            )

    priorities: dict[int, list[FieldConfig]] = {}
    for field_config in template.fields:
        priorities.setdefault(field_config.priority, []).append(field_config)
    for priority, fields in priorities.items():
        if len(fields) <= 1:
            continue
        keys = ", ".join(field_config.key for field_config in fields)
        issues.append(
            TemplateValidationIssue(
                severity="warning",
                code="duplicate_field_priority",
                path="fields.priority",
                message=f"Multiple fields share priority {priority}: {keys}.",
                suggestion="Use distinct priorities when you want deterministic ordered routing.",
            )
        )


def _validate_field_routing(
    template: TemplateConfig,
    issues: list[TemplateValidationIssue],
) -> None:
    if template.field_routing.mode not in {"auto", "ordered"}:
        issues.append(
            TemplateValidationIssue(
                severity="warning",
                code="unknown_field_routing_mode",
                path="field_routing.mode",
                message=f"Unknown field routing mode: {template.field_routing.mode}.",
                suggestion="Use auto for natural follow-up, or ordered for strict priority order.",
            )
        )

    field_keys = {field_config.key for field_config in template.fields}
    for index, override in enumerate(template.field_routing.overrides):
        path = f"field_routing.overrides[{index}]"
        if override.from_field not in field_keys:
            issues.append(
                TemplateValidationIssue(
                    severity="warning",
                    code="routing_unknown_from_field",
                    path=f"{path}.from",
                    message=f"Routing override references unknown field: {override.from_field}.",
                    suggestion="Use one of the configured field keys.",
                )
            )
        if override.to not in field_keys:
            issues.append(
                TemplateValidationIssue(
                    severity="warning",
                    code="routing_unknown_to_field",
                    path=f"{path}.to",
                    message=f"Routing override targets unknown field: {override.to}.",
                    suggestion="Use one of the configured field keys.",
                )
            )


def _validate_field_permissions(
    template: TemplateConfig,
    issues: list[TemplateValidationIssue],
) -> None:
    if not template.field_permissions.enabled:
        return

    field_keys = {field_config.key for field_config in template.fields}
    contact_keys = {method.key for method in template.contact.methods}
    known_keys = field_keys | contact_keys

    for index, rule in enumerate(template.field_permissions.rules):
        path = f"field_permissions.rules[{index}]"
        if not (rule.intents or rule.reply_acts or rule.expected_fields):
            issues.append(
                TemplateValidationIssue(
                    severity="warning",
                    code="field_permission_rule_without_condition",
                    path=path,
                    message="Field permission rule has no matching condition.",
                    suggestion="Add intents, reply_acts, or expected_fields.",
                )
            )
        if not (rule.allow_fields or rule.block_fields):
            issues.append(
                TemplateValidationIssue(
                    severity="warning",
                    code="field_permission_rule_without_action",
                    path=path,
                    message="Field permission rule does not allow or block any fields.",
                    suggestion="Add allow_fields or block_fields.",
                )
            )
        for field_key in rule.expected_fields:
            if field_key not in known_keys:
                issues.append(
                    TemplateValidationIssue(
                        severity="warning",
                        code="field_permission_unknown_expected_field",
                        path=f"{path}.expected_fields",
                        message=(
                            "Field permission rule references unknown expected field: "
                            f"{field_key}."
                        ),
                        suggestion="Use one of the configured profile or contact field keys.",
                    )
                )
        for field_key in rule.allow_fields:
            if field_key not in known_keys:
                issues.append(
                    TemplateValidationIssue(
                        severity="warning",
                        code="field_permission_unknown_allow_field",
                        path=f"{path}.allow_fields",
                        message=f"Field permission rule allows unknown field: {field_key}.",
                        suggestion="Use one of the configured profile or contact field keys.",
                    )
                )
        for field_key in rule.block_fields:
            if field_key not in known_keys:
                issues.append(
                    TemplateValidationIssue(
                        severity="warning",
                        code="field_permission_unknown_block_field",
                        path=f"{path}.block_fields",
                        message=f"Field permission rule blocks unknown field: {field_key}.",
                        suggestion="Use one of the configured profile or contact field keys.",
                    )
                )


def _validate_contact(
    template: TemplateConfig,
    issues: list[TemplateValidationIssue],
) -> None:
    contact = template.contact
    if not contact.enabled:
        return
    if not contact.methods:
        issues.append(
            TemplateValidationIssue(
                severity="warning",
                code="contact_enabled_without_methods",
                path="contact.methods",
                message="Contact collection is enabled but no contact methods are configured.",
                suggestion="Add phone/wechat/email methods, or set contact.enabled to false.",
            )
        )
    supported_risks = {"low", "normal", "medium", "high", "strict"}
    for index, method in enumerate(contact.methods):
        if method.risk not in supported_risks:
            issues.append(
                TemplateValidationIssue(
                    severity="warning",
                    code="unknown_contact_risk",
                    path=f"contact.methods[{index}].risk",
                    message=f"Unknown contact risk level: {method.risk}.",
                    suggestion="Use low, normal, medium, high, or strict.",
                )
            )
        if method.ask_limit < 0:
            issues.append(
                TemplateValidationIssue(
                    severity="error",
                    code="negative_contact_ask_limit",
                    path=f"contact.methods[{index}].ask_limit",
                    message="Contact method ask_limit cannot be negative.",
                    suggestion="Use 0 to make it passive-only, or a positive number.",
                )
            )

    field_keys = {field_config.key for field_config in template.fields}
    trigger = contact.trigger
    for field_key in trigger.required_fields:
        if field_key not in field_keys:
            issues.append(
                TemplateValidationIssue(
                    severity="error",
                    code="contact_unknown_required_field",
                    path="contact.trigger.required_fields",
                    message=f"Contact trigger references unknown required field: {field_key}.",
                    suggestion="Use a configured field key, or remove it from required_fields.",
                )
            )
    for field_key in trigger.optional_fields:
        if field_key not in field_keys:
            issues.append(
                TemplateValidationIssue(
                    severity="warning",
                    code="contact_unknown_optional_field",
                    path="contact.trigger.optional_fields",
                    message=f"Contact trigger references unknown optional field: {field_key}.",
                    suggestion="Use a configured field key, or remove it from optional_fields.",
                )
            )
    fallback_required_fields = [field.key for field in template.fields if field.required]
    required_count = len(trigger.required_fields or fallback_required_fields)
    if trigger.min_required_collected < 0:
        issues.append(
            TemplateValidationIssue(
                severity="error",
                code="contact_negative_min_required",
                path="contact.trigger.min_required_collected",
                message="min_required_collected cannot be negative.",
                suggestion="Use 0 to mean all required fields, or a positive threshold.",
            )
        )
    if required_count and trigger.min_required_collected > required_count:
        issues.append(
            TemplateValidationIssue(
                severity="warning",
                code="contact_threshold_too_high",
                path="contact.trigger.min_required_collected",
                message="Contact threshold is higher than the number of required trigger fields.",
                suggestion="Lower min_required_collected so contact collection can be reached.",
            )
        )


def _validate_compliance(
    template: TemplateConfig,
    issues: list[TemplateValidationIssue],
) -> None:
    if not template.compliance.enabled:
        return
    field_keys = {field_config.key for field_config in template.fields}
    supported_operators = {
        "equals",
        "eq",
        "==",
        "not_equals",
        "ne",
        "!=",
        "contains",
        "in",
        "lt",
        "lte",
        "gt",
        "gte",
    }
    rule_ids: set[str] = set()
    for index, rule in enumerate(template.compliance.rules):
        path = f"compliance.rules[{index}]"
        if rule.id in rule_ids:
            issues.append(
                TemplateValidationIssue(
                    severity="error",
                    code="duplicate_compliance_rule_id",
                    path=f"{path}.id",
                    message=f"Duplicate compliance rule id: {rule.id}.",
                    suggestion="Give each rule a stable unique id.",
                )
            )
        rule_ids.add(rule.id)
        if rule.when.field and rule.when.field not in field_keys:
            issues.append(
                TemplateValidationIssue(
                    severity="error",
                    code="compliance_unknown_field",
                    path=f"{path}.when.field",
                    message=f"Compliance rule references unknown field: {rule.when.field}.",
                    suggestion="Use a configured field key.",
                )
            )
        if not rule.when.field and not rule.semantic_signals:
            issues.append(
                TemplateValidationIssue(
                    severity="warning",
                    code="compliance_rule_without_trigger",
                    path=path,
                    message=(
                        "Compliance rule has no field condition or semantic signal: "
                        f"{rule.id}."
                    ),
                    suggestion="Add when.field or semantic_signals.",
                )
            )
        if rule.when.operator not in supported_operators:
            issues.append(
                TemplateValidationIssue(
                    severity="error",
                    code="unsupported_compliance_operator",
                    path=f"{path}.when.operator",
                    message=f"Unsupported operator: {rule.when.operator}.",
                    suggestion="Use equals, contains, in, lt, lte, gt, or gte.",
                )
            )
        if rule.action == "end" and not rule.message.strip():
            issues.append(
                TemplateValidationIssue(
                    severity="warning",
                    code="compliance_end_without_message",
                    path=f"{path}.message",
                    message="Ending a conversation without a message can feel abrupt.",
                    suggestion="Add a short, polite closing message for this rule.",
                )
            )


def _validate_faq(template: TemplateConfig, issues: list[TemplateValidationIssue]) -> None:
    intents: set[str] = set()
    for index, faq in enumerate(template.faq):
        path = f"faq[{index}]"
        if faq.intent in intents:
            issues.append(
                TemplateValidationIssue(
                    severity="warning",
                    code="duplicate_faq_intent",
                    path=f"{path}.intent",
                    message=f"Duplicate FAQ intent: {faq.intent}.",
                    suggestion="Use unique intent names to make debug output easier to read.",
                )
            )
        intents.add(faq.intent)
        if not faq.keywords:
            issues.append(
                TemplateValidationIssue(
                    severity="warning",
                    code="faq_without_keywords",
                    path=f"{path}.keywords",
                    message=(
                        "FAQ entries without keywords cannot be matched by the simple FAQ engine."
                    ),
                    suggestion="Add common user phrases for this question.",
                )
            )
        if not faq.answer.strip():
            issues.append(
                TemplateValidationIssue(
                    severity="error",
                    code="faq_without_answer",
                    path=f"{path}.answer",
                    message="FAQ answer cannot be empty.",
                    suggestion="Add the answer text, or remove this FAQ entry.",
                )
            )


def _validate_rag(template: TemplateConfig, issues: list[TemplateValidationIssue]) -> None:
    if not template.rag.enabled:
        return
    if not template.rag.knowledge_base_path.strip():
        issues.append(
            TemplateValidationIssue(
                severity="error",
                code="rag_missing_path",
                path="rag.knowledge_base_path",
                message="RAG is enabled but no knowledge base path is configured.",
                suggestion="Set knowledge_base_path, or turn rag.enabled off.",
            )
        )
        return

    path = Path(template.rag.knowledge_base_path)
    if not path.exists():
        issues.append(
            TemplateValidationIssue(
                severity="warning",
                code="rag_path_not_found",
                path="rag.knowledge_base_path",
                message=(
                    "Knowledge base path does not exist from the current working "
                    f"directory: {path}."
                ),
                suggestion="Create the directory, or update knowledge_base_path.",
            )
        )


def _validate_prompt_setup(
    template: TemplateConfig,
    issues: list[TemplateValidationIssue],
) -> None:
    if template.dialogue_policy.file and not template.dialogue_policy.sections:
        issues.append(
            TemplateValidationIssue(
                severity="warning",
                code="dialogue_policy_file_loaded_empty",
                path="dialogue_policy.file",
                message="Dialogue policy file is configured but no policy sections were loaded.",
                suggestion="Check that the YAML file contains a sections list.",
            )
        )
    if template.extraction.enabled and template.extraction.prompt:
        if "{configured_fields}" not in template.extraction.prompt:
            issues.append(
                TemplateValidationIssue(
                    severity="warning",
                    code="extraction_prompt_missing_configured_fields",
                    path="extraction.prompt",
                    message="The extraction prompt does not include {configured_fields}.",
                    suggestion=(
                        "Include {configured_fields} so custom rules stay aligned with "
                        "configured fields."
                    ),
                )
            )
        if "{user_message}" not in template.extraction.prompt:
            issues.append(
                TemplateValidationIssue(
                    severity="warning",
                    code="extraction_prompt_missing_user_message",
                    path="extraction.prompt",
                    message="The extraction prompt does not include {user_message}.",
                    suggestion=(
                        "Include {user_message} when custom rules need the raw user message."
                    ),
                )
            )


def _add_duplicate_key_issues(
    issues: list[TemplateValidationIssue],
    keyed_paths: list[tuple[str, str]],
    *,
    code: str,
    message: str,
) -> None:
    seen: dict[str, str] = {}
    for key, path in keyed_paths:
        if key not in seen:
            seen[key] = path
            continue
        issues.append(
            TemplateValidationIssue(
                severity="error",
                code=code,
                path=path,
                message=f"{message} Duplicate key: {key}.",
                suggestion=f"First seen at {seen[key]}. Rename this key.",
            )
        )

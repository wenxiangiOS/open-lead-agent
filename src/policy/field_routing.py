"""配置字段的自然下一问路由。

用户只需要配置要收集哪些字段；这个文件尽量根据上下文选择更自然的下一问，
避免每个模板作者都要手动设计字段衔接顺序。
"""

from dataclasses import dataclass
from typing import Any

from src.collection import CollectionEngine
from src.collection.state import FieldState
from src.templates.config import FieldConfig, TemplateConfig


@dataclass(frozen=True)
class FieldRoutingPlan:
    """本轮字段路由结果。

    main 是本轮真正推进的主字段；side 是可选顺带字段，只作为拟人化提示，
    不改变旧版 next_field API 的主字段含义。
    """

    main: FieldConfig | None
    side: FieldConfig | None = None
    reason: str = ""


class FieldRoutingPolicy:
    def __init__(self, template: TemplateConfig):
        self.template = template
        self.collection = CollectionEngine(template)

    def next_field(
        self,
        profile: dict[str, Any],
        ask_counts: dict[str, int],
        collected_this_turn: dict[str, Any] | None = None,
        field_states: dict[str, FieldState] | None = None,
    ) -> FieldConfig | None:
        return self.plan(profile, ask_counts, collected_this_turn, field_states).main

    def plan(
        self,
        profile: dict[str, Any],
        ask_counts: dict[str, int],
        collected_this_turn: dict[str, Any] | None = None,
        field_states: dict[str, FieldState] | None = None,
    ) -> FieldRoutingPlan:
        if self.template.field_routing.mode == "ordered":
            return FieldRoutingPlan(
                main=self.collection.next_field(profile, ask_counts),
                reason="ordered",
            )

        collected_this_turn = collected_this_turn or {}
        contextual = self._contextual_next_field(
            profile,
            ask_counts,
            collected_this_turn,
            field_states,
        )
        if contextual is not None:
            return contextual
        return self._fallback_plan(profile, ask_counts, field_states)

    def _contextual_next_field(
        self,
        profile: dict[str, Any],
        ask_counts: dict[str, int],
        collected_this_turn: dict[str, Any],
        field_states: dict[str, FieldState] | None,
    ) -> FieldRoutingPlan | None:
        if (
            not self.template.field_routing.prefer_contextual_followup
            or not self.template.humanization.prefer_contextual_followup
        ):
            return None

        candidates = self._candidate_fields(profile, ask_counts, field_states)
        if not candidates:
            return None

        core_match = self._best_related_candidate(
            collected_this_turn,
            candidates.core,
            min_score=20,
        )
        if core_match is not None:
            return FieldRoutingPlan(
                main=core_match,
                reason="contextual_core_followup",
            )

        medium_match = self._best_related_candidate(
            collected_this_turn,
            candidates.medium,
            min_score=40,
        )
        if medium_match is not None:
            return FieldRoutingPlan(
                main=medium_match,
                reason="contextual_medium_followup",
            )

        return None

    def _candidate_fields(
        self,
        profile: dict[str, Any],
        ask_counts: dict[str, int],
        field_states: dict[str, FieldState] | None,
    ) -> "_TieredCandidates":
        core = [
            field
            for field in self._ordered_fields()
            if self._field_tier(field) == "core"
            and self._should_ask(field, profile, ask_counts, field_states)
        ]
        medium = [
            field
            for field in self._ordered_fields()
            if self._field_tier(field) == "medium"
            and self._should_ask(field, profile, ask_counts, field_states)
        ]
        low = [
            field
            for field in self._ordered_fields()
            if self._field_tier(field) == "low"
            and self._should_ask(field, profile, ask_counts, field_states)
        ]
        return _TieredCandidates(core=core, medium=medium, low=low)

    def _fallback_plan(
        self,
        profile: dict[str, Any],
        ask_counts: dict[str, int],
        field_states: dict[str, FieldState] | None,
    ) -> FieldRoutingPlan:
        if field_states is None:
            main = self.collection.next_field(profile, ask_counts)
            return FieldRoutingPlan(
                main=main,
                side=self._side_for_main(main, profile, ask_counts),
                reason="core_main_with_optional_side"
                if main is not None and self._field_tier(main) == "core"
                else "ordered_fallback",
            )
        candidates = self._candidate_fields(profile, ask_counts, field_states)
        if candidates.core:
            main = candidates.core[0]
            return FieldRoutingPlan(
                main=main,
                side=self._side_for_main(main, profile, ask_counts, field_states),
                reason="core_main_with_optional_side",
            )
        if candidates.medium:
            return FieldRoutingPlan(main=candidates.medium[0], reason="medium_after_core")
        return FieldRoutingPlan(main=None, reason="no_field")

    def _best_related_candidate(
        self,
        collected_this_turn: dict[str, Any],
        candidates: list[FieldConfig],
        *,
        min_score: int,
    ) -> FieldConfig | None:
        best_field: FieldConfig | None = None
        best_score = 0
        for source_key in collected_this_turn:
            source_field = self._field_by_key(source_key)
            source_tag = self._semantic_tag(source_field)
            if not source_tag:
                continue
            for candidate in candidates:
                score = self._transition_weight(source_key, source_tag, candidate)
                if score > best_score:
                    best_field = candidate
                    best_score = score
        if best_score < min_score:
            return None
        return best_field

    def _side_for_main(
        self,
        main: FieldConfig | None,
        profile: dict[str, Any],
        ask_counts: dict[str, int],
        field_states: dict[str, FieldState] | None = None,
    ) -> FieldConfig | None:
        if main is None or self._field_tier(main) != "core":
            return None
        candidates = self._candidate_fields(profile, ask_counts, field_states).medium
        best_field: FieldConfig | None = None
        best_score = 0
        source_tag = self._semantic_tag(main)
        if not source_tag:
            return None
        for candidate in candidates:
            score = self._transition_weight(main.key, source_tag, candidate)
            if score > best_score:
                best_field = candidate
                best_score = score
        if best_score < 35:
            return None
        return best_field

    def _ordered_fields(self) -> list[FieldConfig]:
        return sorted(self.template.fields, key=lambda field: field.priority)

    def _should_ask(
        self,
        field: FieldConfig,
        profile: dict[str, Any],
        ask_counts: dict[str, int],
        field_states: dict[str, FieldState] | None,
    ) -> bool:
        if field_states is not None:
            state = field_states.get(field.key)
            return bool(state and not state.covered and field.ask_limit > 0)
        if profile.get(field.key) or field.ask_limit <= 0:
            return False
        return ask_counts.get(field.key, 0) < field.ask_limit

    def _field_tier(self, field: FieldConfig) -> str:
        if field.tier in {"core", "medium", "low"}:
            return field.tier
        if field.required:
            return "core"
        return "medium"

    def _transition_weight(
        self, source_key: str, source_tag: str, candidate: FieldConfig
    ) -> int:
        for override in self.template.field_routing.overrides:
            if override.from_field == source_key and override.to == candidate.key:
                return override.weight

        target_tag = self._semantic_tag(candidate)
        if not target_tag:
            return 0
        return self._default_routes().get(source_tag, {}).get(target_tag, 0)

    def _field_by_key(self, key: str) -> FieldConfig | None:
        for field in self.template.fields:
            if field.key == key:
                return field
        return None

    def _semantic_tag(self, field: FieldConfig | None) -> str:
        if field is None:
            return ""
        text = " ".join(
            [
                field.key.lower(),
                field.label.lower(),
                field.description.lower(),
                " ".join(example.lower() for example in field.examples),
            ]
        )
        patterns = {
            "place": ("location", "city", "region", "address", "城市", "地区", "地址", "所在地"),
            "work": ("occupation", "job", "work", "career", "行业", "职业", "工作"),
            "money": ("income", "salary", "budget", "price", "收入", "薪资", "工资", "预算"),
            "age": ("age", "birth", "年龄", "年纪", "出生"),
            "education": ("education", "degree", "school", "学历", "学校", "年级"),
            "status": ("marital", "status", "婚姻", "婚况", "状态"),
            "preference": (
                "requirement",
                "preference",
                "need",
                "goal",
                "要求",
                "偏好",
                "需求",
                "目标",
            ),
        }
        for tag, tokens in patterns.items():
            if any(token in text for token in tokens):
                return tag
        return ""

    def _default_routes(self) -> dict[str, dict[str, int]]:
        return {
            "place": {"work": 50, "preference": 20, "money": 10},
            "education": {"work": 35, "status": 30, "preference": 25},
            "work": {"money": 45, "preference": 20},
            "age": {"status": 35, "preference": 25},
            "status": {"preference": 40},
            "preference": {"money": 15},
        }


@dataclass(frozen=True)
class _TieredCandidates:
    core: list[FieldConfig]
    medium: list[FieldConfig]
    low: list[FieldConfig]

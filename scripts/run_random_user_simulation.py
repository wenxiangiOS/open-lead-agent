#!/usr/bin/env python3
"""真实用户随机仿真回归（含时延剖析/模板风险/场景覆盖）。"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sys
import statistics
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.requests import ChatRequest
from src.services.ai_service import AIService
from src.services.core.chat_service import ChatService
from src.services.data.user_service import UserService
from tests.real_ai.scenario_runner import ScenarioLoader

LOCATIONS = ["深圳", "广州", "杭州", "上海", "北京", "成都", "武汉", "苏州"]
EDUCATIONS = ["大专", "本科", "硕士"]
OCCUPATIONS = ["运营", "产品", "程序员", "教师", "设计师", "财务", "销售", "护士"]
PREFERENCES = ["成熟稳重", "三观合拍", "上进", "脾气好", "会沟通", "同城优先", "高一点", "阳光一点"]
KNOWN_OCCUPATIONS = OCCUPATIONS + ["文员", "老师", "医生", "行政", "人事", "客服", "自由职业"]
KNOWN_EDUCATIONS = EDUCATIONS + ["博士", "高中", "中专"]
KNOWN_MARITAL_STATUSES = ["单身", "未婚", "离异", "离婚", "已婚"]


@dataclass
class Persona:
    sex: str
    age_bucket: str
    location: str
    education: str
    occupation: str
    preference: str
    faq_prob: float
    joking_prob: float
    defensive_prob: float
    contact_willingness: str  # phone / wechat / none


@dataclass
class TurnRecord:
    index: int
    user: str
    assistant: str
    latency_s: float
    perf: dict[str, float]
    collected_info: dict[str, Any] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)


@dataclass
class SessionResult:
    session_id: str
    scenario_id: str
    category: str
    tags: list[str]
    persona: Persona
    turns: list[TurnRecord]
    final_profile: dict[str, Any]
    field_checks: list[dict[str, Any]]
    field_failures: list[str]
    policy_checks: list[dict[str, Any]]
    policy_failures: list[str]
    duration_s: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "scenario_id": self.scenario_id,
            "category": self.category,
            "tags": self.tags,
            "persona": asdict(self.persona),
            "turns": [asdict(t) for t in self.turns],
            "final_profile": self.final_profile,
            "field_checks": self.field_checks,
            "field_failures": self.field_failures,
            "policy_checks": self.policy_checks,
            "policy_failures": self.policy_failures,
            "duration_s": round(self.duration_s, 3),
        }


class TimingProbe:
    """Per-turn phase timing probe without changing business logic."""

    def __init__(self, chat_service: ChatService) -> None:
        self.chat_service = chat_service
        self.current: dict[str, float] = {}
        self._restore: list[tuple[Any, str, Any]] = []
        self._install()

    def begin_turn(self) -> None:
        self.current = {}

    def end_turn(self, total_s: float) -> dict[str, float]:
        known = sum(self.current.values())
        self.current["other"] = max(0.0, total_s - known)
        self.current["total"] = total_s
        return {k: round(v, 4) for k, v in self.current.items()}

    def close(self) -> None:
        for obj, attr, fn in reversed(self._restore):
            setattr(obj, attr, fn)

    def _add(self, name: str, delta: float) -> None:
        self.current[name] = self.current.get(name, 0.0) + delta

    def _wrap_async(self, obj: Any, attr: str, phase: str) -> None:
        original = getattr(obj, attr)

        async def wrapped(*args, **kwargs):
            started = time.time()
            try:
                return await original(*args, **kwargs)
            finally:
                self._add(phase, time.time() - started)

        self._restore.append((obj, attr, original))
        setattr(obj, attr, wrapped)

    def _install(self) -> None:
        self._wrap_async(self.chat_service, "_call_ai", "ai_call")
        self._wrap_async(self.chat_service.user_service, "get_user_profile", "profile_load")
        self._wrap_async(self.chat_service.user_service, "save_user_profile", "profile_save")
        self._wrap_async(self.chat_service.conversation_rule_service, "try_handle", "rule_check")
        self._wrap_async(self.chat_service.dialogue_manager, "get_conversation_context", "context_load")
        self._wrap_async(self.chat_service.profile_collection_coordinator, "process_collection", "extract_collect")
        self._wrap_async(self.chat_service, "_build_chat_response", "response_build")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="真实用户随机仿真回归")
    parser.add_argument("--sessions", type=int, default=20, help="随机会话数量（非覆盖模式）")
    parser.add_argument("--min-turns", type=int, default=6, help="每会话最少轮次")
    parser.add_argument("--max-turns", type=int, default=12, help="每会话最多轮次")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--cover-scenarios", action="store_true", help="覆盖场景模式：按场景逐个模拟")
    parser.add_argument(
        "--scenario-file",
        default=None,
        help="场景文件或目录；覆盖模式会自动合并 scenarios + scenarios_pending（当未指定时）",
    )
    parser.add_argument("--scenario-id", action="append", dest="scenario_ids", help="只跑指定场景，可传多次")
    parser.add_argument("--max-scenarios", type=int, help="覆盖模式最多跑前 N 个场景")
    parser.add_argument("--template-risk-threshold", type=float, default=0.18, help="模板化风险阈值")
    parser.add_argument(
        "--report-dir",
        default=str(PROJECT_ROOT / "reports/real_ai_realism"),
        help="报告输出目录",
    )
    parser.add_argument("--verbose", action="store_true", help="打印逐轮详情")
    return parser.parse_args()


def _load_coverage_scenarios(args: argparse.Namespace) -> list[dict[str, Any]]:
    merged = []
    if not args.scenario_file:
        for p in [PROJECT_ROOT / "tests/real_ai/scenarios", PROJECT_ROOT / "tests/real_ai/scenarios_pending"]:
            if p.exists():
                merged.extend(ScenarioLoader(p).load())
    else:
        scenario_path = Path(args.scenario_file)
        merged = ScenarioLoader(scenario_path).load()

    scenarios = [
        {
            "id": s.scenario_id,
            "category": s.category,
            "tags": s.tags,
            "messages": s.messages,
        }
        for s in merged
        if s.category != "mq"
    ]
    if args.scenario_ids:
        allowed = set(args.scenario_ids)
        scenarios = [x for x in scenarios if x["id"] in allowed]
    if args.max_scenarios is not None:
        scenarios = scenarios[: args.max_scenarios]
    return scenarios


def _build_persona(rng: random.Random) -> Persona:
    return Persona(
        sex=rng.choice(["男", "女"]),
        age_bucket=rng.choice(["85后", "90后", "95后"]),
        location=rng.choice(LOCATIONS),
        education=rng.choice(EDUCATIONS),
        occupation=rng.choice(OCCUPATIONS),
        preference=rng.choice(PREFERENCES),
        faq_prob=rng.uniform(0.08, 0.35),
        joking_prob=rng.uniform(0.05, 0.25),
        defensive_prob=rng.uniform(0.05, 0.25),
        contact_willingness=rng.choice(["phone", "wechat", "none"]),
    )


def _split_dense_message(text: str) -> list[str]:
    raw = str(text or "").strip()
    if not raw:
        return []
    parts = re.split(r"[，,。;；!?！？、]\s*|并且|然后|还有|另外", raw)
    out = [p.strip() for p in parts if p and p.strip()]
    if len(out) <= 1:
        return [raw]
    return out[:4]


def _inject_random_behavior(rng: random.Random, persona: Persona) -> str | None:
    x = rng.random()
    if x < persona.faq_prob:
        return rng.choice(["怎么收费", "你们靠谱吗", "怎么匹配", "可以先看照片吗", "会泄露隐私吗"])
    if x < persona.faq_prob + persona.joking_prob:
        return rng.choice(["你查户口呢", "问得挺细啊", "这是面试吗"])
    if x < persona.faq_prob + persona.joking_prob + persona.defensive_prob:
        return rng.choice(["这个为啥要问", "这个不方便说", "我先不想留联系方式"])
    return None


def _normalize_template(text: str) -> str:
    text = re.sub(r"\d+", "#", (text or ""))
    text = re.sub(r"[A-Za-z]+", "EN", text)
    text = re.sub(r"[，,。;；!?！？、~～\s]+", "", text)
    return text[:80]


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def _check_turn(user: str, assistant: str) -> list[str]:
    fails: list[str] = []
    if not assistant.strip():
        fails.append("empty_response")
    if len(assistant) > 280:
        fails.append("response_too_long")
    faq_keys = ["收费", "靠谱", "匹配", "照片", "隐私", "安全"]
    if any(k in user for k in faq_keys) and not any(k in assistant for k in faq_keys + ["免费", "牵线", "安排"]):
        fails.append("faq_not_answered_first")
    return fails


def _check_profile_fields(persona: Persona, profile: dict[str, Any], turns: list[TurnRecord]) -> tuple[list[dict[str, Any]], list[str]]:
    return _check_profile_fields_with_expected_sex(persona, profile, turns, expected_sex=persona.sex)


def _infer_expected_sex_from_turns(turns: list[str]) -> str | None:
    text = " ".join(str(t or "") for t in turns)
    if any(token in text for token in ["我是女生", "我是女的", "女生", "小姐姐"]):
        return "女"
    if any(token in text for token in ["我是男生", "我是男的", "男生", "小哥哥"]):
        return "男"
    return None


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip().lower()


def _normalize_phone(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if digits.startswith("86") and len(digits) == 13 and digits[2] == "1":
        digits = digits[2:]
    return digits


def _normalize_wechat(value: Any) -> str:
    return str(value or "").strip().lower()


def _extract_explicit_phone(text: str) -> str | None:
    candidates = re.findall(r"(?:\+?86[-\s]?)?(1\d{10})", text)
    if candidates:
        return candidates[-1]

    hk_candidates = re.findall(r"\b(\d{8})\b", text)
    if hk_candidates and any(marker in text for marker in ["电话", "号码", "手机号"]):
        return hk_candidates[-1]
    return None


def _extract_explicit_wechat(text: str) -> str | None:
    patterns = [
        r"(?:微信(?:号)?|wx|vx)[：:\s]*([A-Za-z][A-Za-z0-9_-]{4,19})",
        r"([A-Za-z][A-Za-z0-9_-]{5,19})\s*(?:是)?(?:我的)?微信",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if matches:
            return matches[-1]
    return None


def _extract_explicit_age(text: str) -> str | None:
    age_match = re.search(r"(\d{2})岁", text)
    if age_match:
        return age_match.group(1)
    bucket_match = re.search(r"((?:85|90|95)后)", text)
    if bucket_match:
        return bucket_match.group(1)
    return None


def _extract_explicit_partner_requirement(text: str) -> str | None:
    patterns = [
        r"(?:想找|喜欢|偏好|期待)([^，。,.；;]{2,14})",
        r"(?:找)([^，。,.；;]{2,14})(?:的|就行|就可以)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1).strip()
            if candidate and all(token not in candidate for token in ["对象", "男生", "女生"]):
                return candidate
    return None


def _infer_expected_profile_from_turns(turns: list[TurnRecord]) -> dict[str, Any]:
    expected: dict[str, Any] = {}
    combined_text = " ".join(t.user for t in turns)

    sex = _infer_expected_sex_from_turns([t.user for t in turns])
    if sex:
        expected["sex"] = sex

    age = _extract_explicit_age(combined_text)
    if age:
        expected["age"] = age

    for location in LOCATIONS + ["香港"]:
        if location in combined_text:
            expected["location"] = location
            break

    for education in sorted(KNOWN_EDUCATIONS, key=len, reverse=True):
        if education in combined_text:
            expected["education"] = education
            break

    for occupation in sorted(KNOWN_OCCUPATIONS, key=len, reverse=True):
        if occupation in combined_text:
            expected["occupation"] = occupation
            break

    for status in KNOWN_MARITAL_STATUSES:
        if status in combined_text:
            expected["marital_status"] = status
            break

    phone = _extract_explicit_phone(combined_text)
    if phone:
        expected["phone"] = phone

    wechat = _extract_explicit_wechat(combined_text)
    if wechat:
        expected["wechat"] = wechat

    partner_requirement = _extract_explicit_partner_requirement(combined_text)
    if partner_requirement:
        expected["partner_requirement"] = partner_requirement

    return expected


def _check_profile_fields_with_expected_sex(
    persona: Persona,
    profile: dict[str, Any],
    turns: list[TurnRecord],
    *,
    expected_sex: str | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    expected_profile = _infer_expected_profile_from_turns(turns)

    def add(name: str, passed: bool, expected: Any, actual: Any, note: str = "") -> None:
        checks.append(
            {
                "name": name,
                "passed": bool(passed),
                "expected": expected,
                "actual": actual,
                "note": note,
            }
        )
        if not passed:
            failures.append(f"{name}: expected={expected!r}, actual={actual!r}{' (' + note + ')' if note else ''}")

    # 基础字段
    if expected_sex:
        add("sex_equals_persona", profile.get("sex") == expected_sex, expected_sex, profile.get("sex"))
    add("location_truthy", bool(profile.get("location")), "non-empty", profile.get("location"))
    add("education_truthy", bool(profile.get("education")), "non-empty", profile.get("education"))
    add("occupation_truthy", bool(profile.get("occupation")), "non-empty", profile.get("occupation"))

    # 避免污染（常见占位词）
    polluted_values = {"值", "未知", "null", "None"}
    add(
        "occupation_not_placeholder",
        str(profile.get("occupation") or "").strip() not in polluted_values,
        f"not in {sorted(polluted_values)}",
        profile.get("occupation"),
    )

    # 年龄可为空，但若有值应在合理范围
    age = profile.get("age")
    age_ok = True
    if age not in (None, "", "未留"):
        try:
            age_ok = 18 <= int(age) <= 60
        except Exception:
            age_ok = False
    add("age_reasonable_if_present", age_ok, "18-60 or empty", age)

    if expected_profile.get("location"):
        actual_location = _normalize_text(profile.get("location"))
        expected_location = _normalize_text(expected_profile["location"])
        add(
            "location_matches_user_stated",
            bool(actual_location) and expected_location in actual_location,
            expected_profile["location"],
            profile.get("location"),
        )

    if expected_profile.get("education"):
        add(
            "education_matches_user_stated",
            _normalize_text(profile.get("education")) == _normalize_text(expected_profile["education"]),
            expected_profile["education"],
            profile.get("education"),
        )

    if expected_profile.get("occupation"):
        add(
            "occupation_matches_user_stated",
            _normalize_text(profile.get("occupation")) == _normalize_text(expected_profile["occupation"]),
            expected_profile["occupation"],
            profile.get("occupation"),
        )

    if expected_profile.get("marital_status"):
        add(
            "marital_status_matches_user_stated",
            _normalize_text(profile.get("marital_status")) == _normalize_text(expected_profile["marital_status"]),
            expected_profile["marital_status"],
            profile.get("marital_status"),
        )

    if expected_profile.get("age"):
        actual_age = str(profile.get("age") or "").strip()
        expected_age = str(expected_profile["age"])
        age_match = bool(actual_age) and (
            actual_age == expected_age
            or expected_age in actual_age
            or actual_age in expected_age
        )
        add("age_matches_user_stated", age_match, expected_age, profile.get("age"))

    # 联系方式一致性（放宽判定）
    contact = str(profile.get("contact") or "")
    phone = profile.get("phone")
    wechat = profile.get("wechat")
    contact_ok = True
    if contact and "已留" in contact:
        contact_ok = bool(phone or wechat)
    add("contact_consistency", contact_ok, "if contact shows collected then phone/wechat exists", {"contact": contact, "phone": phone, "wechat": wechat})

    # 若用户在对话中明确给过偏好，最终应尽量有 partner_requirement
    user_text = " ".join(t.user for t in turns)
    mentions_pref = any(k in user_text for k in ["喜欢", "想找", "偏好", "成熟", "稳重", "高一点"])
    if mentions_pref:
        add(
            "partner_requirement_when_mentioned",
            bool(profile.get("partner_requirement")),
            "non-empty",
            profile.get("partner_requirement"),
            "user mentioned preference in turns",
        )

    if expected_profile.get("partner_requirement"):
        add(
            "partner_requirement_matches_user_stated",
            bool(profile.get("partner_requirement")) and _normalize_text(expected_profile["partner_requirement"]) in _normalize_text(profile.get("partner_requirement")),
            expected_profile["partner_requirement"],
            profile.get("partner_requirement"),
        )

    if expected_profile.get("phone"):
        add(
            "phone_matches_user_stated",
            _normalize_phone(profile.get("phone")) == _normalize_phone(expected_profile["phone"]),
            expected_profile["phone"],
            profile.get("phone"),
        )

    if expected_profile.get("wechat"):
        add(
            "wechat_matches_user_stated",
            _normalize_wechat(profile.get("wechat")) == _normalize_wechat(expected_profile["wechat"]),
            expected_profile["wechat"],
            profile.get("wechat"),
        )

    return checks, failures


FIELD_KEYWORDS: dict[str, list[str]] = {
    "sex": ["男", "女", "性别", "小哥哥", "小姐姐"],
    "age": ["年龄", "多大", "年龄段", "几岁", "90后", "95后", "85后"],
    "education": ["学历", "本科", "大专", "硕士", "博士"],
    "occupation": ["职业", "做什么", "工作", "行业"],
    "location": ["城市", "哪里", "哪边", "工作生活", "坐标"],
    "marital_status": ["婚况", "婚姻", "单身", "未婚", "离异"],
    "monthly_income": ["月薪", "收入", "薪资", "工资"],
    "partner_requirement": ["想找", "择偶", "要求", "期待", "喜欢什么类型"],
    "contact_phone": ["电话", "号码", "手机号", "方便留个电话"],
    "contact_wechat": ["微信", "vx", "wx", "留个微信"],
    "height": ["身高"],
    "weight": ["体重"],
    "last_name": ["怎么称呼", "名字", "姓名"],
}


def _detect_asked_fields(assistant: str) -> list[str]:
    text = assistant or ""
    found: list[str] = []
    for field, keys in FIELD_KEYWORDS.items():
        if any(k in text for k in keys):
            found.append(field)
    return found


def _check_policy_rules(turns: list[TurnRecord]) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    ask_seq: list[list[str]] = []
    counts: dict[str, int] = {}
    for t in turns:
        asked = _detect_asked_fields(t.assistant)
        ask_seq.append(asked)
        for f in asked:
            counts[f] = counts.get(f, 0) + 1

    def add(name: str, passed: bool, expected: Any, actual: Any, note: str = "") -> None:
        checks.append(
            {"name": name, "passed": bool(passed), "expected": expected, "actual": actual, "note": note}
        )
        if not passed:
            failures.append(f"{name}: expected={expected!r}, actual={actual!r}{' (' + note + ')' if note else ''}")

    # 关键字段主动询问上限（联系方式独立策略，不在这里限次数）
    for f in ["sex", "age", "education", "occupation", "location"]:
        add(f"core_ask_limit_{f}", counts.get(f, 0) <= 2, "<=2", counts.get(f, 0))
    add("quasi_core_ask_limit_marital_status", counts.get("marital_status", 0) <= 2, "<=2", counts.get("marital_status", 0))

    # 中等字段最多主动问1次
    for f in ["monthly_income", "partner_requirement"]:
        add(f"medium_ask_limit_{f}", counts.get(f, 0) <= 1, "<=1", counts.get(f, 0))

    # 低优字段永不主动问
    for f in ["height", "weight", "last_name"]:
        add(f"low_priority_never_ask_{f}", counts.get(f, 0) == 0, "0", counts.get(f, 0))

    # 同字段不能连续两轮都问
    repeated = 0
    for i in range(1, len(ask_seq)):
        overlap = set(ask_seq[i - 1]) & set(ask_seq[i])
        if overlap:
            repeated += len(overlap)
    add("no_consecutive_same_field_ask", repeated == 0, 0, repeated)

    # 月薪问法要带降压表达
    income_soft_fail = 0
    soft_markers = ["不方便", "没关系", "可以不说", "方便说", "看你方便"]
    for t in turns:
        asked = _detect_asked_fields(t.assistant)
        if "monthly_income" in asked and not any(m in (t.assistant or "") for m in soft_markers):
            income_soft_fail += 1
    add("income_question_soft_tone", income_soft_fail == 0, 0, income_soft_fail)

    return checks, failures


async def _run_one(
    *,
    idx: int,
    rng: random.Random,
    chat_service: ChatService,
    probe: TimingProbe,
    persona: Persona,
    turns: list[str],
    scenario_id: str,
    category: str,
    tags: list[str],
    verbose: bool,
) -> SessionResult:
    session_id = f"realism_{idx}_{uuid.uuid4().hex[:8]}"
    dialog_base = f"realism_dialog_{uuid.uuid4().hex[:8]}"
    records: list[TurnRecord] = []
    await chat_service.reset_user_conversation(session_id)
    started = time.time()
    last_ai = ""
    expected_sex = _infer_expected_sex_from_turns(turns) or persona.sex

    for i, seed_msg in enumerate(turns, start=1):
        msg = _inject_random_behavior(rng, persona) if i > 1 else None
        if not msg:
            if seed_msg == "__AUTO__":
                msg = rng.choice(
                    [
                        "你好",
                        f"我{persona.sex}的",
                        f"我{persona.age_bucket}",
                        f"在{persona.location}",
                        f"{persona.education}",
                        f"做{persona.occupation}",
                        f"喜欢{persona.preference}",
                        "电话不太方便",
                        "微信可以吗",
                    ]
                )
            else:
                msg = seed_msg
        req = ChatRequest(question=msg, accountId=session_id, dialogId=f"{dialog_base}_{i}", sex=expected_sex)
        probe.begin_turn()
        t0 = time.time()
        resp = await chat_service.process_chat_request(req)
        total_s = time.time() - t0
        perf = probe.end_turn(total_s)

        ai_text = str(resp.get("response", ""))
        last_ai = ai_text
        turn_failures = _check_turn(msg, ai_text)
        rec = TurnRecord(
            index=i,
            user=msg,
            assistant=ai_text,
            latency_s=round(total_s, 3),
            perf=perf,
            collected_info=resp.get("collected_info", {}) or {},
            failures=turn_failures,
        )
        records.append(rec)

        if verbose:
            print(f"[S{idx}][{scenario_id}] T{i} U: {msg}")
            print(f"[S{idx}][{scenario_id}] T{i} A: {ai_text}")
            print(f"[S{idx}][{scenario_id}] T{i} perf={perf}")

        await asyncio.sleep(rng.uniform(0.15, 0.55))

    profile_resp = await chat_service.get_user_profile(session_id)
    final_profile = profile_resp.get("profile", {}) if profile_resp.get("success") else {}
    field_checks, field_failures = _check_profile_fields_with_expected_sex(
        persona,
        final_profile,
        records,
        expected_sex=expected_sex,
    )
    policy_checks, policy_failures = _check_policy_rules(records)

    return SessionResult(
        session_id=session_id,
        scenario_id=scenario_id,
        category=category,
        tags=tags,
        persona=persona,
        turns=records,
        final_profile=final_profile,
        field_checks=field_checks,
        field_failures=field_failures,
        policy_checks=policy_checks,
        policy_failures=policy_failures,
        duration_s=time.time() - started,
    )


def _build_workload(args: argparse.Namespace, rng: random.Random) -> list[dict[str, Any]]:
    if args.cover_scenarios:
        workload = []
        for sc in _load_coverage_scenarios(args):
            dense = []
            for m in sc["messages"]:
                dense.extend(_split_dense_message(m))
            if not dense:
                dense = ["__AUTO__"] * rng.randint(args.min_turns, args.max_turns)
            workload.append(
                {
                    "scenario_id": sc["id"],
                    "category": sc["category"],
                    "tags": sc["tags"],
                    "turns": dense[: max(args.min_turns, min(len(dense), args.max_turns))] or ["__AUTO__"],
                }
            )
        return workload

    workload = []
    for i in range(args.sessions):
        turns = ["__AUTO__"] * rng.randint(args.min_turns, args.max_turns)
        workload.append(
            {
                "scenario_id": f"random_{i+1}",
                "category": "random",
                "tags": ["realism", "random"],
                "turns": turns,
            }
        )
    return workload


def _analyze(results: list[SessionResult], template_threshold: float) -> dict[str, Any]:
    turns = [t for s in results for t in s.turns]
    latencies = [t.latency_s for t in turns]
    total_field_checks = sum(len(s.field_checks) for s in results)
    total_field_failures = sum(len(s.field_failures) for s in results)
    total_policy_checks = sum(len(s.policy_checks) for s in results)
    total_policy_failures = sum(len(s.policy_failures) for s in results)
    phase_values: dict[str, list[float]] = {}
    field_failure_counter: dict[str, int] = {}
    policy_failure_counter: dict[str, int] = {}
    turn_failure_counter: dict[str, int] = {}
    for t in turns:
        for k, v in t.perf.items():
            phase_values.setdefault(k, []).append(float(v))
        for failure in t.failures:
            turn_failure_counter[failure] = turn_failure_counter.get(failure, 0) + 1
    for session in results:
        for check in session.field_checks:
            if not check.get("passed"):
                field_failure_counter[str(check.get("name"))] = field_failure_counter.get(str(check.get("name")), 0) + 1
        for check in session.policy_checks:
            if not check.get("passed"):
                policy_failure_counter[str(check.get("name"))] = policy_failure_counter.get(str(check.get("name")), 0) + 1

    template_count: dict[str, int] = {}
    for t in turns:
        key = _normalize_template(t.assistant)
        if key:
            template_count[key] = template_count.get(key, 0) + 1
    template_top = sorted(template_count.items(), key=lambda x: x[1], reverse=True)[:20]
    total_turns = len(turns) or 1
    template_ratio = (template_top[0][1] / total_turns) if template_top else 0.0

    p95 = _percentile(latencies, 0.95)
    slow_turns = sorted(
        [
            {
                "scenario_id": s.scenario_id,
                "turn": t.index,
                "latency_s": t.latency_s,
                "user": t.user,
                "assistant": t.assistant[:120],
                "perf": t.perf,
            }
            for s in results
            for t in s.turns
            if t.latency_s > max(15.0, p95 * 1.5)
        ],
        key=lambda x: x["latency_s"],
        reverse=True,
    )[:20]

    optimization_hints = []
    avg_total = statistics.mean(latencies) if latencies else 0.0
    for phase in ["ai_call", "rule_check", "profile_load", "profile_save", "extract_collect", "context_load", "response_build", "other"]:
        vals = phase_values.get(phase, [])
        if not vals:
            continue
        phase_avg = statistics.mean(vals)
        ratio = phase_avg / avg_total if avg_total else 0.0
        if ratio >= 0.6:
            if phase == "ai_call":
                optimization_hints.append("LLM 阶段占比过高：优先优化 prompt 长度、FAQ 快速通道和模型路由。")
            elif phase in {"profile_load", "profile_save"}:
                optimization_hints.append("状态读写占比偏高：减少重复读写并合并保存。")
            elif phase == "rule_check":
                optimization_hints.append("规则阶段占比偏高：建议规则短路、热点正则预编译。")
            elif phase == "other":
                optimization_hints.append("其他阶段占比高：需要继续细化打点拆分。")

    if template_ratio > template_threshold:
        optimization_hints.append(
            f"模板化风险偏高：Top1 模板占比 {template_ratio:.1%} > 阈值 {template_threshold:.1%}，建议扩写多样化话术。"
        )

    field_exact_checks = 0
    field_exact_failures = 0
    field_completeness_checks = 0
    field_completeness_failures = 0
    for session in results:
        for check in session.field_checks:
            name = str(check.get("name") or "")
            is_exact_check = name.endswith("_matches_user_stated") or name == "sex_equals_persona"
            if is_exact_check:
                field_exact_checks += 1
                if not check.get("passed"):
                    field_exact_failures += 1
            else:
                field_completeness_checks += 1
                if not check.get("passed"):
                    field_completeness_failures += 1

    total_turn_failures = sum(len(t.failures) for t in turns)
    total_humanlike_checks = total_policy_checks + len(turns)
    total_humanlike_failures = total_policy_failures + total_turn_failures

    return {
        "humanlike_quality": {
            "total_checks": total_humanlike_checks,
            "failed_checks": total_humanlike_failures,
            "pass_rate": round((total_humanlike_checks - total_humanlike_failures) / total_humanlike_checks, 4) if total_humanlike_checks else 1.0,
            "turn_level_failures": total_turn_failures,
            "policy_rule_failures": total_policy_failures,
            "top_turn_failures": [
                {"name": name, "count": count}
                for name, count in sorted(turn_failure_counter.items(), key=lambda x: x[1], reverse=True)[:20]
            ],
            "top_policy_failures": [
                {"name": name, "count": count}
                for name, count in sorted(policy_failure_counter.items(), key=lambda x: x[1], reverse=True)[:20]
            ],
            "template_top1_ratio": round(template_ratio, 4),
            "latency_p95": round(p95, 3),
            "latency_p99": round(_percentile(latencies, 0.99), 3),
        },
        "extraction_accuracy": {
            "total_checks": total_field_checks,
            "failed_checks": total_field_failures,
            "pass_rate": round((total_field_checks - total_field_failures) / total_field_checks, 4) if total_field_checks else 1.0,
            "exact_match_checks": field_exact_checks,
            "exact_match_failures": field_exact_failures,
            "exact_match_pass_rate": round((field_exact_checks - field_exact_failures) / field_exact_checks, 4) if field_exact_checks else 1.0,
            "completeness_checks": field_completeness_checks,
            "completeness_failures": field_completeness_failures,
            "completeness_pass_rate": round((field_completeness_checks - field_completeness_failures) / field_completeness_checks, 4) if field_completeness_checks else 1.0,
            "top_failed_checks": [
                {"name": name, "count": count}
                for name, count in sorted(field_failure_counter.items(), key=lambda x: x[1], reverse=True)[:20]
            ],
        },
        "field_quality": {
            "total_checks": total_field_checks,
            "failed_checks": total_field_failures,
            "pass_rate": round((total_field_checks - total_field_failures) / total_field_checks, 4) if total_field_checks else 1.0,
            "top_failed_checks": [
                {"name": name, "count": count}
                for name, count in sorted(field_failure_counter.items(), key=lambda x: x[1], reverse=True)[:20]
            ],
            "failed_sessions": [
                {
                    "scenario_id": s.scenario_id,
                    "session_id": s.session_id,
                    "failures": s.field_failures[:10],
                }
                for s in results
                if s.field_failures
            ][:20],
        },
        "policy_quality": {
            "total_checks": total_policy_checks,
            "failed_checks": total_policy_failures,
            "pass_rate": round((total_policy_checks - total_policy_failures) / total_policy_checks, 4) if total_policy_checks else 1.0,
            "top_failed_checks": [
                {"name": name, "count": count}
                for name, count in sorted(policy_failure_counter.items(), key=lambda x: x[1], reverse=True)[:20]
            ],
            "failed_sessions": [
                {
                    "scenario_id": s.scenario_id,
                    "session_id": s.session_id,
                    "failures": s.policy_failures[:10],
                }
                for s in results
                if s.policy_failures
            ][:20],
        },
        "latency": {
            "p50": round(_percentile(latencies, 0.50), 3),
            "p90": round(_percentile(latencies, 0.90), 3),
            "p95": round(p95, 3),
            "p99": round(_percentile(latencies, 0.99), 3),
            "max": round(max(latencies) if latencies else 0.0, 3),
            "avg": round(statistics.mean(latencies) if latencies else 0.0, 3),
        },
        "phase_latency_avg": {k: round(statistics.mean(v), 4) for k, v in phase_values.items() if v},
        "slow_turns_top20": slow_turns,
        "template_risk": {
            "top_templates": [{"template": k, "count": c, "ratio": round(c / total_turns, 4)} for k, c in template_top],
            "top1_ratio": round(template_ratio, 4),
            "threshold": template_threshold,
            "at_risk": template_ratio > template_threshold,
        },
        "optimization_hints": optimization_hints,
    }


def _write_reports(report_dir: Path, results: list[SessionResult], analysis: dict[str, Any], token_usage: dict[str, int]) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = report_dir / f"realism_regression_{ts}.json"
    md_path = report_dir / f"realism_regression_{ts}.md"
    latest_json = report_dir / "latest.json"
    latest_md = report_dir / "latest.md"

    total_sessions = len(results)
    total_turns = sum(len(r.turns) for r in results)
    turn_failed_checks = sum(len(t.failures) for r in results for t in r.turns)
    field_failed_checks = sum(len(r.field_failures) for r in results)
    policy_failed_checks = sum(len(r.policy_failures) for r in results)
    failed_checks = turn_failed_checks + field_failed_checks + policy_failed_checks
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "sessions": total_sessions,
            "turns": total_turns,
            "failed_checks": failed_checks,
            "failed_check_breakdown": {
                "turn": turn_failed_checks,
                "field": field_failed_checks,
                "policy": policy_failed_checks,
            },
            "token_usage": token_usage,
            "latency": analysis["latency"],
        },
        "analysis": analysis,
        "results": [r.to_dict() for r in results],
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    json_path.write_text(text, encoding="utf-8")
    latest_json.write_text(text, encoding="utf-8")

    lines = [
        "# 真实用户仿真回归报告",
        "",
        f"- 会话数: {total_sessions}",
        f"- 总轮次: {total_turns}",
        f"- 失败检查数: {failed_checks}",
        f"- 失败分布: turn={turn_failed_checks}, field={field_failed_checks}, policy={policy_failed_checks}",
        f"- 时延 p95: {analysis['latency']['p95']}s",
        f"- 时延 p99: {analysis['latency']['p99']}s",
        f"- 模板化 Top1 占比: {analysis['template_risk']['top1_ratio']:.1%}",
        f"- Token: {token_usage.get('total_tokens', 0)} (调用 {token_usage.get('call_count', 0)} 次)",
        "",
        "## 核心结论",
        "",
        f"- 拟人化收集通过率: {analysis['humanlike_quality']['pass_rate']:.1%}",
        f"- 字段提取综合通过率: {analysis['extraction_accuracy']['pass_rate']:.1%}",
        f"- 字段精确匹配通过率: {analysis['extraction_accuracy']['exact_match_pass_rate']:.1%}",
        f"- 字段完整性通过率: {analysis['extraction_accuracy']['completeness_pass_rate']:.1%}",
        "",
        "## 拟人化收集质量",
        "",
        f"- 总检查数: {analysis['humanlike_quality']['total_checks']}",
        f"- 失败检查数: {analysis['humanlike_quality']['failed_checks']}",
        f"- Turn 级失败: {analysis['humanlike_quality']['turn_level_failures']}",
        f"- 策略级失败: {analysis['humanlike_quality']['policy_rule_failures']}",
        f"- 模板化 Top1 占比: {analysis['humanlike_quality']['template_top1_ratio']:.1%}",
        f"- 时延 p95: {analysis['humanlike_quality']['latency_p95']}s",
        f"- 时延 p99: {analysis['humanlike_quality']['latency_p99']}s",
    ]
    for item in analysis["humanlike_quality"].get("top_turn_failures", [])[:10]:
        lines.append(f"- 高频 turn 失败 {item['name']}: {item['count']} 次")
    for item in analysis["humanlike_quality"].get("top_policy_failures", [])[:10]:
        lines.append(f"- 高频策略失败 {item['name']}: {item['count']} 次")
    lines += [
        "",
        "## 字段提取准确性",
        "",
        f"- 总检查数: {analysis['extraction_accuracy']['total_checks']}",
        f"- 失败检查数: {analysis['extraction_accuracy']['failed_checks']}",
        f"- 综合通过率: {analysis['extraction_accuracy']['pass_rate']:.1%}",
        f"- 精确匹配检查数: {analysis['extraction_accuracy']['exact_match_checks']}",
        f"- 精确匹配失败数: {analysis['extraction_accuracy']['exact_match_failures']}",
        f"- 精确匹配通过率: {analysis['extraction_accuracy']['exact_match_pass_rate']:.1%}",
        f"- 完整性检查数: {analysis['extraction_accuracy']['completeness_checks']}",
        f"- 完整性失败数: {analysis['extraction_accuracy']['completeness_failures']}",
        f"- 完整性通过率: {analysis['extraction_accuracy']['completeness_pass_rate']:.1%}",
    ]
    for item in analysis["extraction_accuracy"].get("top_failed_checks", [])[:10]:
        lines.append(f"- 高频字段失败 {item['name']}: {item['count']} 次")
    lines += [
        "",
        "## 时延异常 Top20",
        "",
    ]
    for item in analysis["slow_turns_top20"]:
        lines.append(
            f"- {item['scenario_id']}#T{item['turn']}: {item['latency_s']}s, user=`{item['user']}`"
        )
    lines += ["", "## 优化建议", ""]
    hints = analysis.get("optimization_hints") or ["当前未发现显著单阶段瓶颈。"]
    for hint in hints:
        lines.append(f"- {hint}")
    lines += ["", "## 模板化风险 Top10", ""]
    for item in (analysis["template_risk"]["top_templates"] or [])[:10]:
        lines.append(f"- {item['count']} 次 ({item['ratio']:.1%}): `{item['template']}`")
    lines += ["", "## 字段收集质量", ""]
    fq = analysis.get("field_quality", {})
    lines.append(f"- 总检查数: {fq.get('total_checks', 0)}")
    lines.append(f"- 失败检查数: {fq.get('failed_checks', 0)}")
    lines.append(f"- 通过率: {fq.get('pass_rate', 1.0):.1%}")
    for failed in fq.get("failed_sessions", [])[:10]:
        lines.append(f"- {failed['scenario_id']} ({failed['session_id']}): {failed['failures'][:3]}")
    for item in fq.get("top_failed_checks", [])[:10]:
        lines.append(f"- 高频失败 {item['name']}: {item['count']} 次")
    lines += ["", "## 对话策略规则质量", ""]
    pq = analysis.get("policy_quality", {})
    lines.append(f"- 总检查数: {pq.get('total_checks', 0)}")
    lines.append(f"- 失败检查数: {pq.get('failed_checks', 0)}")
    lines.append(f"- 通过率: {pq.get('pass_rate', 1.0):.1%}")
    for failed in pq.get("failed_sessions", [])[:10]:
        lines.append(f"- {failed['scenario_id']} ({failed['session_id']}): {failed['failures'][:3]}")
    for item in pq.get("top_failed_checks", [])[:10]:
        lines.append(f"- 高频失败 {item['name']}: {item['count']} 次")
    lines.append("")
    md_text = "\n".join(lines)
    md_path.write_text(md_text, encoding="utf-8")
    latest_md.write_text(md_text, encoding="utf-8")
    return json_path, md_path


async def main() -> int:
    args = parse_args()
    rng = random.Random(args.seed)
    workload = _build_workload(args, rng)
    if not workload:
        print("没有可执行的工作负载。")
        return 1

    ai_service = AIService()
    user_service = UserService()
    chat_service = ChatService(ai_service, user_service)
    probe = TimingProbe(chat_service)
    await AIService.reset_token_usage()

    results: list[SessionResult] = []
    for i, item in enumerate(workload, start=1):
        persona = _build_persona(rng)
        print(f"[{i}/{len(workload)}] RUN {item['scenario_id']} ({item['category']})")
        result = await _run_one(
            idx=i,
            rng=rng,
            chat_service=chat_service,
            probe=probe,
            persona=persona,
            turns=item["turns"],
            scenario_id=item["scenario_id"],
            category=item["category"],
            tags=item["tags"],
            verbose=args.verbose,
        )
        print(f"[{i}/{len(workload)}] DONE turns={len(result.turns)} duration={result.duration_s:.2f}s")
        results.append(result)

    probe.close()
    token_usage = await AIService.get_token_usage()
    analysis = _analyze(results, args.template_risk_threshold)
    json_path, md_path = _write_reports(Path(args.report_dir), results, analysis, token_usage)
    print(f"拟人化收集通过率: {analysis['humanlike_quality']['pass_rate']:.1%}")
    print(f"字段提取综合通过率: {analysis['extraction_accuracy']['pass_rate']:.1%}")
    print(f"字段精确匹配通过率: {analysis['extraction_accuracy']['exact_match_pass_rate']:.1%}")
    print(f"字段完整性通过率: {analysis['extraction_accuracy']['completeness_pass_rate']:.1%}")
    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

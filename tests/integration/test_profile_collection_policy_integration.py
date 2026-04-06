#!/usr/bin/env python3
"""
资料收集策略集成测试

测试目标：
1. 验证新策略不会过早主动追问低优字段
2. 验证用户提问后，AI 会先回答问题，再回到主线
3. 验证资料达到阈值后，AI 才进入联系方式逻辑

说明：
- 默认使用离线 FakeAI，便于本地稳定回归
- 使用真实 AI 时需显式开启
- 只校验行为和状态，不校验精确文案
"""

import argparse
import os
import sys
import uuid
import asyncio
import re

import pytest
from dotenv import load_dotenv


project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(project_root, ".env"), override=False)

if project_root not in sys.path:
    sys.path.insert(0, project_root)
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.models.requests import ChatRequest
from src.services.ai_service import AIService
from src.services.core.chat_service import ChatService
from src.services.data.user_service import UserService

USE_REAL_AI = os.getenv("PROFILE_POLICY_USE_REAL_AI") == "1"


class FakeAIService:
    """离线资料策略测试专用 AI。"""

    EXTRACT_FIELDS = [
        "称呼", "性别", "所在地", "年龄", "身高", "体重", "学历", "职业",
        "月收入", "婚况", "联系方式", "微信", "择偶要求"
    ]

    def _get_user_message(self, prompt: str) -> str:
        match = re.search(r"【用户消息】(.+?)(?:\n\n|\n【回复后必须附加】)", prompt, re.DOTALL)
        return match.group(1).strip() if match else ""

    def _build_extract_block(self, user_message: str) -> str:
        fields = {field: "null" for field in self.EXTRACT_FIELDS}

        if re.search(r"(我男的|我是男|本人男|男的)", user_message):
            fields["性别"] = "男"
        if re.search(r"(我女的|我是女|本人女|女的)", user_message):
            fields["性别"] = "女"

        age_match = re.search(r"(?:今年)?(\d{1,2})岁?|今年(\d{1,2})", user_message)
        if age_match:
            fields["年龄"] = age_match.group(1) or age_match.group(2)

        height_match = re.search(r"身高\s*(\d{3})|(\d{3})cm", user_message, re.IGNORECASE)
        if height_match:
            fields["身高"] = next(group for group in height_match.groups() if group)

        for location in ["深圳", "杭州", "广州", "上海", "成都", "苏州"]:
            if location in user_message:
                fields["所在地"] = location
                break

        for education in ["博士", "硕士", "本科", "大专"]:
            if education in user_message:
                fields["学历"] = education
                break

        for occupation in ["产品", "运营", "程序员", "研发", "设计", "老师"]:
            if occupation in user_message:
                fields["职业"] = occupation
                break

        income_match = re.search(r"(\d+(?:\.\d+)?)万", user_message)
        if income_match:
            fields["月收入"] = f"{income_match.group(1)}万"

        if "分居" in user_message:
            fields["婚况"] = "离异（手续办理中）"
        elif any(token in user_message for token in ["离异", "离婚"]):
            fields["婚况"] = "离异"
        elif any(token in user_message for token in ["单身", "未婚"]):
            fields["婚况"] = "单身"

        phone_match = re.search(r"(?:电话(?:是)?|手机号(?:是)?|联系方式(?:是)?)\s*([0-9]{8,11})", user_message)
        if phone_match:
            fields["联系方式"] = phone_match.group(1)

        wechat_match = re.search(r"(?:微信(?:号)?(?:是)?|wx(?:是)?)\s*([A-Za-z0-9_]+)", user_message, re.IGNORECASE)
        if wechat_match:
            fields["微信"] = wechat_match.group(1)

        req_bits = []
        for token in ["温柔点", "温柔", "成熟稳重", "成熟稳重点", "同城", "性格稳定", "情绪稳定"]:
            if token in user_message and token not in req_bits:
                req_bits.append(token)
        if req_bits:
            fields["择偶要求"] = ",".join(req_bits)

        lines = [f"{field}:{value}" for field, value in fields.items()]
        return "<extract>\n" + "\n".join(lines) + "\n</extract>"

    async def generate_response(
        self,
        message: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        timeout: float | None = None,
        model_name: str | None = None,
    ) -> str:
        user_message = self._get_user_message(message)

        if any(token in user_message for token in ["收费", "免费", "服务费"]):
            return f"我们会提前说明服务方式和收费情况，你也可以先免费了解流程，不会强制付费。\n{self._build_extract_block(user_message)}"

        if any(token in user_message for token in ["隐私", "泄露", "靠谱吗", "用途", "问这些干嘛"]):
            return f"这些信息主要是为了帮你匹配得更准确，隐私我们会注意，不会随便外泄。\n{self._build_extract_block(user_message)}"

        if "为什么要留联系方式" in user_message:
            return f"联系方式只是为了后续有合适人选时方便联系你，我们会注意隐私，也不会随便打扰。\n{self._build_extract_block(user_message)}"

        if "分居" in user_message:
            return f"我先确认下哦，你现在还在分居阶段，等手续办妥后再来找我会更合适一些。\n{self._build_extract_block(user_message)}"

        if any(token in user_message for token in ["已经办妥", "现在是单身"]):
            return f"那就明白啦，现在是单身状态就可以继续了解啦。你喜欢什么样的另一半，或者我继续帮你看看联系方式也行。\n{self._build_extract_block(user_message)}"

        if any(token in user_message for token in ["微信是", "微信号是", "wx是"]):
            return f"好的呀，微信我先记下啦。后续有合适的人选会第一时间联系你，如果方便的话电话也可以留一个。\n{self._build_extract_block(user_message)}"

        if any(token in user_message for token in ["电话是", "手机号是", "联系方式是"]):
            return f"好的，电话我记下了。后续有合适的人选方便及时联系你，如果你愿意的话微信也可以留一个。\n{self._build_extract_block(user_message)}"

        if any(token in user_message for token in ["不留电话", "电话还是不留"]):
            return f"好的，电话这边我明白了。你愿意留微信也可以，或者我先继续按你的资料帮你留意。\n{self._build_extract_block(user_message)}"

        if any(token in user_message for token in ["不留微信", "微信还是不留"]):
            return f"明白，微信这边我尊重你的想法。那我先把其他信息记下，有合适的也会按你愿意的方式联系。\n{self._build_extract_block(user_message)}"

        if user_message in {"嗯", "好的"}:
            if "当前任务：结束对话收尾" in message:
                return f"好的，那先这样，有需要随时再找我就好。\n{self._build_extract_block(user_message)}"
            return f"好的，信息我先记下了。\n{self._build_extract_block(user_message)}"

        if user_message in {"知道了", "没有了", "没别的要求了", "没有其他要求了", "没有别的问题了"}:
            return f"我继续按你现在的资料往下帮你推进，方便的话留个电话、微信这样的联系方式会更高效。\n{self._build_extract_block(user_message)}"

        if any(token in user_message for token in ["希望找", "想找", "另一半", "要求", "同城", "成熟稳重", "性格稳定", "情绪稳定"]):
            return f"好的，这些要求我记下了。你这边资料已经比较完整了，方便的话留个电话或者微信，后续有合适的人选我能第一时间联系你。\n{self._build_extract_block(user_message)}"

        if any(token in user_message for token in ["我男的", "我女的", "本科", "在深圳", "在杭州", "在广州", "在上海", "在成都", "在苏州"]):
            if "离异" in user_message:
                return f"我顺带确认下哦，现在手续都办妥了吗？确认好这个我再继续帮你往下匹配。\n{self._build_extract_block(user_message)}"
            if any(token in user_message for token in ["单身", "想找", "希望找"]):
                return f"好的，资料我先记下了。你现在是单身的话我这边就能认真帮你了解，方便的话留个电话或者微信，后续更好联系。\n{self._build_extract_block(user_message)}"
            if any(token in user_message for token in ["产品", "运营", "程序员", "研发", "设计", "老师"]):
                return f"好的，资料我先记下了。我顺带确认下你的感情状态，这样我好继续往下帮你筛合适的人。\n{self._build_extract_block(user_message)}"
            return f"好的，资料我先记下了。你现在感情状态是单身吗？我好继续认真帮你了解。\n{self._build_extract_block(user_message)}"

        return f"好的，信息我先记下了。\n{self._build_extract_block(user_message)}"


class TestProfileCollectionPolicyIntegration:
    """新资料收集策略的集成行为测试"""

    @pytest.fixture(autouse=True)
    def setup_services(self):
        if USE_REAL_AI:
            if not os.getenv("ARK_API_KEY"):
                pytest.skip("requires real ARK_API_KEY when PROFILE_POLICY_USE_REAL_AI=1")
            self.ai_service = AIService()
        else:
            self.ai_service = FakeAIService()
        self.user_service = UserService()
        self.chat_service = ChatService(self.ai_service, self.user_service)

    async def _reset_user(self, account_id: str):
        await self.chat_service.reset_user_conversation(account_id)

    async def _send_message(self, account_id: str, message: str, sex: str = "女", retries: int = 2):
        response = ""
        profile = None

        for attempt in range(retries + 1):
            request = ChatRequest(
                question=message,
                accountId=account_id,
                dialogId=f"policy_{uuid.uuid4().hex[:8]}",
                sex=sex,
            )
            result = await self.chat_service.process_chat_request(request)
            response = result.get("response", "")
            profile = await self.user_service.get_user_profile(account_id)

            # 真实 AI 场景下偶发超时会返回空回复，允许自动重试
            if response:
                break

        return response, profile

    def _run(self, coro):
        return asyncio.run(coro)

    @staticmethod
    def _blank_extract_block() -> str:
        fields = [
            "称呼", "性别", "所在地", "年龄", "身高", "体重", "学历", "职业",
            "月收入", "婚况", "联系方式", "微信", "择偶要求"
        ]
        return "<extract>\n" + "\n".join(f"{field}:null" for field in fields) + "\n</extract>"

    async def _seed_profile_fields(self, account_id: str, **field_values):
        profile = await self.user_service.get_user_profile(account_id)
        for field, value in field_values.items():
            setattr(profile, field, value)
            if field in profile.collection_progress:
                profile.collection_progress[field] = bool(value)
        await self.user_service.save_user_profile(account_id, profile)
        return profile

    def test_real_ai_avoids_low_priority_fields_before_core_ready(self):
        """资料未成熟时，AI 不应主动追问低优字段或过早问联系方式"""
        account_id = f"policy_low_priority_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))

        response, profile = self._run(
            self._send_message(
                account_id,
                "我在深圳做产品，今年28，本科。",
                sex="女",
            )
        )

        assert profile is not None
        assert profile.age == 28
        assert profile.location == "深圳"
        assert profile.education == "本科"
        assert profile.occupation is not None

        forbidden_keywords = ["身高", "体重", "怎么称呼", "叫什么", "名字"]
        for keyword in forbidden_keywords:
            assert keyword not in response, f"AI 过早触发了不该问的字段: {keyword}, response={response}"

        assert any(keyword in response for keyword in ["单身", "感情状态", "认真了解", "婚", "电话", "微信", "联系方式"]), response

    def test_real_ai_answers_question_then_returns_to_mainline(self):
        """用户有疑问时先回答疑问，疑问解除后回到主线字段"""
        account_id = f"policy_question_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))

        self._run(
            self._send_message(
                account_id,
                "我女的，29岁，在杭州做运营，本科。",
                sex="女",
            )
        )

        response_1, _ = self._run(self._send_message(account_id, "你们收费吗", sex="女"))
        assert any(keyword in response_1 for keyword in ["免费", "服务费", "收费", "提前说明"]), response_1

        response_2, _ = self._run(self._send_message(account_id, "没有了", sex="女"))
        assert any(
            keyword in response_2
            for keyword in ["单身", "感情状态", "认真了解", "婚", "另一半", "在意", "要求", "收入", "月收入"]
        ), response_2

        forbidden_keywords = ["身高", "体重", "怎么称呼", "名字"]
        for keyword in forbidden_keywords:
            assert keyword not in response_2, f"回到主线后不应追问低优字段: {keyword}, response={response_2}"

    def test_real_ai_enters_contact_only_after_profile_ready(self):
        """资料达到阈值后，AI 应进入联系方式逻辑"""
        account_id = f"policy_contact_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))

        profile = self._run(
            self._seed_profile_fields(
                account_id,
                sex="男",
                age=30,
                location="深圳",
                education="本科",
                occupation="程序员",
                marital_status="单身",
                partner_requirement="温柔点",
                partner_gender_preference="女",
            )
        )
        profile.field_ask_count["monthly_income"] = 1
        self._run(self.user_service.save_user_profile(account_id, profile))

        response, _ = self._run(self._send_message(account_id, "没有其他要求了", sex="男"))

        assert any(keyword in response for keyword in ["电话", "微信", "联系方式"]), response
        assert "身高" not in response
        assert "体重" not in response

    def test_real_ai_full_flow_returns_to_mainline_and_then_asks_contact(self):
        """真实 AI 完整流程：先收集资料，回答疑问，再回主线继续补齐覆盖，成熟后才进入联系方式"""
        account_id = f"policy_full_flow_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))

        response_1, profile_1 = self._run(
            self._send_message(
                account_id,
                "我女的，27岁，在深圳做设计，本科。",
                sex="女",
            )
        )
        assert profile_1 is not None
        assert profile_1.age == 27
        assert profile_1.location == "深圳"
        assert profile_1.education == "本科"
        assert any(
            keyword in response_1
            for keyword in ["单身", "感情状态", "认真了解", "婚", "多大", "年龄", "学历", "工作", "职业", "城市"]
        ), response_1

        response_2, _ = self._run(self._send_message(account_id, "你们靠谱吗，会不会泄露隐私", sex="女"))
        assert any(keyword in response_2 for keyword in ["隐私", "不会", "外泄", "正规", "匹配", "安全", "靠谱"]), response_2

        response_3, profile_3 = self._run(
            self._send_message(
                account_id,
                "单身，想找成熟稳重点的，最好同城。",
                sex="女",
            )
        )
        assert profile_3 is not None
        assert profile_3.marital_status is not None
        assert profile_3.partner_requirement is not None
        assert any(keyword in response_3 for keyword in ["收入", "月收入", "电话", "微信", "联系方式"]), response_3
        assert "身高" not in response_3
        assert "体重" not in response_3

    def test_real_ai_passively_collects_low_priority_without_switching_mainline(self):
        """用户主动给出低优字段时应记录，但 AI 不应因此转成追问低优字段"""
        account_id = f"policy_passive_low_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))

        response, profile = self._run(
            self._send_message(
                account_id,
                "我女的，26岁，在广州做老师，身高168，本科。",
                sex="女",
            )
        )

        assert profile is not None
        assert profile.sex == "女"
        assert profile.age == 26
        assert profile.location == "广州"
        assert profile.education == "本科"
        assert profile.height == "168cm"

        forbidden_keywords = ["体重多少", "体重呢", "怎么称呼", "叫什么"]
        for keyword in forbidden_keywords:
            assert keyword not in response, f"AI 不应因被动拿到低优字段后转去追问低优字段: {keyword}, response={response}"

        assert any(keyword in response for keyword in ["单身", "感情状态", "认真了解", "婚", "职业", "做什么工作"]), response

    def test_real_ai_explains_purpose_and_privacy_before_returning_to_mainline(self):
        """用户质疑用途和隐私时，AI 应先解释，再回到主线"""
        account_id = f"policy_defensive_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))

        self._run(
            self._send_message(
                account_id,
                "我男的，31岁，在杭州做运营，本科。",
                sex="男",
            )
        )

        response_1, _ = self._run(self._send_message(account_id, "你们问这些干嘛，会不会泄露隐私", sex="男"))
        assert any(keyword in response_1 for keyword in ["隐私", "不会", "外泄", "匹配", "更准确", "用途"]), response_1

        response_2, _ = self._run(self._send_message(account_id, "没有别的问题了", sex="男"))
        assert any(
            keyword in response_2
            for keyword in ["单身", "感情状态", "认真了解", "婚", "另一半", "在意", "要求", "收入", "月收入"]
        ), response_2
        for keyword in ["身高", "体重", "怎么称呼", "叫什么"]:
            assert keyword not in response_2, f"答疑后回主线不应跳去低优字段: {keyword}, response={response_2}"

    def test_real_ai_deflective_reply_does_not_switch_to_low_priority(self):
        """用户只回简短确认词时，AI 不应转去追问低优字段"""
        account_id = f"policy_deflective_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))

        self._run(
            self._send_message(
                account_id,
                "我女的，28岁，在上海。",
                sex="女",
            )
        )

        response, _ = self._run(self._send_message(account_id, "嗯", sex="女"))

        for keyword in ["身高", "体重", "怎么称呼", "叫什么", "名字"]:
            assert keyword not in response, f"用户敷衍时不应跳去问低优字段: {keyword}, response={response}"

        assert any(
            keyword in response
            for keyword in [
                "学历", "工作", "职业", "感情状态", "单身", "城市", "在哪",
                "看不懂", "没太理解", "没太看明白", "换个方式说",
                "想说什么", "消息有点奇怪", "没太明白"
            ]
        ), response

    def test_real_ai_separated_status_ends_conversation_politely(self):
        """用户处于分居中时，应礼貌结束，而不是继续资料收集"""
        account_id = f"policy_separated_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))

        response_1, profile_1 = self._run(
            self._send_message(
                account_id,
                "我女的，32岁，在上海工作，离异，现在还在分居中。",
                sex="女",
            )
        )

        assert profile_1 is not None
        assert profile_1.marital_status is not None
        assert any(keyword in response_1 for keyword in ["分居", "手续", "办妥", "暂时", "不符合", "等"]), response_1
        for keyword in ["身高", "体重", "联系方式", "微信", "电话", "择偶要求"]:
            assert keyword not in response_1, f"分居状态下不应继续推进收集: {keyword}, response={response_1}"

        response_2, _ = self._run(self._send_message(account_id, "好的", sex="女"))
        assert len(response_2) <= 30 or any(keyword in response_2 for keyword in ["好的", "嗯嗯", "有需要", "随时找我"]), response_2
        for keyword in ["电话", "微信", "学历", "职业", "身高", "体重", "择偶要求"]:
            assert keyword not in response_2, f"结束后不应重新拉回收集主线: {keyword}, response={response_2}"

    def test_real_ai_ends_politely_after_both_contacts_rejected(self):
        """资料成熟后，用户连续拒绝电话和微信，应礼貌收尾而不是继续追问"""
        account_id = f"policy_both_rejected_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))
        profile = self._run(
            self._seed_profile_fields(
                account_id,
                sex="男",
                age=30,
                location="深圳",
                education="本科",
                occupation="程序员",
                marital_status="单身",
                partner_requirement="聊得来就行",
            )
        )
        profile.field_ask_count["monthly_income"] = 1
        self._run(self.user_service.save_user_profile(account_id, profile))
        self._run(self.chat_service.dialogue_manager.update_recent_responses(account_id, "如果你愿意的话，留个常用电话就行，后面联系也方便。"))

        response_1, profile_1 = self._run(self._send_message(account_id, "不留电话", sex="男"))
        assert profile_1 is not None
        assert any(keyword in response_1 for keyword in ["电话", "微信", "联系", "方便"]), response_1

        if not profile_1.rejected_phone:
            response_1b, profile_1b = self._run(self._send_message(account_id, "还是不留电话", sex="男"))
            assert profile_1b.rejected_phone is True
            assert any(keyword in response_1b for keyword in ["微信", "其他方式", "联系方式", "留个微信"]), response_1b
            profile_1 = profile_1b

        response_2, profile_2 = self._run(self._send_message(account_id, "不留微信", sex="男"))
        assert profile_2 is not None
        assert any(keyword in response_2 for keyword in ["微信", "联系", "方便", "留"]), response_2

        if not profile_2.rejected_wechat:
            response_2b, profile_2b = self._run(self._send_message(account_id, "还是不留微信", sex="男"))
            response_2 = response_2b
            profile_2 = profile_2b

        assert profile_2 is not None
        assert profile_2.rejected_phone is True
        assert profile_2.rejected_wechat is True
        response_3, _ = self._run(self._send_message(account_id, "嗯", sex="男"))
        assert any(keyword in response_3 for keyword in ["先这样", "有需要", "随时找我", "祝", "好消息", "好的", "聊到这儿"]), response_3
        for keyword in ["微信号发", "身高", "体重", "学历", "职业", "电话", "微信"]:
            assert keyword not in response_3, f"双拒联系方式后不应继续追问: {keyword}, response={response_3}"

    def test_real_ai_accepts_wechat_only_and_does_not_get_stuck(self):
        """用户只愿意留微信、不愿留电话时，应记录微信并平滑处理电话拒绝"""
        account_id = f"policy_wechat_only_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))

        self._run(
            self._send_message(
                account_id,
                "我女的，27岁，在杭州做运营，本科，单身。",
                sex="女",
            )
        )
        self._run(self._send_message(account_id, "希望对方成熟稳重一点", sex="女"))

        response_1, profile_1 = self._run(self._send_message(account_id, "微信是abc12345", sex="女"))
        assert profile_1 is not None
        assert profile_1.wechat_collected is True
        assert profile_1.wechat is not None
        assert any(keyword in response_1 for keyword in ["电话", "手机号", "联系方式", "好消息", "联系你"]), response_1

        response_2, profile_2 = self._run(self._send_message(account_id, "不留电话", sex="女"))
        assert profile_2 is not None
        assert profile_2.wechat_collected is True
        assert any(keyword in response_2 for keyword in ["电话", "联系", "方便", "微信", "好消息"]), response_2

        if not profile_2.rejected_phone:
            response_3, profile_3 = self._run(self._send_message(account_id, "还是不留电话", sex="女"))
            response_2 = response_3
            profile_2 = profile_3

        assert profile_2.rejected_phone is True
        for keyword in ["方便再留个电话", "手机号发我", "再发个电话", "电话给我", "身高", "体重", "怎么称呼", "叫什么"]:
            assert keyword not in response_2, f"只留微信后不应偏到低优字段: {keyword}, response={response_2}"
        assert any(
            keyword in response_2
            for keyword in ["微信", "联系你", "好消息", "月收入", "择偶", "要求", "学历", "工作", "职业", "好的", "明白"]
        ), response_2

    def test_real_ai_divorce_confirmed_returns_to_mainline(self):
        """用户离异但手续已办妥时，AI 应确认后回到主线，而不是结束对话"""
        account_id = f"policy_divorce_confirmed_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))

        response_1, profile_1 = self._run(
            self._send_message(
                account_id,
                "我女的，33岁，在成都工作，离异。",
                sex="女",
            )
        )

        assert profile_1 is not None
        assert profile_1.marital_status is not None
        assert any(keyword in response_1 for keyword in ["办妥", "单身状态", "手续", "确认"]), response_1
        for keyword in ["身高", "体重", "联系方式"]:
            assert keyword not in response_1, f"确认离异手续时不应切别的字段: {keyword}, response={response_1}"

        response_2, profile_2 = self._run(self._send_message(account_id, "已经办妥了，现在是单身", sex="女"))
        assert profile_2 is not None
        assert any(keyword in response_2 for keyword in ["喜欢什么样", "另一半", "要求", "学历", "工作", "职业", "联系方式", "电话", "微信"]), response_2
        for keyword in ["分居", "不符合", "再来找我"]:
            assert keyword not in response_2, f"手续已办妥后不应结束对话: {keyword}, response={response_2}"

    def test_real_ai_contact_purpose_question_stays_on_contact_mainline(self):
        """进入联系方式阶段后，用户质疑用途时，AI 应先解释，再继续联系方式主线"""
        account_id = f"policy_contact_question_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))

        self._run(
            self._send_message(
                account_id,
                "我男的，29岁，在广州做产品，本科，单身。",
                sex="男",
            )
        )
        self._run(self._send_message(account_id, "希望找情绪稳定一点的", sex="男"))

        response_1, _ = self._run(self._send_message(account_id, "为什么要留联系方式", sex="男"))
        assert any(keyword in response_1 for keyword in ["联系", "匹配", "方便", "有合适", "不会", "打扰"]), response_1

        response_2, _ = self._run(self._send_message(account_id, "知道了", sex="男"))
        assert any(keyword in response_2 for keyword in ["电话", "微信", "联系方式"]), response_2
        for keyword in ["身高", "体重", "怎么称呼", "叫什么", "月收入", "择偶要求"]:
            assert keyword not in response_2, f"联系方式答疑后应回到联系方式主线: {keyword}, response={response_2}"

    def test_real_ai_high_information_reply_does_not_repeat_known_fields(self):
        """用户一条消息给出多个字段时，AI 应顺滑推进，不回头重复盘问已知字段"""
        account_id = f"policy_high_info_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))

        response_1, profile_1 = self._run(
            self._send_message(
                account_id,
                "我男的，31岁，在苏州做研发，本科，单身，想找同城性格稳定一点的。",
                sex="男",
            )
        )

        assert profile_1 is not None
        assert profile_1.sex == "男"
        assert profile_1.age == 31
        assert profile_1.location == "苏州"
        assert profile_1.education == "本科"
        assert profile_1.marital_status is not None
        assert profile_1.partner_requirement is not None

        repeated_keywords = ["今年多大", "多大了", "在哪个城市", "在哪工作", "什么学历", "现在是单身吗"]
        for keyword in repeated_keywords:
            assert keyword not in response_1, f"高信息量输入后不应回头重复问已知字段: {keyword}, response={response_1}"

        assert any(
            keyword in response_1
            for keyword in [
                "电话", "微信", "联系方式", "工作", "做什么", "月薪", "收入", "择偶", "要求",
                "记下", "第一时间", "同城", "性格稳定", "合适的"
            ]
        ), response_1

    def test_medium_field_active_once_then_never_reasks_even_if_model_repeats(self, monkeypatch):
        """择偶要求一旦真实问过一次，后续即使模型继续问，也要被流程拦掉。"""
        account_id = f"policy_medium_once_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))
        self._run(
            self._seed_profile_fields(
                account_id,
                sex="男",
                age=30,
                location="深圳",
                education="本科",
                occupation="程序员",
            )
        )
        profile = self._run(self.user_service.get_user_profile(account_id))
        profile.field_ask_count["marital_status"] = 1
        profile.field_ask_count["monthly_income"] = 1
        self._run(self.user_service.save_user_profile(account_id, profile))

        responses = iter(
            [
                f"你这边对另一半有什么比较在意的点吗？\n{self._blank_extract_block()}",
                f"你这边对另一半有什么比较在意的点吗？\n{self._blank_extract_block()}",
            ]
        )

        async def _scripted_call_ai(_prompt: str, _account_id: str, _user_message: str = "") -> str:
            return next(responses)

        monkeypatch.setattr(self.chat_service, "_call_ai", _scripted_call_ai)

        response_1, profile_1 = self._run(self._send_message(account_id, "我这边先继续往下聊吧", sex="男"))
        assert "另一半" in response_1
        assert profile_1.is_active_ask_closed("partner_requirement") is True
        assert profile_1.get_ask_count("partner_requirement") == 1

        response_2, profile_2 = self._run(self._send_message(account_id, "这个我先不展开，你继续", sex="男"))
        assert "另一半" not in response_2
        assert "在意的点" not in response_2
        assert profile_2.get_ask_count("partner_requirement") == 1

    def test_resume_profile_collection_turn_blocks_monthly_income_reask(self, monkeypatch):
        """恢复主线轮次里，即使模型想问月薪，也不能主动出现。"""
        account_id = f"policy_resume_medium_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))
        self._run(
            self._seed_profile_fields(
                account_id,
                sex="女",
                age=29,
                location="杭州",
                education="本科",
            )
        )

        async def _scripted_call_ai(_prompt: str, _account_id: str, _user_message: str = "") -> str:
            return f"如果你方便的话，我再轻问一句，你月收入大概在哪个区间？\n{self._blank_extract_block()}"

        monkeypatch.setattr(self.chat_service, "_call_ai", _scripted_call_ai)

        response, _ = self._run(self._send_message(account_id, "你不问其他了？", sex="女"))

        assert "月收入" not in response
        assert "收入大概" not in response
        assert "月薪" not in response

    def test_contact_flow_strips_medium_field_even_if_model_inserts_it(self, monkeypatch):
        """联系方式阶段即使模型夹带择偶要求，也必须被守卫删除。"""
        account_id = f"policy_contact_medium_isolation_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))
        self._run(
            self._seed_profile_fields(
                account_id,
                sex="男",
                age=31,
                location="深圳",
                education="本科",
                occupation="程序员",
                marital_status="单身",
                partner_requirement="聊得来",
            )
        )
        profile = self._run(self.user_service.get_user_profile(account_id))
        profile.field_ask_count["monthly_income"] = 1
        self._run(self.user_service.save_user_profile(account_id, profile))

        async def _scripted_call_ai(_prompt: str, _account_id: str, _user_message: str = "") -> str:
            return (
                "要是你愿意，留个电话也行。"
                "你这边对另一半有什么比较在意的点吗？\n"
                f"{self._blank_extract_block()}"
            )

        monkeypatch.setattr(self.chat_service, "_call_ai", _scripted_call_ai)

        response, profile = self._run(self._send_message(account_id, "没有其他要求了", sex="男"))

        assert any(keyword in response for keyword in ["电话", "联系方式"])
        assert "另一半" not in response
        assert "在意的点" not in response
        assert profile.get_ask_count("partner_requirement") == 0

    def test_faq_reentry_turn_blocks_medium_fields_but_keeps_contact_mainline(self, monkeypatch):
        """FAQ 回答后的承接轮次不能跳去中等字段，且在资料已成熟时允许继续联系方式主线。"""
        account_id = f"policy_faq_reentry_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))
        self._run(
            self._seed_profile_fields(
                account_id,
                sex="男",
                age=31,
                location="深圳",
                education="本科",
                occupation="程序员",
                marital_status="单身",
                partner_requirement="聊得来",
            )
        )
        profile = self._run(self.user_service.get_user_profile(account_id))
        profile.field_ask_count["monthly_income"] = 1
        self._run(self.user_service.save_user_profile(account_id, profile))
        self._run(
            self.chat_service.dialogue_manager.update_recent_responses(
                account_id,
                "联系方式只是为了后续有合适的人选时方便联系你，我们也会注意隐私，不会随便打扰。",
            )
        )

        async def _scripted_call_ai(_prompt: str, _account_id: str, _user_message: str = "") -> str:
            return (
                "如果你方便的话，我再轻问一句，你月收入大概在哪个区间？"
                "要是你愿意，留个电话也行。\n"
                f"{self._blank_extract_block()}"
            )

        monkeypatch.setattr(self.chat_service, "_call_ai", _scripted_call_ai)

        response, _ = self._run(self._send_message(account_id, "知道了", sex="男"))

        assert any(keyword in response for keyword in ["电话", "联系方式"])
        assert "月收入" not in response
        assert "收入大概" not in response
        assert "另一半" not in response

    def test_passive_only_partner_requirement_still_extracts_from_user_message(self):
        """择偶要求进入 PASSIVE_ONLY 后，用户主动表达时仍然要能入档。"""
        account_id = f"policy_passive_partner_extract_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))

        async def _seed_passive_only_partner_requirement():
            profile = await self._seed_profile_fields(
                account_id,
                sex="男",
                age=31,
                location="深圳",
                education="本科",
            )
            profile.close_active_ask("partner_requirement")
            await self.user_service.save_user_profile(account_id, profile)

        self._run(_seed_passive_only_partner_requirement())

        _, profile = self._run(self._send_message(account_id, "我想找成熟稳重的，同城优先", sex="男"))

        assert profile.partner_requirement is not None
        assert "成熟稳重" in profile.partner_requirement
        assert "同城优先" in profile.partner_requirement
        assert profile.is_active_ask_closed("partner_requirement") is True

    def test_passive_only_monthly_income_still_extracts_from_user_message(self):
        """月收入进入 PASSIVE_ONLY 后，用户主动表达时仍然要能入档。"""
        account_id = f"policy_passive_income_extract_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))

        async def _seed_passive_only_monthly_income():
            profile = await self._seed_profile_fields(
                account_id,
                sex="女",
                age=29,
                location="杭州",
                education="本科",
            )
            profile.close_active_ask("monthly_income")
            await self.user_service.save_user_profile(account_id, profile)

        self._run(_seed_passive_only_monthly_income())

        _, profile = self._run(self._send_message(account_id, "我现在税前15k左右", sex="女"))

        assert profile.monthly_income == "税前15k左右"
        assert profile.is_active_ask_closed("monthly_income") is True

    def test_contact_repair_turn_still_blocks_medium_fields(self, monkeypatch):
        """联系方式纠错轮次里，即使模型夹带中等字段，也必须被流程剥掉。"""
        account_id = f"policy_contact_repair_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))
        self._run(
            self._seed_profile_fields(
                account_id,
                sex="男",
                age=31,
                location="深圳",
                education="本科",
                occupation="程序员",
                marital_status="单身",
            )
        )
        self._run(
            self.chat_service.dialogue_manager.update_recent_responses(
                account_id,
                "电话这块你要是方便就留一个，不方便的话我们先继续聊也行。",
            )
        )

        async def _scripted_call_ai(_prompt: str, _account_id: str, _user_message: str = "") -> str:
            return (
                "对，刚刚问的是电话。"
                "如果你方便的话，我再轻问一句，你月收入大概在哪个区间？"
                "电话这块你先不用急，我们继续聊也行。\n"
                f"{self._blank_extract_block()}"
            )

        monkeypatch.setattr(self.chat_service, "_call_ai", _scripted_call_ai)

        response, _ = self._run(self._send_message(account_id, "不是问的电话吗？", sex="男"))

        assert "电话" in response
        assert "月收入" not in response
        assert "收入大概" not in response
        assert "另一半" not in response

    def test_faq_repeat_followup_reentry_still_blocks_medium_fields(self, monkeypatch):
        """FAQ 连续追问后的恢复轮次，在资料已成熟时也不能跳去中等字段。"""
        account_id = f"policy_faq_repeat_reentry_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))
        self._run(
            self._seed_profile_fields(
                account_id,
                sex="女",
                age=29,
                location="杭州",
                education="本科",
                occupation="运营",
                marital_status="单身",
                partner_requirement="成熟稳重",
            )
        )
        profile = self._run(self.user_service.get_user_profile(account_id))
        profile.field_ask_count["monthly_income"] = 1
        self._run(self.user_service.save_user_profile(account_id, profile))
        self._run(
            self.chat_service.dialogue_manager.update_recent_responses(
                account_id,
                "收费这块基础匹配是免费的，你可以先放心。",
            )
        )
        self._run(
            self.chat_service.dialogue_manager.update_recent_responses(
                account_id,
                "我理解你会反复确认，这很正常。你更担心价格、流程，还是隐私安全？",
            )
        )

        async def _scripted_call_ai(_prompt: str, _account_id: str, _user_message: str = "") -> str:
            return (
                "你这边对另一半有什么比较在意的点吗？"
                "要是你愿意，留个电话也行。\n"
                f"{self._blank_extract_block()}"
            )

        monkeypatch.setattr(self.chat_service, "_call_ai", _scripted_call_ai)

        response, _ = self._run(self._send_message(account_id, "知道了", sex="女"))

        assert any(keyword in response for keyword in ["电话", "联系方式"])
        assert "另一半" not in response
        assert "在意的点" not in response

    def test_contact_misroute_correction_chain_blocks_medium_and_low_priority_fields(self, monkeypatch):
        """电话/微信误切后的连续纠错轮次里，中等字段和低优字段都不能插入。"""
        account_id = f"policy_contact_misroute_chain_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))
        self._run(
            self._seed_profile_fields(
                account_id,
                sex="男",
                age=31,
                location="深圳",
                education="本科",
                occupation="程序员",
                marital_status="单身",
            )
        )
        self._run(
            self.chat_service.dialogue_manager.update_recent_responses(
                account_id,
                "我知道你现在对微信这块还有顾虑。你要是愿意，留一个也行，不想留我们就先往下聊。",
            )
        )

        scripted_responses = iter(
            [
                (
                    "对，刚刚本来是在说电话。"
                    "如果你方便的话，我再轻问一句，你月收入大概在哪个区间？"
                    "身高大概多少也可以顺便说下。"
                    "电话这块你先不用急。\n"
                    f"{self._blank_extract_block()}"
                ),
                (
                    "抱歉，刚刚那句接乱了。"
                    "你这边对另一半有什么比较在意的点吗？"
                    "怎么称呼你会更方便？"
                    "电话这块我们先不往下逼。\n"
                    f"{self._blank_extract_block()}"
                ),
            ]
        )

        async def _scripted_call_ai(_prompt: str, _account_id: str, _user_message: str = "") -> str:
            return next(scripted_responses)

        monkeypatch.setattr(self.chat_service, "_call_ai", _scripted_call_ai)

        response_1, _ = self._run(self._send_message(account_id, "不是问的电话吗？", sex="男"))
        assert "电话" in response_1
        for keyword in ["月收入", "收入大概", "另一半", "身高", "体重", "怎么称呼", "叫什么"]:
            assert keyword not in response_1, f"联系方式纠错轮不应插入其它字段: {keyword}, response={response_1}"

        response_2, _ = self._run(self._send_message(account_id, "你已经糊涂了", sex="男"))
        assert any(keyword in response_2 for keyword in ["电话", "抱歉", "先不往下", "继续聊"]), response_2
        for keyword in ["月收入", "收入大概", "另一半", "在意的点", "身高", "体重", "怎么称呼", "叫什么"]:
            assert keyword not in response_2, f"不满纠错轮不应插入其它字段: {keyword}, response={response_2}"

    def test_contact_repair_after_wechat_redirect_still_blocks_all_non_contact_fields(self, monkeypatch):
        """从电话切到微信后的澄清轮次，只允许承接联系方式，不允许中等或低优字段插入。"""
        account_id = f"policy_contact_wechat_redirect_{uuid.uuid4().hex[:8]}"
        self._run(self._reset_user(account_id))
        self._run(
            self._seed_profile_fields(
                account_id,
                sex="女",
                age=29,
                location="杭州",
                education="本科",
                occupation="运营",
                marital_status="单身",
            )
        )
        self._run(
            self.chat_service.dialogue_manager.update_recent_responses(
                account_id,
                "电话不方便的话，微信也可以。",
            )
        )

        async def _scripted_call_ai(_prompt: str, _account_id: str, _user_message: str = "") -> str:
            return (
                "对，刚刚是从电话转到微信这条。"
                "你这边对另一半有什么比较在意的点吗？"
                "体重这块方便说下吗？"
                "微信这块你不想留也没关系。\n"
                f"{self._blank_extract_block()}"
            )

        monkeypatch.setattr(self.chat_service, "_call_ai", _scripted_call_ai)

        response, _ = self._run(self._send_message(account_id, "刚刚不是在说微信吗？", sex="女"))

        assert "微信" in response
        for keyword in ["另一半", "在意的点", "月收入", "收入大概", "身高", "体重", "怎么称呼", "叫什么"]:
            assert keyword not in response, f"微信纠错轮不应插入非联系方式字段: {keyword}, response={response}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="资料收集策略 AI 测试")
    parser.add_argument(
        "--real-ai",
        action="store_true",
        help="使用真实 AI 运行；默认使用离线 FakeAI，便于本地稳定验证",
    )
    args, remaining = parser.parse_known_args()

    if args.real_ai:
        os.environ["PROFILE_POLICY_USE_REAL_AI"] = "1"

    pytest_args = [__file__, "-v", "-o", "addopts="]
    pytest_args.extend(remaining)
    raise SystemExit(pytest.main(pytest_args))

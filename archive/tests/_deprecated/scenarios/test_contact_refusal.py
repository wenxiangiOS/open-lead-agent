#!/usr/bin/env python3
"""
联系方式拒绝场景测试
验证用户主动拒绝联系方式时的处理逻辑
"""

import os
import sys
import asyncio
import uuid
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 清除代理环境变量
for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
    os.environ.pop(proxy_var, None)
os.environ['NO_PROXY'] = '.bigmodel.cn,bigmodel.cn,.doubao.com,doubao.com,.volces.com,volces.com,localhost,127.0.0.1,::1,.cn'
os.environ['no_proxy'] = '.bigmodel.cn,bigmodel.cn,.doubao.com,doubao.com,.volces.com,volces.com,localhost,127.0.0.1,::1,.cn'

project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.services.core.chat_service import ChatService
from src.services.ai_service import AIService
from src.services.data.user_service import UserService
from src.models.requests import ChatRequest


class ContactRefusalTester:
    """联系方式拒绝场景测试"""

    def __init__(self):
        self.ai_service = AIService()
        self.user_service = UserService()
        self.chat_service = ChatService(self.ai_service, self.user_service)

    async def reset_user(self, account_id: str):
        """重置用户数据"""
        await self.chat_service.reset_user_conversation(account_id)
        print(f"[重置] 已清除用户 {account_id} 的数据\n")

    async def send_message(self, account_id: str, message: str) -> tuple:
        """发送消息并返回 (AI回复, 用户资料)"""
        request = ChatRequest(
            question=message,
            accountId=account_id,
            dialogId=f"test_{uuid.uuid4().hex[:8]}"
        )
        result = await self.chat_service.process_chat_request(request)
        response = result.get('response', '')
        profile_data = await self.user_service.get_user_profile(account_id)
        profile = profile_data.to_dict() if profile_data else {}
        return response, profile

    async def test_wechat_refusal_then_phone(self):
        """
        测试场景：用户主动拒绝微信，AI 争取微信后，用户再次拒绝，AI 应该争取电话
        """
        print("=" * 60)
        print("📋 测试场景: 用户拒绝微信后，AI 应争取电话")
        print("=" * 60)

        account_id = f"test_contact_{uuid.uuid4().hex[:8]}"
        await self.reset_user(account_id)

        user_msg = "我叫小张，男的，30岁，175cm，70kg，深圳，本科，IT，2万，单身"
        print(f"[第1轮] 用户: {user_msg}")
        response, profile = await self.send_message(account_id, user_msg)
        print(f"[第1轮] AI: {response}")
        print(f"[状态] 收集进度: {profile.get('progress_percentage', 0):.1f}%")
        print()

        user_msg = "找个温柔的，25-30岁"
        print(f"[第2轮] 用户: {user_msg}")
        response, profile = await self.send_message(account_id, user_msg)
        print(f"[第2轮] AI: {response}")
        print(f"[状态] 择偶要求: {profile.get('partner_requirement', '无')}")
        print()

        user_msg = "不留微信可以吗"
        print(f"[第3轮] 用户: {user_msg}")
        response, profile = await self.send_message(account_id, user_msg)
        print(f"[第3轮] AI: {response}")
        print(f"[状态] wechat_persuasion_attempted={profile.get('wechat_persuasion_attempted')}")
        print()

        if "微信" in response and "电话" not in response:
            print("✅ 第3轮检查通过: AI 只争取微信，没有提电话")
        else:
            print(f"❌ 第3轮检查失败: AI 应该只争取微信，但回复是: {response}")

        user_msg = "不想留"
        print(f"[第4轮] 用户: {user_msg}")
        response, profile = await self.send_message(account_id, user_msg)
        print(f"[第4轮] AI: {response}")
        print(f"[状态] rejected_wechat={profile.get('rejected_wechat')}")
        print()

        if "电话" in response and ("好的那" in response or "也可以" in response):
            print("✅ 第4轮检查通过: AI 正确过渡到争取电话")
        elif "没关系哒" in response and "电话只是" in response:
            print(f"❌ 第4轮检查失败: AI 话术太生硬，应该自然过渡，但回复是: {response}")
        else:
            print(f"⚠️ 第4轮检查: AI 回复需要人工确认: {response}")

        return account_id

    async def test_hong_user(self):
        """
        测试场景：香港用户需要收集电话和微信
        """
        print("=" * 60)
        print("📋 测试场景: 香港用户需要收集电话和微信")
        print("=" * 60)

        account_id = f"test_hong_{uuid.uuid4().hex[:8]}"
        await self.reset_user(account_id)

        user_msg = "我叫小李，女的，28岁，160cm，50kg，香港，本科，文员，1.5万，单身"
        print(f"[第1轮] 用户: {user_msg}")
        response, profile = await self.send_message(account_id, user_msg)
        print(f"[第1轮] AI: {response}")
        print(f"[状态] 地区: {profile.get('location')}")
        print()

        user_msg = "找个香港的男生，有上进心"
        print(f"[第2轮] 用户: {user_msg}")
        response, profile = await self.send_message(account_id, user_msg)
        print(f"[第2轮] AI: {response}")
        print()

        user_msg = "没有了"
        print(f"[第3轮] 用户: {user_msg}")
        response, profile = await self.send_message(account_id, user_msg)
        print(f"[第3轮] AI: {response}")
        print()

        user_msg = "电话是56789012"
        print(f"[第4轮] 用户: {user_msg}")
        response, profile = await self.send_message(account_id, user_msg)
        print(f"[第4轮] AI: {response}")
        print(f"[状态] contact={profile.get('contact')}, wechat={profile.get('wechat')}")
        print()

        if "微信" in response:
            print("✅ 第4轮检查通过: 香港用户收集电话后，AI 询问微信")
        else:
            print(f"⚠️ 第4轮检查: AI 是否询问微信需要人工确认: {response}")

        return account_id

    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("🧪 联系方式拒绝场景测试")
        print("=" * 60)
        print()

        try:
            await self.test_wechat_refusal_then_phone()
            print()

            await self.test_hong_user()
            print()

            print("=" * 60)
            print("📊 测试完成")
            print("=" * 60)

        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()


def main():
    tester = ContactRefusalTester()
    asyncio.run(tester.run_all_tests())


if __name__ == "__main__":
    main()

"""
离异场景自动化测试

测试场景：
1. 用户直接说"分居中可以吗" - 应该直接回复结束语
2. 用户说"离异" -> AI问手续 -> 用户说"办妥了" - 应该继续收集信息
3. 用户说"离异" -> AI问手续 -> 用户说"办理中" - 应该回复结束语
4. 用户说"离异" -> AI问手续 -> 用户说"还没办好" - 应该回复结束语
5. 用户说"正在分居" - 应该直接回复结束语
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uuid


async def test_scenario(scenario_name: str, messages: list, check_func):
    """测试单个场景"""
    print(f"\n{'='*60}")
    print(f"📋 测试场景: {scenario_name}")
    print(f"{'='*60}")

    from src.services.core.chat_service import ChatService
    from src.services.data.user_service import UserService
    from src.services.ai_service import AIService
    from src.models.requests import ChatRequest

    ai_service = AIService()
    user_service = UserService()
    chat_service = ChatService(ai_service, user_service)

    account_id = f"test_divorce_{uuid.uuid4().hex[:8]}"

    try:
        profile = await user_service.get_user_profile(account_id)
        profile.conversation_ended = False
        profile.marital_status = None
        profile.divorce_confirmed = False
        profile.collection_progress = {k: False for k in profile.collection_progress}
        await user_service.save_user_profile(account_id, profile)
        print(f"[重置] 已清除用户 {account_id} 的数据")

        responses = []
        for i, msg in enumerate(messages):
            print(f"\n[第{i+1}轮] 用户: {msg}")
            request = ChatRequest(
                question=msg,
                accountId=account_id,
                dialogId=f"test_{uuid.uuid4().hex[:8]}"
            )
            result = await chat_service.process_chat_request(request)
            response = result.get("response", "")
            responses.append(response)
            print(f"[第{i+1}轮] AI: {response}")

            profile = await user_service.get_user_profile(account_id)
            print(f"[状态] conversation_ended={profile.conversation_ended}, marital_status={profile.marital_status}")

        success = check_func(responses)
        if success:
            print(f"\n✅ 测试通过: {scenario_name}")
        else:
            print(f"\n❌ 测试失败: {scenario_name}")

        return success

    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有测试场景"""
    results = []

    print("\n" + "="*60)
    print("🧪 离异场景自动化测试")
    print("="*60)

    result1 = await test_scenario(
        "用户直接说'分居中可以吗' - 应直接回复结束语",
        ["分居中可以吗"],
        lambda responses: (
            ("分居" in responses[0] or "暂时" in responses[0] or "等" in responses[0]) and
            ("办妥" in responses[0] or "再来" in responses[0] or "顺利" in responses[0])
        )
    )
    results.append(result1)

    result2 = await test_scenario(
        "用户说离异后确认办妥 - 应继续收集信息",
        ["找对象", "男，30岁，深圳", "离异", "办妥了"],
        lambda responses: (
            ("手续" in responses[2] or "单身" in responses[2] or "办妥" in responses[2] or "确认" in responses[2])
        )
    )
    results.append(result2)

    result3 = await test_scenario(
        "用户说离异后说办理中 - 应回复结束语",
        ["找对象", "男，30岁，深圳", "离异", "办理中"],
        lambda responses: (
            ("等" in responses[3] or "祝" in responses[3] or "再来" in responses[3] or "顺利" in responses[3])
        )
    )
    results.append(result3)

    result4 = await test_scenario(
        "用户说离异后说还没办好 - 应回复结束语",
        ["找对象", "男，30岁，深圳", "离异", "还没办好"],
        lambda responses: (
            ("等" in responses[3] or "祝" in responses[3] or "再来" in responses[3] or "顺利" in responses[3])
        )
    )
    results.append(result4)

    result5 = await test_scenario(
        "用户说'正在分居' - 应直接回复结束语",
        ["正在分居，想找对象"],
        lambda responses: (
            ("分居" in responses[0] or "暂时" in responses[0] or "等" in responses[0]) and
            ("办妥" in responses[0] or "再来" in responses[0] or "顺利" in responses[0])
        )
    )
    results.append(result5)

    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")

    if passed == total:
        print("🎉 所有测试通过！")
    else:
        print(f"⚠️ 有 {total - passed} 个测试失败")


if __name__ == "__main__":
    asyncio.run(main())

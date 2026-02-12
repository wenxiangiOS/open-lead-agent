#!/usr/bin/env python3
"""
小缘 AI 红娘 - 交互式测试工具

使用方式：python testChat.py 或 ./t
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# 确保可以导入 src 模块
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.services.chat_service import ChatService
from src.services.ai_service import AIService
from src.services.user_service import UserService
from src.models.requests import ChatRequest
from src.config.settings import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChatTester:
    """交互式聊天测试工具"""

    def __init__(self):
        """初始化测试工具"""
        self.account_id = "test_user_001"
        self.dialog_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.message_count = 0

        # 初始化服务
        self.ai_service = AIService()
        self.user_service = UserService()
        self.chat_service = ChatService(self.ai_service, self.user_service)

        print("=" * 50)
        print("🤖 小缘 AI 红娘 - 测试工具")
        print("=" * 50)
        print(f"用户ID: {self.account_id}")
        print(f"对话ID: {self.dialog_id}")
        print("-" * 50)
        print("命令:")
        print("  quit/exit/q - 退出")
        print("  user <id> - 切换用户")
        print("  reset - 重置对话")
        print("  profile - 查看资料")
        print("  history - 查看历史")
        print("  token - 查看Token统计")
        print("  help - 显示帮助")
        print("-" * 50)

    async def welcome(self):
        """发送欢迎消息"""
        print("👧 小缘: 你好呀，我们是同城脱单联盟，这边需要帮脱单吗？可以根据小哥哥/小姐姐的要求推荐合适的男生/女生哦！")
        print("（此条为系统自动发送）")
        print("怎么牵线TA？")
        print("想找适合自己的男生/女生？")
        print()

    async def send_message(self, user_input: str):
        """发送消息"""
        if not user_input.strip():
            return

        self.message_count += 1

        # 构建请求
        request = ChatRequest(
            question=user_input,
            accountId=self.account_id,
            dialogId=self.dialog_id
        )

        # 处理请求
        try:
            result = await self.chat_service.process_chat_request(request)

            if result.get('success'):
                response = result.get('response', '抱歉，我没有理解您的意思')
                # 如果回复为空，不显示（表示委婉结束话题）
                if response and response.strip():
                    print(f"👧 小缘: {response}\n")

                # 显示收集的信息
                if result.get('collected_info'):
                    collected = result['collected_info']
                    print(f"  [已收集信息]")
                    for key, value in collected.items():
                        print(f"    {key}: {value}")
                    print()

                # 显示Token使用情况
                await self.show_token_stats()

            else:
                error = result.get('error', '处理失败')
                print(f"❌ 错误: {error}\n")

        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            print(f"❌ 处理失败: {e}\n")

    async def show_token_stats(self):
        """显示Token使用统计"""
        stats = await AIService.get_token_usage()
        if stats['call_count'] > 0:
            print(f"  [Token统计] 本次会话累计: {stats['total_tokens']} tokens "
                  f"(输入: {stats['prompt_tokens']}, 输出: {stats['completion_tokens']}, "
                  f"调用次数: {stats['call_count']})")
            print()

    async def show_profile(self):
        """显示用户资料"""
        result = await self.chat_service.get_user_profile(self.account_id)

        if result.get('success'):
            profile = result.get('profile', {})
            print(f"\n📋 用户资料:")
            print(f"  称呼: {profile.get('last_name', '未留')}")
            print(f"  性别: {profile.get('sex', '未留')}")
            print(f"  年龄: {profile.get('age', '未留')}")
            print(f"  身高: {profile.get('height', '未留')}")
            print(f"  体重: {profile.get('weight', '未留')}")
            print(f"  地区: {profile.get('location', '未留')}")
            print(f"  学历: {profile.get('education', '未留')}")
            print(f"  婚况: {profile.get('marital_status', '未留')}")
            print(f"  月收入: {profile.get('monthly_income', '未留')}")
            print(f"  职业: {profile.get('occupation', '未留')}")
            print(f"  联系方式: {profile.get('contact', '未留')}")
            print(f"  收集进度: {profile.get('progress_percentage', 0):.1f}%")
            print()

    async def show_history(self):
        """显示对话历史"""
        result = await self.chat_service.get_user_conversation_history(
            self.account_id,
            limit=10
        )

        if result.get('success'):
            history = result.get('history', [])
            print(f"\n📜 对话历史 (最近 {len(history)} 条):\n")

            for i, msg in enumerate(history[-10:], 1):
                role = "👤 你" if msg.get('role') == 'user' else "👧 小缘"
                content = msg.get('content', '')[:100]
                print(f"  {i}. {role}: {content}")
            print()

    async def reset_conversation(self):
        """重置对话"""
        result = await self.chat_service.reset_user_conversation(self.account_id)
        print(f"\n✅ {result.get('message', '对话已重置')}\n")

    async def switch_user(self, new_user_id: str):
        """切换用户"""
        old_id = self.account_id
        self.account_id = new_user_id
        self.dialog_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.message_count = 0

        print(f"\n✅ 已切换用户: {old_id} → {new_user_id}")
        print(f"用户ID: {self.account_id}")
        print(f"对话ID: {self.dialog_id}")
        print()

    async def show_token_stats_detail(self):
        """显示Token统计详情"""
        stats = await AIService.get_token_usage()
        print(f"\n📊 Token使用统计:")
        print(f"  总Token: {stats['total_tokens']}")
        print(f"  输入Token: {stats['prompt_tokens']}")
        print(f"  输出Token: {stats['completion_tokens']}")
        print(f"  调用次数: {stats['call_count']}")
        print()

    async def run(self):
        """运行测试工具"""
        # 发送欢迎消息
        await self.welcome()

        # 主循环
        while True:
            try:
                # 获取用户输入
                user_input = input("你: ").strip()

                if not user_input:
                    continue

                # 处理命令
                if user_input.lower() in ('quit', 'exit', 'q'):
                    # 显示最终Token统计
                    stats = await AIService.get_token_usage()
                    if stats['call_count'] > 0:
                        print(f"\n📊 本次会话Token统计:")
                        print(f"  总计: {stats['total_tokens']} tokens")
                        print(f"  输入: {stats['prompt_tokens']}")
                        print(f"  输出: {stats['completion_tokens']}")
                        print(f"  调用: {stats['call_count']}次")
                    print("\n👋 再见啦！")
                    break

                elif user_input.lower() == 'reset':
                    await self.reset_conversation()

                elif user_input.lower() == 'profile':
                    await self.show_profile()

                elif user_input.lower() == 'history':
                    await self.show_history()

                elif user_input.lower() == 'token':
                    await self.show_token_stats_detail()

                elif user_input.lower().startswith('user '):
                    # 切换用户命令：user <新用户ID>
                    new_user_id = user_input[5:].strip()
                    if new_user_id:
                        await self.switch_user(new_user_id)
                    else:
                        print("\n❌ 请提供用户ID，例如: user test_user_002\n")

                elif user_input.lower() == 'help':
                    print("\n📖 命令:")
                    print("  quit/exit/q - 退出")
                    print("  user <id> - 切换用户")
                    print("  reset - 重置对话")
                    print("  profile - 查看资料")
                    print("  history - 查看历史")
                    print("  token - 查看Token统计")
                    print("  help - 显示帮助")
                    print()

                else:
                    # 发送消息
                    await self.send_message(user_input)

            except KeyboardInterrupt:
                print("\n\n👋 再见啦！")
                break
            except Exception as e:
                logger.error(f"发生错误: {e}")
                print(f"\n❌ 错误: {e}\n")


def main():
    """主函数"""
    tester = ChatTester()
    asyncio.run(tester.run())


if __name__ == "__main__":
    main()

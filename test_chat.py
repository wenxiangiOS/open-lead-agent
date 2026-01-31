"""交互式测试脚本 - 在终端实时测试豆包 API（含信息收集）"""

import sys
import os
import asyncio

# 确保 src 目录在 Python 路径中
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# 禁用代理
os.environ['NO_PROXY'] = '*'
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

from src.api.routes import chat_service
from src.models.requests import ChatRequest

print("=" * 60)
print("豆包 AI 红娘 - 交互式测试（含信息收集）")
print("=" * 60)
print("输入消息，输入 'quit' 或 'exit' 退出")
print("输入 'info' 查看已收集的用户信息\n")

# 默认用户ID
user_id = "test_user_001"
print(f"当前用户ID: {user_id}")
print(f"如需切换用户，请输入 'user:新的ID'\n")

async def process_message(msg: str):
    """处理用户消息"""
    try:
        # 构造请求
        request = ChatRequest(
            question=msg,
            accountId=user_id,
            sex="男"  # 默认性别
        )

        # 通过 ChatService 处理（会自动收集信息）
        result = await chat_service.process_chat_request(request)

        if result.get("success"):
            return result.get('response')
        else:
            return f"[错误] {result.get('error')}"

    except Exception as e:
        return f"[异常] {e}"


async def show_user_info():
    """显示已收集的用户信息"""
    user_profile = chat_service.user_service.get_user_profile_dict(user_id)

    print("\n" + "=" * 60)
    print("已收集的用户信息:")
    print("=" * 60)

    for key, value in user_profile.items():
        if value and value != "unknown":
            print(f"  {key}: {value}")

    progress = user_profile.get('collection_progress', {})
    collected = sum(1 for v in progress.values() if v)
    total = len(progress)
    print(f"\n收集进度: {collected}/{total} ({user_profile.get('progress_percentage', 0):.1f}%)")

    missing = user_profile.get('missing_fields', [])
    if missing:
        print(f"待收集字段: {', '.join(missing[:5])}" + ("..." if len(missing) > 5 else ""))

    print("=" * 60 + "\n")


async def interactive_chat():
    """交互式聊天"""
    while True:
        try:
            # 获取用户输入
            user_input = input("你: ").strip()

            # 退出条件
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("再见！")
                break

            # 查看信息
            if user_input.lower() == 'info':
                await show_user_info()
                continue

            # 切换用户
            if user_input.lower().startswith('user:'):
                parts = user_input.split(':', 1)
                if len(parts) > 1 and parts[1].strip():
                    user_id = parts[1].strip()
                    print(f"\n已切换到用户: {user_id}\n")
                continue

            if not user_input:
                continue

            # 处理消息
            print("豆包: ", end="", flush=True)

            # 处理消息并获取回复
            response = await process_message(user_input)

            # 打印回复
            print(response)
            print()

        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except EOFError:
            print("\n\n再见！")
            break


# 运行交互式聊天
asyncio.run(interactive_chat())

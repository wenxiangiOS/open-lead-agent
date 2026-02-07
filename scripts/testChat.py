#!/usr/bin/env python3
"""实时JSON提取测试 - 支持多用户切换"""

import asyncio
import sys
import os

# 设置路径
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

# 禁用代理
os.environ['NO_PROXY'] = '*'
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

import json
from src.api.routes import chat_service, user_service
from src.models.requests import ChatRequest

# 禁用输出缓冲
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

def clean_invalid_unicode(text: str) -> str:
    """清理无效的 Unicode 字符"""
    try:
        return text.encode('utf-8', errors='ignore').decode('utf-8')
    except Exception:
        import re
        return re.sub(r'[\udc80-\udcff]', '', text)

def print_flush(*args, **kwargs):
    print(*args, **kwargs, flush=True)

def get_user_prompt():
    """获取用户输入提示（显示当前用户ID）"""
    return f"[当前用户: {user_id}]\n你: "

def show_help():
    """显示帮助信息"""
    print_flush("\n" + "=" * 70)
    print_flush("📝 可用命令:")
    print_flush("  /switch <用户ID>  - 切换到新用户（如: /switch test_user_001）")
    print_flush("  /current         - 查看当前用户ID")
    print_flush("  /clear           - 清除当前用户数据（重新开始）")
    print_flush("  /info            - 查看当前用户完整档案")
    print_flush("  /help            - 显示此帮助信息")
    print_flush("  /quit, /exit, /q - 退出程序")
    print_flush()
    print_flush("💡 快捷用法:")
    print_flush("  用户ID: 消息      - 直接切换用户并发送消息")
    print_flush("  例如: test_user_002: 你好")
    print_flush("  例如: user_小红: 我是女的，26岁")
    print_flush("=" * 70 + "\n")

def show_current_user():
    """显示当前用户信息"""
    print_flush(f"\n📌 当前用户: {user_id}")

    # 获取用户档案
    try:
        profile = user_service.get_user_profile(user_id)
        print_flush(f"   姓名: {profile.last_name or '未填写'}")
        print_flush(f"   性别: {profile.sex or '未填写'}")
        print_flush(f"   年龄: {profile.age or '未填写'}")
        print_flush(f"   所在地: {profile.location or '未填写'}")
        print_flush(f"   学历: {profile.education or '未填写'}")
        print_flush(f"   职业: {profile.occupation or '未填写'}")
        print_flush(f"   身高: {profile.height or '未填写'}")
        print_flush(f"   体重: {profile.weight or '未填写'}")
        print_flush(f"   月收入: {profile.monthly_income or '未填写'}")
        print_flush(f"   婚况: {profile.marital_status or '未填写'}")
        print_flush(f"   联系方式: {profile.contact or '未填写'}")
    except Exception as e:
        print_flush(f"   (新用户，暂无数据)")
    print_flush()

def show_user_info():
    """显示用户完整档案"""
    print_flush(f"\n{'=' * 70}")
    print_flush(f"📊 用户完整档案: {user_id}")
    print_flush(f"{'=' * 70}")

    try:
        profile_dict = user_service.get_user_profile_dict(user_id)

        # 提取用户信息（排除内部字段）
        user_data = {}
        for key, value in profile_dict.items():
            if key not in ['account_id', 'created_at', 'updated_at', 'collection_progress',
                          'progress_percentage', 'missing_fields', 'error_count', 'skipped_fields']:
                if value is not None and value != "":
                    user_data[key] = value

        if user_data:
            json_str = json.dumps(user_data, ensure_ascii=False, indent=2)
            print_flush(json_str)
        else:
            print_flush("暂无数据")
    except Exception as e:
        print_flush(f"获取档案失败: {e}")

    print_flush(f"{'=' * 70}\n")

def clear_user_data():
    """清除当前用户数据"""
    try:
        # 删除Redis中的数据
        from src.services.redis_service import redis_service
        redis_service.delete_sync(f"user_profile:{user_id}")
        redis_service.delete_sync(f"user_state:{user_id}")
        print_flush(f"\n✅ 已清除用户 [{user_id}] 的数据，可以重新开始测试\n")
    except Exception as e:
        print_flush(f"\n❌ 清除数据失败: {e}\n")

print_flush("=" * 70)
print_flush("豆包 AI 红娘 - 多用户测试模式")
print_flush("=" * 70)
print_flush("\n💡 快捷切换用户: 用户ID: 消息 (如: test_002: 你好)")
print_flush("   或输入 /help 查看所有命令\n")

# 默认用户ID
user_id = "test_user_001"

# 导入AIService用于获取token统计
from src.services.ai_service import AIService

async def chat():
    global user_id

    # 显示欢迎信息
    show_current_user()

    while True:
        try:
            raw_input = input(get_user_prompt())
            user_input = clean_invalid_unicode(raw_input).strip()
        except EOFError:
            break

        # 空输入时不显示新提示符，直接继续（显示一个空行让视觉效果更好）
        if not user_input:
            continue

        # 处理快速切换用户（格式：用户ID: 消息）
        if ':' in user_input and not user_input.startswith('/'):
            possible_user_id = user_input.split(':', 1)[0].strip()
            # 检查是否是有效的用户ID格式（不包含空格，且不是已知命令）
            if ' ' not in possible_user_id and len(possible_user_id) > 0:
                # 确实是用户ID切换
                actual_message = user_input.split(':', 1)[1].strip()
                user_id = possible_user_id
                print_flush(f"\n✅ 已切换到用户: {user_id}\n")
                # 如果有消息内容，继续处理
                if actual_message:
                    user_input = actual_message
                else:
                    show_current_user()
                    continue
            # 如果不是用户ID切换（比如消息中有冒号），则正常处理

        # 处理命令
        if user_input.startswith('/'):
            command = user_input.lower().split()
            cmd = command[0]

            # 退出命令
            if cmd in ['/quit', '/exit', '/q']:
                print_flush("\n再见！")
                token_usage = await AIService.get_token_usage()
                print_flush()
                print_flush("=" * 70)
                print_flush("📊 Token使用统计:")
                print_flush(f"  API调用次数: {token_usage['call_count']}")
                print_flush(f"  输入Token: {token_usage['prompt_tokens']}")
                print_flush(f"  输出Token: {token_usage['completion_tokens']}")
                print_flush(f"  总计Token: {token_usage['total_tokens']}")
                print_flush("=" * 70)
                break

            # 切换用户
            elif cmd == '/switch':
                if len(command) >= 2:
                    new_user_id = command[1]
                    user_id = new_user_id
                    print_flush(f"\n✅ 已切换到用户: {user_id}")
                    show_current_user()
                else:
                    print_flush("\n❌ 请提供用户ID，例如: /switch test_user_002\n")
                continue

            # 查看当前用户
            elif cmd == '/current':
                show_current_user()
                continue

            # 查看完整档案
            elif cmd == '/info':
                show_user_info()
                continue

            # 清除数据
            elif cmd == '/clear':
                clear_user_data()
                continue

            # 帮助信息
            elif cmd == '/help':
                show_help()
                continue

            else:
                print_flush(f"\n❌ 未知命令: {cmd}")
                print_flush("输入 /help 查看可用命令\n")
                continue

        # 空输入跳过
        if not user_input:
            continue

        # 正常对话
        print_flush("豆包正在思考...", end="")

        request = ChatRequest(
            question=user_input,
            accountId=user_id,
            sex="男"
        )

        result = await chat_service.process_chat_request(request)

        # 清除思考提示
        print_flush("\r" + " " * 40 + "\r", end="")

        if result.get("success"):
            # 打印豆包回复
            response = result.get('response', '')
            print_flush(f"豆包: {response}")

            # 打印本次提取的新数据
            all_fields = result.get('all_fields', [])

            if all_fields:
                json_data = {}
                for field_info in all_fields:
                    field = field_info.get("field")
                    value = field_info.get("value")
                    if field and value is not None:
                        json_data[field] = value

                wrapped_data = {user_id: json_data}
                json_str = json.dumps(wrapped_data, ensure_ascii=False)
                print_flush(f"📊 本次提取: {json_str}")

            # 获取并打印完整的用户档案
            user_profile = user_service.get_user_profile_dict(user_id)

            # 提取非 null 的字段
            complete_data = {}
            for key, value in user_profile.items():
                if key not in ['account_id', 'created_at', 'updated_at', 'collection_progress',
                              'progress_percentage', 'missing_fields', 'error_count', 'skipped_fields']:
                    if value is not None and value != "":
                        complete_data[key] = value

            wrapped_complete = {user_id: complete_data}
            complete_json_str = json.dumps(wrapped_complete, ensure_ascii=False, indent=2)
            print_flush(f"📊 完整档案:\n{complete_json_str}")

            # 显示累计token统计
            token_usage = await AIService.get_token_usage()
            print_flush(f"📊 累计Token: 调用{token_usage['call_count']}次 | "
                        f"输入{token_usage['prompt_tokens']} | "
                        f"输出{token_usage['completion_tokens']} | "
                        f"总计{token_usage['total_tokens']}")
        else:
            print_flush(f"[错误] {result.get('error')}")

        print_flush()

if __name__ == "__main__":
    try:
        asyncio.run(chat())
    except KeyboardInterrupt:
        print_flush("\n\n再见！")

#!/usr/bin/env python3
"""
测试验证层功能
"""

import asyncio
import sys
import os

# 确保可以导入 src 模块
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.api.middleware.validation import (
    RequestValidator,
    validate_request,
    CommonValidators,
    MinLengthRule,
    MaxLengthRule,
    PatternRule
)


async def test_request_validator():
    """测试请求验证器"""
    print("=" * 60)
    print("请求验证器测试")
    print("=" * 60)

    # 创建验证器
    validator = (
        RequestValidator()
        .add_required("user_id", "question")
        .add_min_length("question", 1)
        .add_max_length("question", 100)
        .add_pattern("user_id", r"^user_\d+$", "用户 ID 格式错误")
    )

    # 测试有效数据
    valid_data = {
        "user_id": "user_123",
        "question": "你好"
    }

    is_valid, errors = validator.validate(valid_data)
    print(f"\n✅ 有效数据测试: {'通过' if is_valid else '失败'}")
    if errors:
        print(f"   错误: {errors}")

    # 测试无效数据 - 缺少必填字段
    invalid_data_1 = {
        "question": "你好"
    }

    is_valid, errors = validator.validate(invalid_data_1)
    print(f"\n❌ 缺少必填字段测试: {'通过' if not is_valid else '失败'}")
    if errors:
        print(f"   错误: {errors}")

    # 测试无效数据 - 格式错误
    invalid_data_2 = {
        "user_id": "invalid_user",
        "question": "你好"
    }

    is_valid, errors = validator.validate(invalid_data_2)
    print(f"\n❌ 格式错误测试: {'通过' if not is_valid else '失败'}")
    if errors:
        print(f"   错误: {errors}")

    # 测试无效数据 - 长度超限
    invalid_data_3 = {
        "user_id": "user_123",
        "question": "x" * 200  # 超过最大长度
    }

    is_valid, errors = validator.validate(invalid_data_3)
    print(f"\n❌ 长度超限测试: {'通过' if not is_valid else '失败'}")
    if errors:
        print(f"   错误: {errors}")


async def test_common_validators():
    """测试常用验证器"""
    print("\n" + "=" * 60)
    print("常用验证器测试")
    print("=" * 60)

    # 测试用户 ID 验证
    user_validator = CommonValidators.user_id()
    valid_user = {"user_id": "user_123"}
    is_valid, errors = user_validator.validate(valid_user)
    print(f"\n✅ 用户 ID 验证: {'通过' if is_valid else '失败'}")

    # 测试聊天消息验证
    chat_validator = CommonValidators.chat_message()
    valid_chat = {"question": "你好呀"}
    is_valid, errors = chat_validator.validate(valid_chat)
    print(f"✅ 聊天消息验证: {'通过' if is_valid else '失败'}")

    # 测试分页验证
    page_validator = CommonValidators.pagination()
    valid_page = {"limit": 10, "offset": 0}
    is_valid, errors = page_validator.validate(valid_page)
    print(f"✅ 分页参数验证: {'通过' if is_valid else '失败'}")

    # 测试评分验证
    rating_validator = CommonValidators.rating()
    valid_rating = {"rating": 5}
    is_valid, errors = rating_validator.validate(valid_rating)
    print(f"✅ 评分验证: {'通过' if is_valid else '失败'}")


async def test_custom_rules():
    """测试自定义验证规则"""
    print("\n" + "=" * 60)
    print("自定义验证规则测试")
    print("=" * 60)

    # 创建自定义规则
    phone_rule = PatternRule(
        "phone",
        r"^1[3-9]\d{9}$",
        "手机号格式不正确，请输入11位手机号"
    )

    # 测试有效手机号
    print(f"\n✅ 有效手机号: {phone_rule.validate('13812345678')}")

    # 测试无效手机号
    print(f"❌ 无效手机号: {not phone_rule.validate('12345678901')}")
    print(f"   错误消息: {phone_rule.get_error_message()}")

    # 测试长度规则
    min_rule = MinLengthRule("name", 2)
    print(f"\n✅ 最小长度 (name='Tom'): {min_rule.validate('Tom')}")
    print(f"❌ 最小长度 (name='A'): {not min_rule.validate('A')}")

    max_rule = MaxLengthRule("name", 10)
    print(f"\n✅ 最大长度 (name='Tom'): {max_rule.validate('Tom')}")
    print(f"❌ 最大长度 (name='12345678901'): {not max_rule.validate('12345678901')}")


async def main():
    """主测试函数"""
    await test_request_validator()
    await test_common_validators()
    await test_custom_rules()

    print("\n" + "=" * 60)
    print("✅ 验证层测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

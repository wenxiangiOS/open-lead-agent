#!/usr/bin/env python3
"""示例：如何获取用户数据"""

from src.services.user_service import UserService

def get_user_data(account_id: str):
    """
    只需要用户ID即可获取完整数据

    Args:
        account_id: 用户账号ID（如"api_redis_test"）

    Returns:
        包含所有字段的用户档案
    """
    user_service = UserService()
    profile = user_service.get_user_profile(account_id)

    # 所有可用字段
    data = {
        "基本信息": {
            "姓名": profile.last_name,
            "性别": profile.sex,
            "年龄": profile.age,
            "所在地": profile.location,
        },
        "详细信息": {
            "学历": profile.education,
            "职业": profile.occupation,
            "身高": profile.height,
            "体重": profile.weight,
            "月收入": profile.monthly_income,
            "婚况": profile.marital_status,
            "联系方式": profile.contact,
        },
        "元数据": {
            "创建时间": profile.created_at,
            "更新时间": profile.updated_at,
        }
    }

    return data

# 示例：获取用户数据
if __name__ == "__main__":
    account_id = "api_redis_test"
    user_data = get_user_data(account_id)

    print(f"=== 用户ID: {account_id} ===")
    for category, fields in user_data.items():
        print(f"\n【{category}】")
        for key, value in fields.items():
            status = "✅" if value else "❌"
            print(f"  {status} {key}: {value or '未填写'}")

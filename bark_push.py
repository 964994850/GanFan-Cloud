"""
Bark 推送模块
使用 Bark iOS 应用推送每日菜单通知。
Bark 官方服务：https://api.day.app
推送格式：GET https://api.day.app/{key}/{title}/{body}
"""

import urllib.parse
import requests

BARK_BASE_URL = "https://api.day.app"


def push_menu(
    bark_key: str,
    title: str,
    special_meals: list[str],
    zero_point_meals: list[str],
    weekday_name: str,
) -> bool:
    """
    将今日菜单推送到 Bark。
    返回 True 表示成功，False 表示失败。
    """
    body_lines: list[str] = []

    if special_meals:
        body_lines.append("【特色餐】")
        body_lines.extend(special_meals)
    else:
        body_lines.append("【特色餐】今日无数据")

    body_lines.append("")

    if zero_point_meals:
        body_lines.append("【零点自选】")
        body_lines.extend(zero_point_meals[:15])  # 避免通知过长
        if len(zero_point_meals) > 15:
            body_lines.append(f"… 共 {len(zero_point_meals)} 项")
    else:
        body_lines.append("【零点自选】今日无数据")

    body = "\n".join(body_lines)

    encoded_title = urllib.parse.quote(title, safe="")
    encoded_body = urllib.parse.quote(body, safe="")
    url = f"{BARK_BASE_URL}/{bark_key}/{encoded_title}/{encoded_body}"

    params = {
        "sound": "minuet",
        "group": "每日菜单",
        "icon": "https://img.icons8.com/emoji/96/fork-and-knife-with-plate-emoji.png",
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == 200:
            print(f"✓ Bark 推送成功：{title}")
            return True
        else:
            print(f"✗ Bark 推送返回异常: {data}")
            return False
    except Exception as exc:
        print(f"✗ Bark 推送失败: {exc}")
        return False

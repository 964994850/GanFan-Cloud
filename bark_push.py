"""
Bark 推送模块
使用 Bark iOS 应用推送每日菜单通知。
Bark 官方服务：https://api.day.app
推送格式：GET https://api.day.app/{key}/{title}/{body}
"""

import requests

BARK_BASE_URL = "https://api.day.app"


def _build_body(
    special_meals1: list[str],
    zero_meals1: list[str],
    special_meals2: list[str],
    zero_meals2: list[str],
) -> str:
    lines: list[str] = []

    def section(header: str, meals: list[str]) -> None:
        lines.append(header)
        if meals:
            lines.extend(f"  {m}" for m in meals)
        else:
            lines.append("  今日暂无")
        lines.append("")

    lines.append("═══ 一期 ═══")
    section("▸ 特色餐", special_meals1)
    section("▸ 零点自选", zero_meals1)

    lines.append("═══ 二期 ═══")
    section("▸ 特色餐", special_meals2)
    section("▸ 零点自选", zero_meals2)

    # 去掉末尾多余空行
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def push_menu(
    bark_keys: str,
    title: str,
    special_meals1: list[str],
    zero_meals1: list[str],
    special_meals2: list[str],
    zero_meals2: list[str],
    weekday_name: str,
) -> bool:
    """
    将今日一期+二期菜单推送到 Bark。
    bark_keys 支持单个 Key 或多个 Key（逗号分隔），全部推送成功才返回 True。
    """
    keys = [k.strip() for k in bark_keys.split(",") if k.strip()]
    if not keys:
        print("✗ BARK_KEY 为空")
        return False

    body = _build_body(special_meals1, zero_meals1, special_meals2, zero_meals2)

    all_success = True
    for key in keys:
        url = f"{BARK_BASE_URL}/push"
        payload = {
            "device_key": key,
            "title": title,
            "body": body,
            "sound": "minuet",
            "group": "每日菜单",
            "icon": "https://img.icons8.com/emoji/96/fork-and-knife-with-plate-emoji.png",
        }
        try:
            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == 200:
                print(f"✓ Bark 推送成功：{title}（key=...{key[-6:]}）")
            else:
                print(f"✗ Bark 推送返回异常（key=...{key[-6:]}）: {data}")
                all_success = False
        except Exception as exc:
            print(f"✗ Bark 推送失败（key=...{key[-6:]}）: {exc}")
            all_success = False

    return all_success

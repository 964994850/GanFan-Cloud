"""
Bark 推送模块
使用 Bark iOS 应用推送每日菜单通知。
Bark 官方服务：https://api.day.app
使用 POST JSON 方式推送，支持长内容。
"""

import requests

BARK_BASE_URL = "https://api.day.app"


def _push(bark_keys: str, title: str, body: str) -> bool:
    """底层推送，支持逗号分隔的多个 Key。"""
    keys = [k.strip() for k in bark_keys.split(",") if k.strip()]
    if not keys:
        print("✗ BARK_KEY 为空")
        return False

    all_success = True
    for key in keys:
        payload = {
            "device_key": key,
            "title": title,
            "body": body,
            "sound": "minuet",
            "group": "每日菜单",
            "icon": "https://img.icons8.com/emoji/96/fork-and-knife-with-plate-emoji.png",
        }
        try:
            resp = requests.post(f"{BARK_BASE_URL}/push", json=payload, timeout=15)
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


def _format_section(label: str, meals: list[str]) -> list[str]:
    lines = [label]
    lines.extend(f"  {m}" for m in meals)
    return lines


def push_special(
    bark_keys: str,
    today_name: str,
    special1: list[str],
    special2: list[str],
) -> bool:
    """
    08:20 推送特色餐。一期/二期均无内容时跳过不推。
    """
    if not special1 and not special2:
        print("今日无特色餐，跳过推送")
        return True

    lines: list[str] = []
    if special1:
        lines += ["═══ 一期特色餐 ═══"]
        lines += [f"  {m}" for m in special1]
        lines.append("")
    if special2:
        lines += ["═══ 二期特色餐 ═══"]
        lines += [f"  {m}" for m in special2]

    while lines and lines[-1] == "":
        lines.pop()

    return _push(bark_keys, f"{today_name} · 特色餐", "\n".join(lines))


def push_lunch(
    bark_keys: str,
    today_name: str,
    lunch1: list[str],
    lunch2: list[str],
) -> bool:
    """11:30 推送午餐自选。一期/二期均无内容时跳过不推。"""
    if not lunch1 and not lunch2:
        print("今日无午餐自选数据，推送提示")
        return _push(bark_keys, f"{today_name} · 午餐自选", "今日食堂无餐食")

    lines: list[str] = []
    lines += ["═══ 一期 ═══"]
    lines += _format_section("▸ 午餐自选", lunch1) if lunch1 else ["  今日暂无"]
    lines.append("")
    lines += ["═══ 二期 ═══"]
    lines += _format_section("▸ 午餐自选", lunch2) if lunch2 else ["  今日暂无"]

    while lines and lines[-1] == "":
        lines.pop()

    return _push(bark_keys, f"{today_name} · 午餐自选", "\n".join(lines))


def push_dinner(
    bark_keys: str,
    today_name: str,
    dinner1: list[str],
    dinner2: list[str],
) -> bool:
    """17:00 推送晚餐自选。一期/二期均无内容时跳过不推。"""
    if not dinner1 and not dinner2:
        print("今日无晚餐自选数据，推送提示")
        return _push(bark_keys, f"{today_name} · 晚餐自选", "今日食堂无餐食")

    lines: list[str] = []
    lines += ["═══ 一期 ═══"]
    lines += _format_section("▸ 晚餐自选", dinner1) if dinner1 else ["  今日暂无"]
    lines.append("")
    lines += ["═══ 二期 ═══"]
    lines += _format_section("▸ 晚餐自选", dinner2) if dinner2 else ["  今日暂无"]

    while lines and lines[-1] == "":
        lines.pop()

    return _push(bark_keys, f"{today_name} · 晚餐自选", "\n".join(lines))

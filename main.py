"""
每日菜单云端推送 — 主入口

用法：
  python main.py --mode special   # 08:20 推送特色餐（无则跳过）
  python main.py --mode lunch     # 11:30 推送午餐自选
  python main.py --mode dinner    # 17:00 推送晚餐自选

环境变量（GitHub Secrets）：
  MINERU_TOKEN   MinerU 官方 API Token
  BARK_KEY       Bark 设备 Key（多个用逗号分隔）
"""

import os
import sys
import argparse
import tempfile
from datetime import datetime
from pathlib import Path

from wechat_fetcher import get_latest_article, fetch_menu_images
from mineru_api import parse_image_with_api
from menu_parser import extract_tables_from_md, extract_today_menu
from bark_push import push_special, push_lunch, push_dinner


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["special", "lunch", "dinner"],
        required=True,
        help="推送模式：special=特色餐  lunch=午餐自选  dinner=晚餐自选",
    )
    args = parser.parse_args()
    mode: str = args.mode

    print("=" * 60)
    print(f"每日菜单推送 [{mode}]  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ── 读取必要的环境变量 ────────────────────────────────────────────────
    mineru_token = os.environ.get("MINERU_TOKEN", "").strip()
    bark_key = os.environ.get("BARK_KEY", "").strip()

    missing = [n for n, v in [("MINERU_TOKEN", mineru_token), ("BARK_KEY", bark_key)] if not v]
    if missing:
        print(f"✗ 缺少环境变量: {', '.join(missing)}")
        sys.exit(1)

    # ── 步骤 1：获取最新文章 ──────────────────────────────────────────────
    print("\n[1/4] 获取最新文章...")
    article_url, _ = get_latest_article()

    # ── 步骤 2：下载图片 ──────────────────────────────────────────────────
    print("\n[2/4] 下载菜单图片（一期 + 二期）...")
    with tempfile.TemporaryDirectory() as tmpdir:
        save_dir = Path(tmpdir)
        images = fetch_menu_images(article_url, save_dir, max_images=4)

        if len(images) < 2:
            print(f"✗ 下载图片不足（获取到 {len(images)} 张，需要至少 2 张）")
            sys.exit(1)

        # ── 步骤 3：两张图片分别 OCR ──────────────────────────────────────
        print("\n[3/4] 调用 MinerU API 解析图片（一期 + 二期）...")
        md1 = parse_image_with_api(images[0], mineru_token)
        md2 = parse_image_with_api(images[1], mineru_token)

    # ── 步骤 4：解析 + 按模式推送 ─────────────────────────────────────────
    print("\n[4/4] 解析表格并推送...")
    s1, z1 = extract_tables_from_md(md1)
    s2, z2 = extract_tables_from_md(md2)

    if not any([s1, z1, s2, z2]):
        print("✗ 两张图片均未提取到表格")
        sys.exit(1)

    special1, lunch1, dinner1, today_name = extract_today_menu(s1, z1)
    special2, lunch2, dinner2, _          = extract_today_menu(s2, z2)

    if mode == "special":
        success = push_special(bark_key, today_name, special1, special2)
    elif mode == "lunch":
        success = push_lunch(bark_key, today_name, lunch1, lunch2)
    else:
        success = push_dinner(bark_key, today_name, dinner1, dinner2)

    print("\n" + "=" * 60)
    if success:
        print("✓ 全部完成！")
    else:
        print("⚠ 推送失败，请检查 BARK_KEY")
        sys.exit(1)


if __name__ == "__main__":
    main()

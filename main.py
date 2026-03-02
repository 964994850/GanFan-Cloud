"""
每日菜单云端推送 — 主入口
流程：获取微信公众号图片 → MinerU API OCR → 解析表格 → Bark 推送

环境变量（GitHub Secrets）：
  MINERU_TOKEN   MinerU 官方 API Token
  BARK_KEY       Bark 设备 Key
"""

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from wechat_fetcher import get_latest_article, fetch_menu_images
from mineru_api import parse_image_with_api
from menu_parser import extract_tables_from_md, extract_today_menu
from bark_push import push_menu


def main() -> None:
    print("=" * 60)
    print(f"每日菜单推送  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ── 读取必要的环境变量 ────────────────────────────────────────────────
    mineru_token = os.environ.get("MINERU_TOKEN", "").strip()
    bark_key = os.environ.get("BARK_KEY", "").strip()

    missing = [name for name, val in [("MINERU_TOKEN", mineru_token), ("BARK_KEY", bark_key)] if not val]
    if missing:
        print(f"✗ 缺少环境变量: {', '.join(missing)}")
        sys.exit(1)

    # ── 步骤 1：获取最新微信公众号文章 ───────────────────────────────────
    print("\n[1/4] 获取最新文章...")
    article_url, article_title = get_latest_article()

    # ── 步骤 2：下载图片（取第2张，即菜单主图） ──────────────────────────
    print("\n[2/4] 下载菜单图片...")
    with tempfile.TemporaryDirectory() as tmpdir:
        save_dir = Path(tmpdir)
        images = fetch_menu_images(article_url, save_dir, max_images=4)

        if len(images) < 2:
            print(f"✗ 下载图片不足（获取到 {len(images)} 张，需要至少 2 张）")
            sys.exit(1)

        menu_image = images[1]  # 第2张为菜单表格图

        # ── 步骤 3：MinerU API OCR ─────────────────────────────────────
        print("\n[3/4] 调用 MinerU API 解析图片...")
        md_content = parse_image_with_api(menu_image, mineru_token)

    # ── 步骤 4：解析表格 + 推送 ──────────────────────────────────────────
    print("\n[4/4] 解析菜单表格并推送...")
    special_table, zero_point_table = extract_tables_from_md(md_content)

    if not special_table and not zero_point_table:
        print("✗ 未能从 Markdown 中提取到任何表格，请检查图片或 OCR 结果")
        sys.exit(1)

    special_meals, zero_point_meals, today_name = extract_today_menu(special_table, zero_point_table)

    title = f"{today_name}菜单"
    success = push_menu(bark_key, title, special_meals, zero_point_meals, today_name)

    print("\n" + "=" * 60)
    if success:
        print("✓ 全部完成！")
    else:
        print("⚠ 流程完成，但 Bark 推送失败，请检查 BARK_KEY")
        sys.exit(1)


if __name__ == "__main__":
    main()

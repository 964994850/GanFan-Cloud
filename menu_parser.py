"""
菜单表格解析模块（云端版）
从 MinerU 返回的 Markdown 文本中提取特色餐和零点自选表格，
并按星期筛选当天菜品列表。
逻辑移植自原 menu_pipeline.py，无本地依赖。
"""

import re
import io
from datetime import datetime

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

from bs4 import BeautifulSoup

# ── 星期名称映射 ──────────────────────────────────────────────────────────────
WEEKDAY_NAME_TO_NUM: dict[str, int] = {
    "星期一": 0, "星期二": 1, "星期三": 2, "星期四": 3,
    "星期五": 4, "星期六": 5, "星期日": 6,
    "周一": 0, "周二": 1, "周三": 2, "周四": 3,
    "周五": 4, "周六": 5, "周日": 6,
    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
    "Friday": 4, "Saturday": 5, "Sunday": 6,
}

WEEKDAY_NAMES = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def _get_weekday_name(weekday_num: int) -> str:
    return WEEKDAY_NAMES[weekday_num] if 0 <= weekday_num < 7 else f"星期{weekday_num + 1}"


def _parse_html_table(html_table: str) -> list[list] | None:
    """将 <table>…</table> HTML 字符串解析为二维列表（自动处理 rowspan/colspan）。"""
    if HAS_PANDAS:
        try:
            dfs = pd.read_html(io.StringIO(html_table))
            if dfs:
                return dfs[0].values.tolist()
        except Exception:
            pass

    soup = BeautifulSoup(html_table, "html.parser")
    table = soup.find("table")
    if not table:
        return None

    rows = []
    for tr in table.find_all("tr"):
        row = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if row:
            rows.append(row)
    return rows if rows else None


def extract_tables_from_md(md_content: str) -> tuple[list[list] | None, list[list] | None]:
    """
    从 Markdown 文本中提取第3、4个 <table> 块，
    分别对应特色餐表格和零点自选表格。
    """
    table_pattern = re.compile(r"<table>.*?</table>", re.DOTALL)
    all_tables = table_pattern.findall(md_content)

    special_table = None
    zero_point_table = None

    if len(all_tables) >= 3:
        special_table = _parse_html_table(all_tables[2])
        print("✓ 找到特色餐表格（第3个 table）")
    if len(all_tables) >= 4:
        zero_point_table = _parse_html_table(all_tables[3])
        print("✓ 找到零点自选表格（第4个 table）")

    if len(all_tables) < 3:
        print(f"⚠ 仅找到 {len(all_tables)} 个表格（需要至少3个）")

    return special_table, zero_point_table


def _detect_weekday_columns(header_row: list, data_col_start: int = 1) -> list[tuple[int, int]]:
    """识别表头行中的星期列，返回 [(col_index, weekday_num), ...]。"""
    result = []
    for col_idx, cell in enumerate(header_row):
        if col_idx < data_col_start:
            continue
        cell_str = str(cell).strip() if cell is not None else ""
        for name, num in WEEKDAY_NAME_TO_NUM.items():
            if name in cell_str:
                result.append((col_idx, num))
                break
    return result


def extract_today_menu(
    special_table: list[list] | None,
    zero_point_table: list[list] | None,
) -> tuple[list[str], list[str], str]:
    """
    根据当前日期从表格中提取今日菜单。
    返回 (特色餐列表, 零点自选列表, 今日星期名称)。
    """
    today_weekday = datetime.now().weekday()
    today_name = _get_weekday_name(today_weekday)

    special_meals: list[str] = []
    zero_point_meals: list[str] = []

    # 特色餐（仅工作日）
    if special_table and today_weekday < 5:
        cols = _detect_weekday_columns(special_table[0], data_col_start=1)
        col_map = {wnum: cidx for cidx, wnum in cols}
        if today_weekday in col_map:
            special_meals = _extract_special(special_table, col_map[today_weekday])
        else:
            print(f"⚠ 特色餐表格中未找到 {today_name} 对应列")

    # 零点自选
    if zero_point_table:
        cols = _detect_weekday_columns(zero_point_table[0], data_col_start=2)
        col_map = {wnum: cidx for cidx, wnum in cols}
        if today_weekday in col_map:
            zero_point_meals = _extract_zero_point(zero_point_table, col_map[today_weekday])
        else:
            print(f"⚠ 零点自选表格中未找到 {today_name} 对应列")

    return special_meals, zero_point_meals, today_name


def _extract_special(table: list[list], col_index: int) -> list[str]:
    meals = []
    for row in table[1:]:
        if len(row) > col_index and len(row) > 0:
            project = str(row[0]).strip().replace("nan", "")
            meal = str(row[col_index]).strip().replace("nan", "")
            if meal and project:
                meals.append(f"{project}: {meal}")
    return meals


def _extract_zero_point(table: list[list], col_index: int) -> list[str]:
    meals = []
    cur_category = ""
    cur_sub = ""
    for row in table[1:]:
        if len(row) > col_index:
            if len(row) > 0:
                v = str(row[0]).strip().replace("nan", "")
                if v:
                    cur_category = v
            if len(row) > 1:
                v = str(row[1]).strip().replace("nan", "")
                if v:
                    cur_sub = v
            meal = str(row[col_index]).strip().replace("nan", "")
            if meal:
                label = f"{cur_category}-{cur_sub}" if cur_sub else cur_category
                meals.append(f"{label}: {meal}")
    return meals

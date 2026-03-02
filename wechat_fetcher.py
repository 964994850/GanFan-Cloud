"""
微信公众号图片获取模块（云端版）
从公众号相册页面获取最新菜单文章，提取并下载图片。
无需 Playwright，纯 requests + BeautifulSoup。
"""

import re
import requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

TARGET_URL = (
    "https://mp.weixin.qq.com/mp/appmsgalbum"
    "?__biz=MjM5OTY5MDc4Mg==&action=getalbum"
    "&album_id=2533738113198948352&scene=126"
    "&sessionid=1769950878491#wechat_redirect"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _get_html(url: str) -> str:
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text


def _normalize_image_url(src: str) -> str:
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("/"):
        return "https://mp.weixin.qq.com" + src
    if not src.startswith("http"):
        return "https://mp.weixin.qq.com" + src
    return src


def _extract_image_urls(soup: BeautifulSoup) -> list[str]:
    content_area = soup.find("div", id="js_content")
    if not content_area:
        return []
    urls = []
    for img in content_area.find_all("img"):
        src = img.get("data-src") or img.get("src")
        if src:
            urls.append(_normalize_image_url(src))
    return urls


def _filter_content_images(image_urls: list[str]) -> list[str]:
    filtered = []
    for url in image_urls:
        url_lower = url.lower()
        if any(k in url_lower for k in ["avatar", "icon", "logo", "button", "btn"]):
            continue
        if url.startswith("data:image"):
            continue
        if "mmbiz" in url_lower and re.search(r"/(64|132)(/|$|\?|&)", url) and "/640" not in url:
            continue
        filtered.append(url)
    return filtered


def _get_file_extension(content_type: str, url: str) -> str:
    if "png" in content_type or ".png" in url.lower():
        return "png"
    if "gif" in content_type or ".gif" in url.lower():
        return "gif"
    if "webp" in content_type or ".webp" in url.lower():
        return "webp"
    return "jpg"


def _download_image(url: str, filepath: Path, referer: str) -> str:
    headers = {"User-Agent": USER_AGENT, "Referer": referer}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    filepath.write_bytes(resp.content)
    return resp.headers.get("content-type", "")


def get_latest_article() -> tuple[str, str]:
    """返回最新文章的 (url, title)"""
    print("正在访问微信公众号页面...")
    html = _get_html(TARGET_URL)
    soup = BeautifulSoup(html, "html.parser")

    items = soup.find_all("li", class_=re.compile(r"album__list-item"))
    if not items:
        raise RuntimeError("未找到任何文章列表项")

    articles = []
    for item in items:
        link = item.get("data-link", "").replace("&amp;", "&")
        title = item.get("data-title", "").replace("&amp;", "&")
        if not link:
            continue
        try:
            params = parse_qs(urlparse(link).query)
            mid = int(params.get("mid", [0])[0]) if params.get("mid") else 0
        except Exception:
            mid = 0
        articles.append({"title": title, "link": link, "mid": mid})

    if not articles:
        raise RuntimeError("未能解析到任何文章信息")

    articles.sort(key=lambda x: x["mid"], reverse=True)
    latest = articles[0]
    print(f"最新文章: {latest['title']}")
    return latest["link"], latest["title"]


def fetch_menu_images(article_url: str, save_dir: Path, max_images: int = 4) -> list[Path]:
    """
    从指定文章页面下载菜单图片。
    返回成功下载的本地路径列表。
    """
    save_dir.mkdir(parents=True, exist_ok=True)
    print(f"正在访问文章页面: {article_url}")

    html = _get_html(article_url)
    soup = BeautifulSoup(html, "html.parser")

    urls = _extract_image_urls(soup)
    if not urls:
        raise RuntimeError("文章中未找到图片")

    # 去重保序
    seen: set[str] = set()
    unique_urls = [u for u in urls if not (u in seen or seen.add(u))]  # type: ignore[func-returns-value]
    filtered = _filter_content_images(unique_urls)[:max_images]

    if not filtered:
        raise RuntimeError("过滤后无可下载图片")

    today = datetime.now().strftime("%Y%m%d")
    downloaded: list[Path] = []

    for idx, url in enumerate(filtered, 1):
        ext = _get_file_extension("", url)
        filepath = save_dir / f"menu_{today}_{idx}.{ext}"
        if filepath.exists():
            filepath.unlink()

        try:
            content_type = _download_image(url, filepath, article_url)
            actual_ext = _get_file_extension(content_type, url)
            if actual_ext != ext:
                new_path = save_dir / f"menu_{today}_{idx}.{actual_ext}"
                if new_path.exists():
                    new_path.unlink()
                filepath.rename(new_path)
                filepath = new_path
            downloaded.append(filepath)
            print(f"  ✓ 已保存: {filepath.name}")
        except Exception as exc:
            print(f"  ✗ 下载失败 ({url[:60]}...): {exc}")

    print(f"共下载 {len(downloaded)}/{len(filtered)} 张图片")
    return downloaded

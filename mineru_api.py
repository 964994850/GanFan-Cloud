"""
MinerU 官方云端 API 调用模块
流程：申请预签名上传 URL → PUT 上传本地图片 → 轮询批量任务结果 → 下载 ZIP 解压获取 .md
API 文档：https://mineru.net/doc/docs/index_en/
"""

import io
import os
import time
import zipfile
import requests
from pathlib import Path

BATCH_UPLOAD_URL = "https://mineru.net/api/v4/file-urls/batch"
BATCH_RESULT_URL = "https://mineru.net/api/v4/extract/task/batch/{batch_id}"

POLL_INTERVAL = 10   # 秒
POLL_TIMEOUT = 300   # 最多等待 5 分钟


def _headers(token: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }


def parse_image_with_api(image_path: Path, token: str) -> str:
    """
    将本地图片上传至 MinerU API，轮询等待完成，返回解析后的 Markdown 文本。
    抛出 RuntimeError 表示失败。
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"图片文件不存在: {image_path}")

    # ── 步骤 1：申请预签名上传 URL ────────────────────────────────────────
    print(f"正在向 MinerU API 申请上传链接: {image_path.name}")
    payload = {
        "files": [{"name": image_path.name, "is_ocr": True, "data_id": image_path.stem}],
        "enable_formula": False,
        "enable_table": True,
        "language": "ch",
        "model_version": "vlm",
    }
    resp = requests.post(BATCH_UPLOAD_URL, headers=_headers(token), json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != 0:
        raise RuntimeError(f"申请上传链接失败: {result}")

    batch_id: str = result["data"]["batch_id"]
    upload_urls: list[str] = result["data"]["file_urls"]
    if not upload_urls:
        raise RuntimeError("未获取到上传链接")

    # ── 步骤 2：PUT 上传图片（无需设置 Content-Type）────────────────────
    print(f"正在上传图片到预签名 URL...")
    with open(image_path, "rb") as f:
        up_resp = requests.put(upload_urls[0], data=f, timeout=60)
    if up_resp.status_code != 200:
        raise RuntimeError(f"图片上传失败，HTTP {up_resp.status_code}")
    print("  ✓ 图片上传成功")

    # ── 步骤 3：轮询批量任务结果 ─────────────────────────────────────────
    print(f"等待 MinerU 解析（batch_id={batch_id}）...")
    query_url = BATCH_RESULT_URL.format(batch_id=batch_id)
    deadline = time.time() + POLL_TIMEOUT

    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        poll_resp = requests.get(query_url, headers=_headers(token), timeout=30)
        poll_resp.raise_for_status()
        poll_data = poll_resp.json()

        if poll_data.get("code") != 0:
            raise RuntimeError(f"查询任务状态失败: {poll_data}")

        files_info: list[dict] = poll_data.get("data", {}).get("files", [])
        if not files_info:
            continue

        file_info = files_info[0]
        state: str = file_info.get("state", "")
        print(f"  任务状态: {state}")

        if state == "done":
            zip_url: str = file_info.get("full_zip_url", "")
            if not zip_url:
                raise RuntimeError("任务完成但未返回结果 zip 地址")
            return _extract_md_from_zip(zip_url)

        if state == "failed":
            err = file_info.get("err_msg", "未知错误")
            raise RuntimeError(f"MinerU 解析失败: {err}")

    raise TimeoutError(f"MinerU 解析超时（>{POLL_TIMEOUT}s），batch_id={batch_id}")


def _extract_md_from_zip(zip_url: str) -> str:
    """下载结果 ZIP，从中提取 .md 文件内容并返回。"""
    print(f"正在下载解析结果 ZIP...")
    resp = requests.get(zip_url, timeout=60)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        md_files = [name for name in zf.namelist() if name.endswith(".md")]
        if not md_files:
            raise RuntimeError("ZIP 中未找到 .md 文件")
        # 优先选择非 content_list 的主 md 文件
        primary = next((n for n in md_files if "content_list" not in n), md_files[0])
        content = zf.read(primary).decode("utf-8")
        print(f"  ✓ 获取 Markdown（{primary}，{len(content)} 字符）")
        return content

# 每日菜单云端推送（fan-cloud）

> **说明**：本目录是 `Fan/` 的云端化版本，**不修改父目录任何文件**。
> 原始本地版本位于 `Fan/`（`menu_pipeline.py` 等），保持原样不变。

## 架构

```
微信公众号文章
    ↓ (wechat_fetcher.py)
菜单图片下载（临时目录）
    ↓ (mineru_api.py)
MinerU 官方 API OCR → Markdown
    ↓ (menu_parser.py)
提取当天表格数据
    ↓ (bark_push.py)
Bark iOS 推送
```

GitHub Actions (`cron: 每天 08:00 北京时间`) 全程驱动，无需任何服务器。

## 目录结构

```
fan-cloud/
├── main.py               # 主入口，串联所有步骤
├── wechat_fetcher.py     # 微信公众号图片获取
├── mineru_api.py         # MinerU 官方 API 调用（上传+轮询+下载）
├── menu_parser.py        # 菜单 Markdown 表格解析
├── bark_push.py          # Bark iOS 推送
├── requirements.txt      # 依赖（无本地 MinerU）
└── .github/
    └── workflows/
        └── daily_menu.yml  # GitHub Actions 定时任务
```

## 前置准备（手动完成一次）

### 1. MinerU API Token

1. 访问 [https://mineru.net/apiManag](https://mineru.net/apiManag)
2. 注册账号，填问卷申请 API Token
3. 免费额度：每账号每天 2000 页（菜单图片仅消耗 1 页/天）

### 2. Bark 设备 Key

1. iPhone 在 App Store 搜索 **Bark** 下载
2. 打开 App，首页显示专属推送地址，其中 `api.day.app/` 后面的一串即为 Key

### 3. 上传代码到 GitHub

```bash
# 在 fan-cloud/ 目录下初始化仓库（或直接推整个 Fan/ 仓库）
git init
git add .
git commit -m "init: 每日菜单云端推送"
git remote add origin https://github.com/你的用户名/你的仓库.git
git push -u origin main
```

### 4. 配置 GitHub Secrets

在仓库页面 **Settings → Secrets and variables → Actions → New repository secret** 添加：

| Secret 名称 | 值 |
|---|---|
| `MINERU_TOKEN` | MinerU 申请的 API Token |
| `BARK_KEY` | Bark App 中显示的设备 Key |

## 本地测试

```bash
cd fan-cloud
pip install -r requirements.txt

# Windows PowerShell
$env:MINERU_TOKEN = "your_token"
$env:BARK_KEY = "your_bark_key"
python main.py

# Linux/macOS
MINERU_TOKEN=your_token BARK_KEY=your_bark_key python main.py
```

## 与原版本的差异

| 功能 | 原版（Fan/） | 云端版（fan-cloud/） |
|---|---|---|
| 图片获取 | `wechat_menu_scraper.py` | `wechat_fetcher.py`（相同逻辑，去掉 schedule） |
| OCR 解析 | 本地 `mineru` 命令行 | MinerU 官方 REST API |
| 结果输出 | 生成 HTML 文件 | Bark iOS 推送 |
| 触发方式 | 手动运行 | GitHub Actions cron |
| 本地依赖 | MinerU + Playwright | 仅 requests + bs4 + pandas |

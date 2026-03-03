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

由 **外部定时服务** 在指定时间调用 GitHub API 触发 workflow，无需自建服务器。

## 目录结构

```
fan-cloud/
├── main.py               # 主入口（--mode special/lunch/dinner）
├── wechat_fetcher.py     # 微信公众号图片获取
├── mineru_api.py         # MinerU 官方 API 调用
├── menu_parser.py        # 菜单表格解析
├── bark_push.py          # Bark 推送
├── requirements.txt
└── .github/workflows/
    ├── daily_special.yml   # 特色餐（08:20 触发）
    ├── daily_lunch.yml    # 午餐自选（11:30 触发）
    ├── daily_dinner.yml   # 晚餐自选（17:00 触发）
    └── daily_menu.yml     # 手动触发 + 选择模式
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

在仓库 **Settings → Secrets and variables → Actions** 添加：

| Secret 名称 | 值 |
|---|---|
| `MINERU_TOKEN` | MinerU 申请的 API Token |
| `BARK_KEY` | Bark App 中显示的设备 Key（多个用逗号分隔） |

### 5. 外部定时服务（替代 GitHub cron）

GitHub 自带的 schedule 容易漏跑，建议用 [cron-job.org](https://cron-job.org) 或 [EasyCron](https://www.easycron.com) 在指定时间触发 workflow。

**步骤：**

1. 在 GitHub 创建 **Personal Access Token**：Settings → Developer settings → Personal access tokens → Generate new token，勾选 `repo`。
2. 在定时服务里新建 **3 个定时任务**，请求方式 **POST**，URL 和时间为：

| 北京时间 | 请求 URL |
|----------|----------|
| 08:20 | `https://api.github.com/repos/你的用户名/你的仓库名/actions/workflows/daily_special.yml/dispatches` |
| 11:30 | `https://api.github.com/repos/你的用户名/你的仓库名/actions/workflows/daily_lunch.yml/dispatches` |
| 17:00 | `https://api.github.com/repos/你的用户名/你的仓库名/actions/workflows/daily_dinner.yml/dispatches` |

3. 请求头：`Authorization: Bearer 你的Token`，`Accept: application/vnd.github+json`，`X-GitHub-Api-Version: 2022-11-28`。
4. 请求体（JSON）：`{"ref":"main"}`（如默认分支是 `main`，否则改成实际分支名）。
5. 定时规则：按服务商的 cron 或“每天 08:20 / 11:30 / 17:00”设置（注意选 **北京时区** 或换算成 UTC：08:20=00:20 UTC，11:30=03:30 UTC，17:00=09:00 UTC）。

## 本地测试

```bash
cd fan-cloud
pip install -r requirements.txt

# Windows PowerShell
$env:MINERU_TOKEN = "your_token"
$env:BARK_KEY = "your_bark_key"
python main.py

# Linux/macOS
MINERU_TOKEN=your_token BARK_KEY=your_bark_key python main.py --mode special
```

## 与原版本的差异

| 功能 | 原版（Fan/） | 云端版（fan-cloud/） |
|---|---|---|
| 图片获取 | `wechat_menu_scraper.py` | `wechat_fetcher.py`（相同逻辑，去掉 schedule） |
| OCR 解析 | 本地 `mineru` 命令行 | MinerU 官方 REST API |
| 结果输出 | 生成 HTML 文件 | Bark iOS 推送 |
| 触发方式 | 手动运行 | 外部定时服务 + GitHub Actions workflow_dispatch |
| 本地依赖 | MinerU + Playwright | 仅 requests + bs4 + pandas |

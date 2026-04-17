# Transfermarkt Scout Platform — 项目完整说明

> **语言 / Language**: 中文在前，English below（第二部分）

---

# 第一部分：中文说明

## 项目简介

**Transfermarkt Scout Platform** 是一个基于 Streamlit 构建的足球数据 Dashboard。  
它通过爬取 [Transfermarkt](https://www.transfermarkt.co.uk) 网站，自动收集五大联赛（及英格兰低级别联赛）球队的阵容信息，并生成可下载的 **Pre Scout Report**（赛前侦察报告）。

### 核心功能

| 功能模块 | 说明 |
|---|---|
| 联赛 & 球队选择 | 支持8个联赛，自动抓取球队列表，24小时本地缓存 |
| Squad Overview | 展示双队完整阵容（姓名、位置、上场时间、年龄、合同信息） |
| Contract Watch | 筛选2026年夏季合同到期球员（不含租借），按上场时间排序 |
| Loan Players | 展示所有租借球员及其母队信息 |
| Pre Scout Report | 生成标准双栏赛前侦察报告，支持 HTML 预览和 PDF 下载 |

---

## 项目结构

```
scout_platform/
│
├── app.py                      ← Streamlit 主程序入口
├── requirements.txt            ← Python 依赖清单
├── README.md                   ← 快速启动说明
├── PROJECT_GUIDE.md            ← 本文件（完整说明）
│
├── scraper/                    ← 数据抓取模块
│   ├── __init__.py
│   ├── leagues.py              ← 联赛页面抓取 + 球队URL管理
│   └── team.py                 ← 球队阵容页面抓取（核心爬虫）
│
├── report/                     ← 报告生成模块
│   ├── __init__.py
│   ├── generator.py            ← Jinja2 渲染 + WeasyPrint PDF 导出
│   ├── formation.py            ← SVG 阵型图生成器
│   └── template.html           ← 报告 HTML/CSS 模板
│
├── assets/
│   └── league_logos/           ← （可选）联赛 Logo 静态资源
│
└── cache/
    └── teams_cache.json        ← 自动生成的球队 URL 缓存（运行后创建）
```

---

## 环境要求

- **Python**: 3.10 或以上
- **操作系统**: macOS / Linux / Windows（WeasyPrint PDF 在 Windows 上需要额外配置）

---

## 安装步骤

### 第一步：创建虚拟环境（推荐）

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 第二步：安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 第三步：安装 WeasyPrint 系统依赖（PDF 功能需要）

**macOS：**
```bash
brew install pango
```

**Ubuntu / Debian：**
```bash
sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0
```

**Windows：**  
参考 [WeasyPrint 官方 Windows 安装指南](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows)

> ⚠️ **注意**: 如果 WeasyPrint 安装遇到困难，PDF 导出功能可以暂时跳过。  
> App 提供 HTML 下载，用浏览器打开后直接 `Ctrl+P` 打印成 PDF 效果完全相同。

### 第四步：启动应用

```bash
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`

---

## 使用说明

### Sidebar（左侧控制面板）

1. **Your club name** — 填入你所在俱乐部名称，会显示在报告标题上（默认：Gillingham）
2. **League** — 选择联赛（支持英超、英冠、英甲、英乙、西甲、德甲、意甲、法甲）
3. **Home team / Away team** — 选择主客队。第一次选择某联赛时会自动抓取球队列表并缓存
4. **Match date** — 比赛日期，显示在报告上
5. **Formation** — 手动选择两队阵型（用于报告中的阵型示意图）
6. **Last 5 games** — 手动为每队选择近5场比赛结果（W/D/L），显示为彩色圆点
7. **Player(s) of interest** — 自由文本，填写需要重点关注的球员，会出现在报告对应板块
8. **Fetch data** 按钮 — 触发数据抓取（约需10-30秒，含延迟以避免被识别为爬虫）

### 主界面 Tabs

| Tab | 内容 |
|---|---|
| 📋 Squad overview | 双队完整阵容表，支持排序/过滤，可下载 CSV 和 XLSX |
| 📅 Contract watch | 夏季合同到期球员对比 |
| 🔄 Loan players | 租借球员及来源俱乐部 |
| 📄 Pre scout report | 点击"Generate report"生成报告预览，可下载 HTML 或 PDF |

---

## 各文件详细说明

### `app.py` — 主程序

Streamlit App 的唯一入口文件。负责：
- 整体页面布局（Sidebar + Main area + 4个 Tabs）
- Session state 管理（缓存已抓取的球队数据，避免重复请求）
- 调用 `scraper` 和 `report` 模块
- 交互式表格展示（优先使用 AgGrid，回退至原生 `st.dataframe`）
- 导出按钮（CSV / XLSX / HTML / PDF）

**关键设计**：
- `st.session_state` 存储抓取结果，切换 Tab 不会重新请求
- Sidebar 的 "↻" 按钮强制刷新球队列表缓存
- PDF 生成是懒加载的，只有点击"Generate PDF"按钮后才调用 WeasyPrint

---

### `scraper/leagues.py` — 联赛抓取

管理8个联赛的入口 URL，以及联赛页面 → 球队列表的抓取逻辑。

**核心函数**：
- `get_league_names()` — 返回支持的联赛名称列表
- `get_teams(league, force_refresh)` — 返回 `{球队名: {kader_url, crest_url}}` 字典
- `_fetch_teams_from_page(url)` — 抓取联赛页面的 `table.items`，提取球队链接和队徽

**缓存机制**：
- 首次抓取后保存至 `cache/teams_cache.json`
- 24小时内再次打开 App 直接读缓存，不重复请求
- Sidebar 的 "↻" 按钮传入 `force_refresh=True` 强制刷新

---

### `scraper/team.py` — 球队阵容抓取

基于你原始 notebook 代码改造，核心逻辑完全保留并优化封装。

**核心函数**：
- `scrape_team(kader_url)` — 主入口，返回包含4个 DataFrame 和元数据的字典
- `_scrape_kader(url)` — 抓取 `/kader/` 页面，提取球员姓名、位置、年龄、合同日期、合同类型（含租借信息）、队徽
- `_scrape_minutes(url)` — 抓取 `/leistungsdaten/` 页面，提取上场时间，去重处理
- `_extract_from_club(contract_type)` — 从合同类型字符串中解析租借来源俱乐部

**返回结构**：
```python
{
    "full_df":   DataFrame,  # 完整阵容（所有球员）
    "summer_df": DataFrame,  # 夏季合同到期（2026年5-8月，不含租借）
    "loan_df":   DataFrame,  # 租借球员
    "team_name": str,        # 球队名称
    "crest_url": str,        # 队徽图片 URL
    "error":     str | None, # 错误信息（正常为 None）
}
```

**Anti-scraping 处理**：
- 两次 HTTP 请求之间随机延迟 2-4 秒
- 模拟 Chrome 120 的 User-Agent 和 Accept-Language 请求头

---

### `report/formation.py` — 阵型图生成

纯 Python SVG 生成，不依赖任何外部图形库。

**核心函数**：
- `formation_svg(formation_str, width, height)` — 返回 SVG 字符串
- `formation_svg_base64(formation_str)` — 返回 Base64 Data URI，可直接嵌入 HTML `<img src="...">`

**预设阵型**（`FORMATIONS` 字典）：
`4-4-2`, `4-3-3`, `4-2-3-1`, `4-1-4-1`, `3-5-2`, `3-4-3`, `5-3-2`, `4-5-1`

对于字典中没有的阵型，会自动解析格式字符串（如 `3-4-2-1`）动态生成。

---

### `report/generator.py` — 报告生成器

**核心函数**：
- `render_html(...)` — 接收所有报告数据，用 Jinja2 渲染 `template.html`，返回 HTML 字符串
- `render_pdf(html)` — 将 HTML 字符串传给 WeasyPrint，返回 PDF bytes

`render_html` 接收的参数：

| 参数 | 类型 | 说明 |
|---|---|---|
| `owner_club` | str | 报告归属俱乐部名称 |
| `home_team` / `away_team` | str | 主客队名称 |
| `league` | str | 联赛名称 |
| `match_date` | str | 比赛日期字符串 |
| `home/away_formation` | str | 阵型字符串 |
| `home/away_l5g` | list | 近5场结果，如 `['w','w','d','l','w']` |
| `home/away_crest_url` | str | 队徽图片 URL |
| `home/away_summer_df` | DataFrame | 到期合同球员数据 |
| `home/away_loan_df` | DataFrame | 租借球员数据 |
| `home/away_poi` | str | 重点关注球员文字描述 |

---

### `report/template.html` — 报告模板

纯 HTML + CSS 模板，深蓝色主题，复原附件中的报告视觉风格。

**页面结构**：
```
┌─────────────────────────────────────────┐
│  俱乐部名称 + Pre Scout Report 标题     │
├─────────────────────────────────────────┤
│  [阵型图][主队队徽] V [客队队徽][阵型图] │
│  Last 5 Games 彩色圆点                  │
│  比赛日期 + 联赛名称                    │
├──────────────┬──────────────────────────┤
│ 主队          │ 客队                    │
│ Player(s) of  │ Player(s) of            │
│ Interest      │ Interest                │
│               │                         │
│ Out of        │ Out of                  │
│ Contract 表格 │ Contract 表格           │
│               │                         │
│ On Loan 表格  │ On Loan 表格            │
├─────────────────────────────────────────┤
│  Footer: 生成时间 + 数据来源            │
└─────────────────────────────────────────┘
```

颜色编码：
- `dot-w` → 绿色 (#22c55e) — 胜
- `dot-d` → 黄色 (#f59e0b) — 平
- `dot-l` → 红色 (#ef4444) — 负

---

## 依赖说明

| 库 | 用途 | 是否必须 |
|---|---|---|
| `streamlit` | Web UI 框架 | ✅ 必须 |
| `requests` | HTTP 请求 | ✅ 必须 |
| `beautifulsoup4` | HTML 解析 | ✅ 必须 |
| `pandas` | 数据处理 | ✅ 必须 |
| `openpyxl` | XLSX 导出 | ✅ 必须 |
| `jinja2` | HTML 模板渲染 | ✅ 必须 |
| `lxml` | BeautifulSoup 解析器 | ✅ 推荐 |
| `streamlit-aggrid` | 交互式表格 | ⚠️ 可选（无则回退到原生表格）|
| `weasyprint` | HTML → PDF 转换 | ⚠️ 可选（无则只能下载 HTML）|

---

## 常见问题

**Q: 抓取数据时报错 `403 Forbidden`？**  
A: Transfermarkt 对频繁请求有保护机制。等待几分钟后重试，或考虑更换 IP。

**Q: AgGrid 安装失败？**  
A: `pip install streamlit-aggrid` 可能需要特定版本。失败时 App 会自动使用原生 `st.dataframe`，功能正常，只是少了列过滤功能。

**Q: PDF 生成时报错 `OSError: no library called "libgobject-2.0-0"`？**  
A: WeasyPrint 缺少系统依赖，按照上方"安装 WeasyPrint 系统依赖"步骤安装 Pango。

**Q: 球队列表为空？**  
A: 网络连接问题或 Transfermarkt 页面结构变化。点击 Sidebar 的 "↻" 按钮强制重新抓取。

**Q: 想修改报告样式怎么办？**  
A: 直接编辑 `report/template.html`，所有颜色和布局都在该文件的 `<style>` 块中，修改后重新点击"Generate report"即可生效。

---

## 后续可扩展的功能方向

- **球员档案页**：点击表格中的球员姓名，抓取并展示该球员的 `/profil/spieler/` 详情页
- **多球队对比**：同一联赛中选择 2-3 支球队，对比夏季到期球员的位置分布
- **赛季切换**：修改 URL 中的 `saison_id` 参数，回溯历史赛季数据
- **近期比赛数据**：抓取 Transfermarkt 的比赛结果页面，自动填充 Last 5 Games
- **数据可视化**：添加年龄分布直方图、位置分布饼图等图表

---

---

# Part 2: English Documentation

## Project Overview

**Transfermarkt Scout Platform** is a Streamlit-based football data dashboard that scrapes [Transfermarkt](https://www.transfermarkt.co.uk) to collect squad information from the top European leagues and automatically generates downloadable **Pre Scout Reports**.

### Key Features

| Module | Description |
|---|---|
| League & Team Selection | 8 leagues supported, auto-fetches team list with 24h local cache |
| Squad Overview | Full squad table for both teams with sortable/filterable columns |
| Contract Watch | Players whose contracts expire in summer 2026 (loans excluded) |
| Loan Players | Active loan players with parent club information |
| Pre Scout Report | Two-column scouting report with HTML preview and PDF download |

---

## Project Structure

```
scout_platform/
│
├── app.py                      ← Streamlit main entry point
├── requirements.txt            ← Python dependencies
├── README.md                   ← Quick-start guide
├── PROJECT_GUIDE.md            ← This file (full documentation)
│
├── scraper/                    ← Data scraping module
│   ├── __init__.py
│   ├── leagues.py              ← League page scraper + team URL cache
│   └── team.py                 ← Squad page scraper (core crawler)
│
├── report/                     ← Report generation module
│   ├── __init__.py
│   ├── generator.py            ← Jinja2 rendering + WeasyPrint PDF export
│   ├── formation.py            ← SVG formation diagram generator
│   └── template.html           ← Report HTML/CSS template
│
├── assets/
│   └── league_logos/           ← (optional) local league logo images
│
└── cache/
    └── teams_cache.json        ← Auto-generated team URL cache (created at runtime)
```

---

## Requirements

- **Python**: 3.10 or higher
- **OS**: macOS / Linux / Windows (WeasyPrint PDF requires extra steps on Windows)

---

## Installation

### Step 1: Create a virtual environment (recommended)

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### Step 2: Install Python dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Install WeasyPrint system dependencies (required for PDF export)

**macOS:**
```bash
brew install pango
```

**Ubuntu / Debian:**
```bash
sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0
```

**Windows:**  
See the [WeasyPrint Windows installation guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows).

> ⚠️ **Note**: If WeasyPrint installation is problematic, PDF export can be skipped.  
> The app provides an HTML download — open it in any browser and print (`Ctrl+P`) to get an equivalent PDF.

### Step 4: Launch the app

```bash
streamlit run app.py
```

The browser will automatically open `http://localhost:8501`.

---

## Usage

### Sidebar Controls

1. **Your club name** — Club name shown in the report header (default: Gillingham)
2. **League** — Select from 8 supported leagues
3. **Home / Away team** — Select the two teams. The team list is fetched on first use and cached
4. **Match date** — Displayed on the report
5. **Formation** — Manually select each team's formation (used for the SVG diagram in the report)
6. **Last 5 games** — Manually select W/D/L for each of the last 5 games; rendered as coloured dots
7. **Player(s) of interest** — Free text field for notable players; appears in the report
8. **Fetch data** button — Triggers scraping (takes ~10–30 seconds including anti-scraping delay)

### Main Area Tabs

| Tab | Content |
|---|---|
| 📋 Squad overview | Full squad for both teams; sortable, filterable, downloadable as CSV/XLSX |
| 📅 Contract watch | Summer 2026 expiring contracts compared side by side |
| 🔄 Loan players | Active loan players and their parent clubs |
| 📄 Pre scout report | Click "Generate report" for live preview; download as HTML or PDF |

---

## Module Reference

### `scraper/leagues.py`

Manages entry URLs for 8 leagues and the logic to scrape team listings.

- `get_league_names()` — Returns list of supported league names
- `get_teams(league, force_refresh)` — Returns `{team_name: {kader_url, crest_url}}`
- Cache stored in `cache/teams_cache.json`, valid for 24 hours

### `scraper/team.py`

Core scraper, migrated and improved from the original notebook.

- `scrape_team(kader_url)` — Main entry point, returns dict with 4 DataFrames + metadata
- Scrapes both `/kader/` (squad) and `/leistungsdaten/` (playing time) pages
- Random 2–4 second delay between requests to avoid detection

### `report/formation.py`

Pure-Python SVG formation diagram generator (no external graphics libraries).

- `formation_svg(formation_str)` — Returns raw SVG string
- `formation_svg_base64(formation_str)` — Returns Base64 Data URI for HTML embedding
- Preset formations: `4-4-2`, `4-3-3`, `4-2-3-1`, `4-1-4-1`, `3-5-2`, `3-4-3`, `5-3-2`, `4-5-1`
- Unknown formations are parsed dynamically from the string

### `report/generator.py`

- `render_html(...)` — Renders the Jinja2 template with all match data, returns HTML string
- `render_pdf(html)` — Converts HTML string to PDF bytes via WeasyPrint

### `report/template.html`

HTML + CSS template reproducing the dark-blue two-column scouting report format.  
Edit the `<style>` block to customise colours, fonts, or layout.

---

## Dependencies

| Package | Purpose | Required |
|---|---|---|
| `streamlit` | Web UI framework | ✅ Yes |
| `requests` | HTTP requests | ✅ Yes |
| `beautifulsoup4` | HTML parsing | ✅ Yes |
| `pandas` | Data manipulation | ✅ Yes |
| `openpyxl` | XLSX export | ✅ Yes |
| `jinja2` | HTML template rendering | ✅ Yes |
| `lxml` | Fast BS4 parser | ✅ Recommended |
| `streamlit-aggrid` | Interactive grid tables | ⚠️ Optional (falls back to `st.dataframe`) |
| `weasyprint` | HTML → PDF conversion | ⚠️ Optional (HTML download still works without it) |

---

## Troubleshooting

**`403 Forbidden` when scraping?**  
Transfermarkt rate-limits aggressive crawlers. Wait a few minutes and retry, or try from a different network.

**`streamlit-aggrid` install fails?**  
The app gracefully falls back to the native `st.dataframe`. Install is optional.

**WeasyPrint `OSError: no library called "libgobject-2.0-0"`?**  
Install the Pango system library as described in Step 3 above.

**Team list is empty?**  
Network issue or Transfermarkt page structure changed. Click the "↻" button in the sidebar to force a fresh fetch.

**Want to change the report style?**  
Edit `report/template.html` directly. All colours and layout are defined in the `<style>` block. Click "Generate / refresh report" to see changes immediately.

---

## Potential Future Enhancements

- **Player profile page**: Click a player row to scrape and display their `/profil/spieler/` page (market value, transfer history, nationality)
- **Multi-team comparison**: Compare summer expiry structures across 2–3 teams in the same league
- **Season selector**: Change `saison_id` in the URL to browse historical seasons
- **Auto Last 5 Games**: Scrape Transfermarkt's fixture result pages to fill in W/D/L automatically
- **Data visualisations**: Age distribution histograms, position distribution pie charts, minutes vs contract expiry scatter plots

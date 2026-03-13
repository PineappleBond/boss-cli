# boss-cli

[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue.svg)](https://pypi.org/project/boss-cli/)

A CLI for BOSS 直聘 — search jobs, view recommendations, manage applications, and chat with recruiters via reverse-engineered API 🤝

[English](#features) | [中文](#功能特性)

## More Tools

- [xiaohongshu-cli](https://github.com/jackwener/xiaohongshu-cli) — Xiaohongshu CLI for notes, search, and interactions
- [bilibili-cli](https://github.com/jackwener/bilibili-cli) — Bilibili CLI for videos, users, and search
- [twitter-cli](https://github.com/jackwener/twitter-cli) — Twitter/X CLI for timelines, bookmarks, and posting
- [discord-cli](https://github.com/jackwener/discord-cli) — Discord CLI for local-first sync, search, and export

## Features

- 🔐 **Auth** — auto-extract browser cookies, QR code login (Unicode half-block rendering), status check
- 🔍 **Search** — jobs by keyword with city/salary/experience/degree filters
- ⭐ **Recommendations** — personalized job recommendations based on profile
- 👤 **Profile** — view personal info, resume status
- 📮 **Applications** — view applied jobs list
- 📋 **Interviews** — view interview invitations
- 💬 **Chat** — view communicated boss list
- 🤝 **Greet** — send greetings to recruiters, single or batch
- 🏙️ **Cities** — 40+ supported cities

## Installation

```bash
# From source
git clone git@github.com:jackwener/boss-cli.git
cd boss-cli
uv sync
```

## Usage

```bash
# ─── Auth ─────────────────────────────────────────
boss login                             # QR code login (scan with Boss app)
boss status                            # Check login status
boss logout                            # Clear saved cookies

# ─── Search ───────────────────────────────────────
boss search "golang"                   # Search jobs
boss search "Python" --city 杭州       # Filter by city
boss search "Java" --salary 20-30K     # Filter by salary
boss search "前端" --exp 3-5年          # Filter by experience
boss search "AI" --degree 硕士         # Filter by degree
boss search "后端" --city 深圳 -p 2    # Pagination

# ─── Recommendations ──────────────────────────────
boss recommend                         # View recommended jobs
boss recommend -p 2                    # Next page

# ─── Personal Center ─────────────────────────────
boss me                                # View profile
boss applied                           # View applied jobs
boss interviews                        # View interview invitations
boss chat                              # View communicated bosses

# ─── Greet ────────────────────────────────────────
boss greet <securityId>                # Send greeting to a boss
boss batch-greet "golang" --city 杭州 -n 5          # Batch greet top 5
boss batch-greet "Python" --salary 20-30K --dry-run  # Preview only

# ─── Utilities ────────────────────────────────────
boss cities                            # List supported cities
boss --version                         # Show version
```

## Authentication

boss-cli supports multiple authentication methods:

1. **Saved cookies** — loads from `~/.config/boss-cli/credential.json`
2. **Browser cookies** — auto-detects installed browsers and extracts cookies (supports Chrome, Firefox, Edge, Brave)
3. **QR code login** — terminal QR output using Unicode half-blocks, scan with Boss 直聘 APP

`boss login` triggers QR code login. Other authenticated commands automatically try saved cookies first, then browser extraction.

### Cookie TTL

Saved cookies warn after **7 days**. Re-login with `boss login` if API calls fail.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BOSS_CLI_CONFIG` | `~/.config/boss-cli` | Config directory path |

## Rate Limiting & Anti-Detection

- **Browser fingerprint**: macOS Chrome 133 User-Agent, `sec-ch-ua` headers
- **Batch greet delay**: 1.5s between greetings to avoid rate limiting
- **`__zp_stoken__` handling**: auto-detect expiry and prompt re-login

## Use as AI Agent Skill

boss-cli ships with a [`SKILL.md`](./SKILL.md) that teaches AI agents how to use it.

### Claude Code / Antigravity

```bash
mkdir -p .agents/skills
git clone git@github.com:jackwener/boss-cli.git .agents/skills/boss-cli
```

## Project Structure

```text
boss_cli/
├── __init__.py           # Package version
├── cli.py                # Click entry point (lightweight, add_command only)
├── client.py             # API client (rate-limit, retry, anti-detection)
├── auth.py               # Authentication (browser-cookie3, QR login)
├── constants.py          # URLs, headers, city codes, filter enums
├── exceptions.py         # Structured exceptions (BossApiError hierarchy)
└── commands/
    ├── __init__.py
    ├── _common.py        # handle_command, structured_output_options
    ├── auth.py           # login, logout, status, me
    ├── search.py         # search, recommend, cities
    ├── personal.py       # applied, interviews
    └── social.py         # chat, greet, batch-greet
```

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest tests/ -v

# Smoke tests (need cookies)
uv run pytest tests/ -v -m smoke

# Lint
uv run ruff check .
```

## Troubleshooting

**Q: `环境异常 (__zp_stoken__ 已过期)`**

Your session cookies have expired. Run `boss logout && boss login` to refresh.

**Q: `暂无投递记录` but I have applied**

Some features require fresh `__zp_stoken__`. Try re-logging in from a browser, then `boss login`.

**Q: Search returns no results**

Check your city filter. Some keywords are city-specific. Use `boss cities` to see available cities.

---

## 功能特性

- 🔐 **认证** — 自动提取浏览器 Cookie，二维码扫码登录（Unicode 半块渲染），状态检查
- 🔍 **搜索** — 按关键词搜索职位，支持城市/薪资/经验/学历筛选
- ⭐ **推荐** — 基于求职期望的个性化推荐
- 👤 **个人** — 查看个人资料
- 📮 **投递** — 查看已投递职位列表
- 📋 **面试** — 查看面试邀请
- 💬 **沟通** — 查看沟通过的 Boss 列表
- 🤝 **打招呼** — 向 Boss 打招呼/投递，支持批量操作
- 🏙️ **城市** — 40+ 城市支持

## 使用示例

```bash
# 认证
boss login                             # 二维码扫码登录
boss status                            # 检查登录状态
boss logout                            # 清除 Cookie

# 搜索
boss search "golang" --city 杭州       # 按城市搜索
boss search "Python" --salary 20-30K   # 按薪资筛选
boss search "前端" --exp 3-5年         # 按经验筛选

# 推荐
boss recommend                         # 个性化推荐

# 个人中心
boss me                                # 个人资料
boss applied                           # 已投递
boss interviews                        # 面试邀请
boss chat                              # 沟通列表

# 打招呼
boss greet <securityId>                # 单个打招呼
boss batch-greet "golang" -n 10        # 批量打招呼

# 工具
boss cities                            # 城市列表
```

## 常见问题

- `环境异常` — Cookie 过期，执行 `boss logout && boss login` 刷新
- 搜索无结果 — 检查城市筛选或关键词，使用 `boss cities` 查看支持的城市

## License

Apache-2.0

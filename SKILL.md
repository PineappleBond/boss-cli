---
name: boss-cli
description: Use boss-cli for ALL BOSS 直聘 operations — searching jobs, viewing recommendations, managing applications, chatting with recruiters, and batch greeting. Invoke whenever the user requests any job search or recruitment platform interaction on BOSS 直聘.
author: jackwener
version: "0.1.0"
tags:
  - boss
  - zhipin
  - boss直聘
  - job-search
  - recruitment
  - cli
---

# boss-cli — BOSS 直聘 CLI Tool

**Binary:** `boss`
**Credentials:** browser cookies (auto-extracted) or QR code login

## Setup

```bash
# Install (requires Python 3.10+)
git clone git@github.com:jackwener/boss-cli.git
cd boss-cli
uv sync
```

## Authentication

**IMPORTANT FOR AGENTS**: Before executing ANY boss command, check if credentials exist first.

### Step 0: Check if already authenticated

```bash
boss status 2>&1 | grep -q "已登录" && echo "AUTH_OK" || echo "AUTH_NEEDED"
```

If `AUTH_OK`, skip to [Command Reference](#command-reference).
If `AUTH_NEEDED`, guide user to login:

```bash
boss login                              # QR code login — scan with Boss app
```

### Step 1: Handle common auth issues

| Symptom | Agent action |
|---------|-------------|
| `环境异常 (__zp_stoken__ 已过期)` | Run `boss logout && boss login` |
| `未登录` | Run `boss login` |
| API timeout | Check network, retry |

## Command Reference

### Search & Browse

| Command | Description | Example |
|---------|-------------|---------|
| `boss search <keyword>` | Search jobs with filters | `boss search "golang" --city 杭州 --salary 20-30K` |
| `boss recommend` | Personalized recommendations | `boss recommend -p 2` |
| `boss cities` | List supported cities | `boss cities` |

### Personal Center

| Command | Description | Example |
|---------|-------------|---------|
| `boss me` | View profile (name, age, degree) | `boss me --json-output` |
| `boss applied` | View applied jobs | `boss applied -p 1` |
| `boss interviews` | View interview invitations | `boss interviews` |
| `boss chat` | View communicated bosses | `boss chat` |

### Actions

| Command | Description | Example |
|---------|-------------|---------|
| `boss greet <securityId>` | Greet a boss / apply | `boss greet abc123` |
| `boss batch-greet <keyword>` | Batch greet from search | `boss batch-greet "Python" --city 杭州 -n 5` |
| `boss batch-greet <keyword> --dry-run` | Preview without sending | `boss batch-greet "golang" --dry-run` |

### Account

| Command | Description |
|---------|-------------|
| `boss login` | QR code login (terminal QR output) |
| `boss status` | Check authentication status |
| `boss logout` | Clear saved credentials |

## Search Filter Options

| Filter | Flag | Values |
|--------|------|--------|
| City | `--city` | 北京, 上海, 杭州, 深圳, etc. (use `boss cities` for full list) |
| Salary | `--salary` | 3K以下, 3-5K, 5-10K, 10-15K, 15-20K, 20-30K, 30-50K, 50K以上 |
| Experience | `--exp` | 不限, 在校/应届, 1年以内, 1-3年, 3-5年, 5-10年, 10年以上 |
| Degree | `--degree` | 不限, 大专, 本科, 硕士, 博士 |

## Agent Workflow Examples

### Search → Batch Greet pipeline

```bash
# Preview first
boss batch-greet "golang" --city 杭州 --salary 20-30K --dry-run
# Then execute
boss batch-greet "golang" --city 杭州 --salary 20-30K -n 10 -y
```

### Daily job check workflow

```bash
boss recommend                         # Check recommendations
boss search "Python" --city 杭州       # Search specific jobs
boss applied                           # Check application status
boss interviews                        # Check interview invitations
boss chat                              # Check messages
```

### Profile check

```bash
boss me --json-output | jq '.name, .age, .degreeCategory'
```

## Limitations

- **No message sending** — cannot send chat messages (MQTT/Protobuf required)
- **No resume editing** — cannot edit resume from CLI
- **No company search** — company pages return HTML (need __zp_stoken__)
- **Single account** — one set of cookies at a time
- **Rate limited** — batch-greet has built-in 1.5s delay between greetings

## Anti-Detection Notes for Agents

- **Do NOT parallelize requests** — built-in delays exist for account safety
- **Batch greet limit**: recommend ≤ 10 greetings per session to avoid detection
- **Re-login if `__zp_stoken__` expires**: run `boss logout && boss login`
- **Respect rate limits**: the 1.5s delay in batch-greet is intentional

## Safety Notes

- Do not ask users to share raw cookie values in chat logs.
- Prefer local browser cookie extraction over manual secret copy/paste.
- If auth fails, ask the user to re-login via `boss login`.
- Agent should treat cookie values as secrets (do not echo to stdout).

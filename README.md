# Superset Devin Automation

This repo automates bug-fixing for [nehap29/superset](https://github.com/nehap29/superset).

It runs inside Docker on a schedule, checks for new GitHub issues, and hands each one to [Devin](https://devin.ai) to fix. Devin reads the issue, writes a fix, and opens a pull request — all without human intervention.

---

## What it does

Every hour (configurable), the automation:

1. **Scans** `nehap29/superset` for open GitHub issues.
2. **Skips** any issue it has already seen (tracked in a local JSON file).
3. **Creates a Devin session** for each new issue — Devin receives the issue title, description, and instructions to open a PR.
4. **Checks back** on sessions it started earlier and picks up status changes or PR links.
5. **Comments on the GitHub issue** with a link to the Devin session and, once available, the PR.
6. **Logs a summary** of all tracked issues and their statuses.

---

## How to run

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed
- A **GitHub personal access token** with `repo` scope ([create one here](https://github.com/settings/tokens))
- A **Devin API key** ([docs](https://docs.devin.ai/api-reference/overview))

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/nehap29/superset-devin-automation.git
cd superset-devin-automation

# 2. Create your config file
cp .env.example .env

# 3. Open .env and fill in your two keys:
#    GITHUB_TOKEN=ghp_...
#    DEVIN_API_KEY=...

# 4. Start the automation
docker compose up --build
```

It will scan immediately on startup, then repeat every hour. Logs print to the console.

### Run once (no loop)

If you just want a single scan instead of a continuous loop:

```bash
docker compose run --rm scanner once
```

### Run without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set env vars, then:
python -m src.main once   # single scan
python -m src.main        # continuous loop
```

---

## Configuration

Set these in your `.env` file. Only the first two are required.

| Variable | Required | Default | What it controls |
|----------|----------|---------|------------------|
| `GITHUB_TOKEN` | **yes** | — | GitHub token with `repo` scope |
| `DEVIN_API_KEY` | **yes** | — | Devin API key |
| `TARGET_REPO` | no | `nehap29/superset` | Which repo to scan for issues |
| `SCAN_INTERVAL_SECONDS` | no | `3600` | Seconds between scans (default: 1 hour) |
| `MAX_ACU_LIMIT` | no | `10` | Cost cap per Devin session (in ACUs) |
| `POST_STATUS_COMMENTS` | no | `true` | Whether to comment on GitHub issues |
| `ISSUE_LABELS` | no | _(all issues)_ | Only scan issues with these labels (comma-separated) |
| `LOG_LEVEL` | no | `INFO` | Python log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## Repo structure

```
superset-devin-automation/
├── src/
│   ├── main.py              # Entrypoint — runs the scan loop
│   ├── scanner.py           # Fetches open issues from GitHub
│   ├── session_manager.py   # Creates Devin sessions & polls their status
│   ├── state.py             # Tracks which issues already have sessions (JSON file)
│   ├── reporter.py          # Posts comments on GitHub issues & generates reports
│   └── config.py            # Reads configuration from environment variables
├── Dockerfile               # Builds the Python container
├── docker-compose.yml       # Runs the container with a persistent data volume
├── requirements.txt         # Python dependencies (just `requests`)
├── .env.example             # Template for your config — copy to .env
└── .gitignore
```

**Where to start reading:** `src/main.py` — it calls everything else in order.

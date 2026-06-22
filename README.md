# Superset Devin Automation

Dockerized automation that periodically scans open GitHub issues in
[nehap29/superset](https://github.com/nehap29/superset), creates a
[Devin](https://devin.ai) session for each new issue, and posts status updates
back on the issue as the session progresses.

## How it works

```
┌─────────────┐  scan   ┌─────────────┐  create   ┌─────────────┐
│  GitHub API  │◄───────│   Scanner    │─────────►│  Devin API   │
│  (issues)    │        │  (periodic)  │          │  (sessions)  │
└──────┬───────┘        └──────┬───────┘          └──────┬───────┘
       │                       │                         │
       │  comment              │  persist                │  poll
       ▼                       ▼                         ▼
  Issue gets           state.json            Session status/PR URL
  status update        (dedup)               fed back to reporter
```

Each cycle:

1. **Fetch** all open issues from the target repo via the GitHub API.
2. **Deduplicate** against a local JSON state file so each issue triggers at
   most one Devin session.
3. **Create** a Devin session per new issue with a prompt derived from the
   issue title and body.
4. **Poll** existing sessions for status changes (running → finished, PR
   created, etc.).
5. **Comment** on the GitHub issue with session links and PR URLs.
6. **Log** a Markdown summary report every cycle.

## Quick start

```bash
# 1. Clone
git clone https://github.com/nehap29/superset-devin-automation.git
cd superset-devin-automation

# 2. Configure
cp .env.example .env
# Edit .env — fill in GITHUB_TOKEN and DEVIN_API_KEY

# 3. Run with Docker Compose
docker compose up --build
```

### Run a single scan (no loop)

```bash
docker compose run --rm scanner once
```

## Configuration

All settings are read from environment variables (see `.env.example`):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | yes | — | GitHub personal access token with `repo` scope |
| `DEVIN_API_KEY` | yes | — | Devin API key |
| `TARGET_REPO` | no | `nehap29/superset` | Owner/repo to scan |
| `SCAN_INTERVAL_SECONDS` | no | `3600` | Seconds between scans |
| `MAX_ACU_LIMIT` | no | `10` | Max ACUs per Devin session |
| `POST_STATUS_COMMENTS` | no | `true` | Post comments on issues |
| `ISSUE_LABELS` | no | _(all)_ | Comma-separated label filter |
| `LOG_LEVEL` | no | `INFO` | Python log level |
| `STATE_FILE` | no | `/data/state.json` | Path to state persistence file |

## Project structure

```
src/
  config.py          — Environment-based configuration
  scanner.py         — GitHub issue fetcher
  session_manager.py — Devin API client (create & poll sessions)
  state.py           — JSON-backed dedup / tracking state
  reporter.py        — GitHub comment poster & report generator
  main.py            — Entrypoint (loop or one-shot mode)
Dockerfile
docker-compose.yml
.env.example
```

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Single scan (requires env vars)
python -m src.main once
```

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
6. **Logs a summary report** with system health, success rates, and per-issue status.

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
| `LOG_FORMAT` | no | `text` | `text` for human-readable, `json` for log aggregators |
| `METRICS_FILE` | no | `/data/metrics.json` | Path to cumulative metrics file |
| `REPORT_FILE` | no | `/data/report.md` | Path to the generated status report |

---

## Observability and monitoring

The automation is designed so an engineering leader can answer **"Is this working?"** at a glance.

### What gets tracked

Every scan cycle records:

| Metric | Description |
|--------|-------------|
| **Issues scanned** | How many open issues were found |
| **Sessions created** | How many new Devin sessions were started |
| **Sessions failed** | How many session-creation attempts failed |
| **Sessions polled** | How many in-progress sessions were checked |
| **Status changes** | How many sessions transitioned state (e.g., running → finished) |
| **Comments posted** | How many GitHub issue comments were posted |
| **Errors** | Any errors that occurred (with context) |
| **Cycle duration** | Wall-clock time for the full scan cycle |

### Where to find it

| Output | Location | Format |
|--------|----------|--------|
| **Console logs** | `docker compose logs -f` | Text or JSON (set `LOG_FORMAT=json`) |
| **Status report** | `/data/report.md` inside the container | Markdown with health table, outcomes, issue details, cycle history |
| **Metrics file** | `/data/metrics.json` inside the container | JSON with cumulative stats + last 50 cycles |
| **GitHub comments** | On each issue in the target repo | Markdown tables with session links and PR URLs |

### Reading the status report

The report (`/data/report.md`) has four sections:

1. **System Health** — total cycles, issues tracked, sessions created, success rate, average cycle duration, last scan time.
2. **Session Outcomes** — breakdown by status (`created`, `running`, `finished`, `errored`).
3. **Issue Details** — per-issue table with links to the GitHub issue, Devin session, and PR.
4. **Recent Cycle History** — last 10 cycles with timing and throughput.

### JSON logging for production

Set `LOG_FORMAT=json` to emit structured JSON logs (one object per line), ready for ingestion by log aggregators like Datadog, ELK, or CloudWatch:

```json
{"timestamp": "2026-06-22T00:15:00+00:00", "level": "INFO", "logger": "src.main", "message": "3 new issue(s) to process"}
```

---

## Repo structure

```
superset-devin-automation/
├── src/
│   ├── main.py              # Entrypoint — runs the scan loop
│   ├── config.py            # Environment-based configuration
│   ├── models.py            # Shared data models (Issue, SessionRecord)
│   ├── scanner.py           # Fetches open issues from GitHub
│   ├── session_manager.py   # Creates Devin sessions & polls their status
│   ├── state.py             # Tracks which issues already have sessions (JSON, atomic writes)
│   ├── reporter.py          # Posts GitHub comments & generates executive summary reports
│   ├── metrics.py           # Per-cycle and cumulative analytics tracking
│   ├── http_client.py       # Shared HTTP client with retry logic
│   └── logging_setup.py     # Configurable text/JSON logging
├── Dockerfile               # Python 3.12-slim container
├── docker-compose.yml       # Runs the container with a persistent data volume
├── requirements.txt         # Python dependencies (just `requests`)
├── .env.example             # Template — copy to .env and fill in keys
└── .gitignore
```

**Where to start reading:** `src/main.py` — it calls everything else in order.

### Module dependency graph

```
main.py
  ├── config.py          (env vars)
  ├── logging_setup.py   (log format)
  ├── metrics.py         (cycle tracking)
  ├── scanner.py         (GitHub issues)
  │     └── http_client.py
  ├── session_manager.py (Devin API)
  │     └── http_client.py
  ├── reporter.py        (comments + reports)
  │     ├── http_client.py
  │     └── metrics.py
  └── state.py           (persistence)
        └── models.py
```

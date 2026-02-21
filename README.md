# 🎯 Yard Goats Game Alert & Promotions Tracker

Automated alerts for Hartford Yard Goats home games — SMS + email, 5 days in advance, for a small group.

## Architecture

- **Scraper** (Python) — daily GitHub Actions cron, scrapes milb.com schedule + promotions → SQLite
- **Alert Engine** (Python) — daily GitHub Actions cron, sends SMS (Twilio) + email (SendGrid) for Fri/Sat/Sun games
- **Dashboard** (Next.js SSG) — static site deployed to Vercel, auto-rebuilt after each scrape
- **Database** — SQLite file committed to repo (`data/yardgoats.db`)
- **Scheduler** — GitHub Actions (free tier)

## One-Time Setup

### 1. Clone & initialize
```bash
git clone https://github.com/YOUR_USER/yardgoats-tracker.git
cd yardgoats-tracker
python3 admin/manage.py status   # initializes DB
```

### 2. Add recipients
```bash
python3 admin/manage.py add --name "You" --phone "+18605550001" --email "you@example.com"
python3 admin/manage.py add --name "Friend" --phone "+18605550002"
python3 admin/manage.py list
```

### 3. Set GitHub Actions Secrets
In your repo → Settings → Secrets and variables → Actions:

| Secret | Where to get it |
|--------|----------------|
| `TWILIO_ACCOUNT_SID` | twilio.com console |
| `TWILIO_AUTH_TOKEN` | twilio.com console |
| `TWILIO_FROM_NUMBER` | Twilio phone number (E.164) |
| `SENDGRID_API_KEY` | app.sendgrid.com → API Keys |
| `VERCEL_TOKEN` | vercel.com → Settings → Tokens |
| `VERCEL_ORG_ID` | Vercel project settings |
| `VERCEL_PROJECT_ID` | Vercel project settings |

### 4. Deploy dashboard to Vercel
```bash
cd dashboard && npm install && npm run build
# Then connect repo to Vercel via vercel.com UI
```

### 5. Enable GitHub Actions
Push to `main` — workflows activate automatically.

## Local Development

```bash
cp .env.example .env
# Fill in real values in .env

# Test scraper
python3 scraper/main.py

# Test alert engine (dry-run)
python3 alerts/main.py --dry-run

# Run tests
python3 tests/run_tests.py
```

## Recipient Management

```bash
python3 admin/manage.py add     --name "Name" --phone "+1..." --email "..."
python3 admin/manage.py list
python3 admin/manage.py list    --all          # includes inactive
python3 admin/manage.py remove  --id 3         # soft delete
python3 admin/manage.py restore --id 3
python3 admin/manage.py status
```

## Cost

| Service | Cost |
|---------|------|
| GitHub Actions | Free (public repo = unlimited minutes) |
| Vercel hosting | Free tier |
| SendGrid email | Free (100/day) |
| Twilio SMS | ~$0.008/msg ≈ $1.60/season for 5 people |
| **Total** | **~$1.60/season** |

## Repo Structure

```
yardgoats-tracker/
├── .github/workflows/     # Cron jobs
├── scraper/               # Schedule + promotions scraper
├── alerts/                # SMS + email notification engine
├── dashboard/             # Next.js static dashboard
├── admin/                 # Recipient management CLI
├── data/                  # yardgoats.db (SQLite)
├── tests/                 # Test suite
└── docs/                  # Project brief, PRD, architecture docs
```

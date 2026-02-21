# 🏛 Architecture Document — Yard Goats Tracker

## 1. Executive Summary

Automated alerts for Hartford Yard Goats home games (Fri/Sat/Sun) delivering SMS and email notifications 5 days in advance.

## 2. Technology Stack

- **Language**: Python 3.x
- **Database**: SQLite (Shared Persistence)
- **Scraping**: BeautifulSoup4 + Requests
- **Messaging**: Twilio (SMS) + SendGrid (Email)
- **Infrastructure**: GitHub Actions (Scheduler) + Vercel (Next.js Dashboard)

## 3. Architecture Pattern: Component-Based Monolith

The system consists of independent functional modules communicating through a shared database:

1. **Scraper (Ingestion)**: 
    - Fetches schedule from MLB Stats API.
    - Scrapes promotions from MilB.com.
    - Upserts state into SQLite.
2. **Alert Engine (Notification)**: 
    - Filters games based on a "5-day lead time" logic.
    - Targets specific "Home Game Weekend" criteria (Fri/Sat/Sun).
    - Ensures single-delivery through an audit table.
3. **Admin CLI (Management)**: 
    - Management interface for the recipient registry.
    - Database health and status checks.

## 4. Data Architecture

The system uses a single SQLite file (`yardgoats.db`) with four primary tables:
- `games`: Schedule registry.
- `promotions`: Linked promo data.
- `recipients`: Notification targets.
- `alerts_sent`: Audit log and deduplication registry.

## 5. Development Workflow

- **Local Setup**: Clone, `init_db`, and configure `.env`.
- **Testing**: Run `tests/run_tests.py` (mocked external dependencies).
- **Deployment**: Automatic via GitHub Actions cron jobs and Vercel CD.

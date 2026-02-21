# 🎯 Project Overview — Yard Goats Tracker

## 1. Project Purpose

Automated alerts for Hartford Yard Goats home games delivered via SMS and email 5 days in advance for a small group.

## 2. Key Features

- **Automated Scraper**: Daily fetch of MLB schedule and MilB promotions.
- **Alert Engine**: SMS and email notifications with a 5-day lead time.
- **Admin CLI**: Manage recipients and database status.
- **Dashboard**: Next.js-based static site for schedule visualization (planned).
- **Audit Logging**: Deduplication of alerts and delivery status tracking.

## 3. Technology Stack Summary

| Technology | Purpose |
| :--- | :--- |
| Python 3.x | Core Logic |
| SQLite | Persistence |
| BeautifulSoup4 | Scraping |
| Twilio | SMS Output |
| SendGrid | Email Output |
| GitHub Actions | Scheduler |
| Vercel | Hosting |

## 4. Documentation Links

- [Architecture](./architecture.md)
- [Source Tree Analysis](./source-tree-analysis.md)
- [Development Guide](./development-guide.md)

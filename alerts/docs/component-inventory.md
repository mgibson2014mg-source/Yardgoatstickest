# 🧩 Component Inventory — Yard Goats Tracker

## 1. Core Logic Components

### 1.1 Ingestion Components (`/scraper`)
- **Schedule Parser**: Interfaces with MLB Stats API; handles timezone and date normalization.
- **Promotion Scraper**: BeautifulSoup4-based HTML parser for milb.com; classifies promos into types.
- **DB Upsert Engine**: Manages SQLite transactions for data synchronization.

### 1.2 Notification Components (`/alerts`)
- **Lead-Time Filter**: Logic to identify games exactly 5 days out that meet weekend criteria.
- **Payload Builder**: Aggregates game and promotion data into user-friendly message objects.
- **Twilio Provider**: Wrapper for SMS delivery and mask-logging.
- **SendGrid Provider**: Wrapper for Email delivery with HTML template support.

### 1.3 Management Components (`/admin`)
- **Recipient Registry**: CLI-based CRUD operations for notification targets.
- **Migration Handler**: Basic SQLite schema initialization logic.

## 2. Infrastructure Components
- **GitHub Actions (Cron)**: 
    - `daily-scrape.yml`: Triggers ingestion.
    - `daily-alerts.yml`: Triggers notification delivery.
- **SQLite Database**: Local persistence layer for state management across cron runs.

## 3. UI Components (Planned)
- **Dashboard (Next.js)**: Static site components for visualizing the upcoming home stand and active promotions.

# 🌳 Source Tree Analysis — Yard Goats Tracker

## Directory Structure

```
yardgoats-tracker/
├── admin/               # Recipient & Database Management CLI
│   ├── db.py            # SQLite helper functions (CRUD operations)
│   └── manage.py        # CLI entry point for adding/listing recipients
├── alerts/              # Notification Engine (SMS + Email)
│   ├── email_sender.py  # SendGrid integration & HTML templates
│   ├── engine.py        # Alert logic (filtering, payload building)
│   ├── main.py          # Alert service entry point
│   └── sms.py           # Twilio integration
├── dashboard/           # (Placeholder) Next.js static dashboard
├── data/                # Data Persistence
│   └── schema.sql       # SQLite schema definitions
├── docs/                # Project documentation
├── scraper/             # Schedule & Promotions Scraper
│   ├── main.py          # Scraper service entry point
│   ├── promotions.py    # MilB.com promotions scraper (BeautifulSoup)
│   └── schedule.py      # MLB Stats API client
├── tests/               # Unit Test Suite
│   ├── run_tests.py     # Test runner
│   ├── test_alerts.py   # Alert engine tests (mocked)
│   └── test_scraper.py  # Scraper & Parser tests
└── README.md            # Primary project documentation
```

## Critical Files & Entry Points

- **`scraper/main.py`**: Entry point for the daily scrape job.
- **`alerts/main.py`**: Entry point for the daily alert delivery.
- **`admin/manage.py`**: Management CLI for recipients and DB status.
- **`data/schema.sql`**: Definitive source for the SQLite database structure.
- **`tests/run_tests.py`**: Centralized test execution script.

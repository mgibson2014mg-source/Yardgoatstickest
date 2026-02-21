# 🎯 Project Documentation Index — Yard Goats Tracker

## Project Overview

- **Type**: Multi-part Monolith (Python Backend + Data Persistence)
- **Primary Language**: Python 3.x
- **Architecture**: Component-Based Monolith (Shared SQLite)

## Quick Reference

- **Tech Stack**: Python, SQLite, BeautifulSoup, Twilio, SendGrid
- **Entry Points**: 
    - `scraper/main.py` (Daily Scrape)
    - `alerts/main.py` (Daily Notifications)
    - `admin/manage.py` (Registry CLI)
- **Architecture Pattern**: Shared Persistence (SQLite)

## Generated Documentation

- [Project Overview](./project-overview.md)
- [Architecture](./architecture.md)
- [Source Tree Analysis](./source-tree-analysis.md)
- [Development Guide](./development-guide.md)
- [API Contracts](./api-contracts.md)
- [Data Models](./data-models.md)
- [Component Inventory](./component-inventory.md) _(Dashboard placeholder)_

## Existing Documentation

- [README](../README.md) - Project overview, architecture, and setup instructions.

## Getting Started

1. Follow the [Development Guide](./development-guide.md) to set up your local environment.
2. Run `python admin/manage.py status` to initialize the database.
3. Configure your `.env` with Twilio and SendGrid credentials.
4. Execute `python tests/run_tests.py` to verify the installation.

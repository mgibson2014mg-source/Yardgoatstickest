# 🛠 Development Guide — Yard Goats Tracker

## 1. Local Setup

### 1.1 Prerequisites
- Python 3.8+
- SQLite3
- Twilio & SendGrid accounts (for full integration)

### 1.2 Installation
```bash
git clone https://github.com/YOUR_USER/yardgoats-tracker.git
cd yardgoats-tracker
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
# Install dependencies
pip install requests beautifulsoup4 twilio sendgrid
```

### 1.3 Environment Configuration
Copy `.env.example` to `.env` and fill in your API credentials:
```bash
cp .env.example .env
```

### 1.4 Initialize Database
```bash
python admin/manage.py status
```

## 2. Development Commands

### 2.1 Management CLI
- **List Recipients**: `python admin/manage.py list`
- **Add Recipient**: `python admin/manage.py add --name "Name" --phone "+1..." --email "..."`
- **Check Status**: `python admin/manage.py status`

### 2.2 Scraper
- **Run Scraper**: `python scraper/main.py`
- **Dry Run**: `python scraper/main.py --dry-run`

### 2.3 Alert Engine
- **Run Alerts**: `python alerts/main.py`
- **Dry Run**: `python alerts/main.py --dry-run`

## 3. Testing
Execute the full test suite:
```bash
python tests/run_tests.py
```

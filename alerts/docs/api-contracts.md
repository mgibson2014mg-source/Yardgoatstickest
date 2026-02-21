# 🔌 API Contracts — Yard Goats Tracker

## 1. Internal Python API

### 1.1 Scraper (`scraper/db.py`)
| Function | Parameters | Description |
| :--- | :--- | :--- |
| `init_db()` | None | Initializes the SQLite database and creates tables from `schema.sql`. |
| `get_conn()` | None | Returns a row-factory enabled SQLite connection object. |
| `upsert_game()` | `conn, game_dict` | Inserts or updates a game record based on `game_date`. |
| `upsert_promotions()` | `conn, game_id, promo_list` | Replaces all promotions for a specific game ID. |

### 1.2 Alert Engine (`alerts/engine.py`)
| Function | Parameters | Description |
| :--- | :--- | :--- |
| `get_qualifying_games()` | `conn, target_date` | Filters for home games on Fri/Sat/Sun for the given date. |
| `build_alert_payload()` | `game_row` | Constructs a flattened dictionary of game and promotion data. |
| `check_data_freshness()` | `conn` | Validates that the `games` table has been updated recently. |

## 2. CLI Interface (`admin/manage.py`)

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `add` | `--name, --phone, --email` | Adds a new recipient to the registry. |
| `list` | `--all` | Lists active (or all) recipients in the database. |
| `remove` | `--id` | Soft-deletes a recipient by setting `active=0`. |
| `status` | None | Checks database connectivity and initializes if missing. |

## 3. External Integrations
- **MLB Stats API**: `https://statsapi.mlb.com/api/v1/schedule`
- **MilB Promotions**: `https://www.milb.com/hartford/tickets/promotions`

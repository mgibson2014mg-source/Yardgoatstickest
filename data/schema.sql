-- Yard Goats Tracker — SQLite Schema v1.0
-- Per Architecture Doc Section 3.4

CREATE TABLE IF NOT EXISTS games (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    game_date   DATE NOT NULL UNIQUE,
    day_of_week TEXT NOT NULL,
    start_time  TEXT,
    opponent    TEXT NOT NULL,
    is_home     BOOLEAN NOT NULL DEFAULT 1,
    ticket_url  TEXT,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS promotions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    promo_type  TEXT NOT NULL CHECK(promo_type IN ('giveaway','fireworks','discount','theme','heritage','special')),
    description TEXT,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipients (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    phone   TEXT,
    email   TEXT,
    active  BOOLEAN NOT NULL DEFAULT 1,
    CHECK (phone IS NOT NULL OR email IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS alerts_sent (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id      INTEGER NOT NULL REFERENCES games(id),
    recipient_id INTEGER NOT NULL REFERENCES recipients(id),
    channel      TEXT NOT NULL CHECK(channel IN ('sms','email')),
    sent_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status       TEXT NOT NULL CHECK(status IN ('delivered','failed','pending')),
    UNIQUE(game_id, recipient_id, channel)
);

CREATE INDEX IF NOT EXISTS idx_games_date ON games(game_date);
CREATE INDEX IF NOT EXISTS idx_games_dow  ON games(day_of_week);
CREATE INDEX IF NOT EXISTS idx_promos_game ON promotions(game_id);
CREATE INDEX IF NOT EXISTS idx_alerts_game ON alerts_sent(game_id);

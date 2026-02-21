# 📊 Data Models — Yard Goats Tracker

## 1. Entity Relationship Diagram (Conceptual)
`games` (1) ── < (N) `promotions`
`games` (1) ── < (N) `alerts_sent` > ── (1) `recipients`

## 2. Table Definitions

### 2.1 `games`
Primary registry for all scheduled home and away games.
- `id`: Integer (PK)
- `game_date`: Date (Unique Index)
- `day_of_week`: Text (e.g., 'Friday')
- `opponent`: Text
- `is_home`: Boolean (1 = Home Game)
- `ticket_url`: Text (Nullable)

### 2.2 `promotions`
Detailed promotion information parsed from the MilB website.
- `id`: Integer (PK)
- `game_id`: Integer (FK -> games.id)
- `promo_type`: Enum ('giveaway', 'fireworks', 'discount', etc.)
- `description`: Text (e.g., 'Los Chivos Jersey Giveaway')

### 2.3 `recipients`
Notification registry for SMS and email targets.
- `id`: Integer (PK)
- `name`: Text
- `phone`: Text (E.164 format)
- `email`: Text
- `active`: Boolean (Default: 1)

### 2.4 `alerts_sent`
Audit log to track delivery status and prevent duplicate notifications.
- `id`: Integer (PK)
- `game_id`: Integer (FK)
- `recipient_id`: Integer (FK)
- `channel`: Enum ('sms', 'email')
- `sent_at`: Timestamp
- `status`: Enum ('delivered', 'failed', 'pending')

import Database from 'better-sqlite3';
import path from 'path';

const dbPath = path.resolve(process.cwd(), '..', 'data', 'yardgoats.db');

export const db = new Database(dbPath, {
  readonly: true,
  fileMustExist: true,
});

export interface Game {
  id: number;
  game_date: string;
  day_of_week: string;
  start_time: string;
  opponent: string;
  is_home: number;
  ticket_url: string;
  updated_at: string;
  promotions: Promotion[];
}

export interface Promotion {
  id: number;
  game_id: number;
  promo_type: string;
  description: string;
}

export function getUpcomingGames(): Game[] {
  const games = db.prepare('SELECT * FROM games WHERE is_home = 1 ORDER BY game_date ASC').all() as Omit<Game, 'promotions'>[];
  
  const gamesWithPromos: Game[] = games.map((game) => {
    const promotions = db.prepare('SELECT * FROM promotions WHERE game_id = ?').all(game.id) as Promotion[];
    return { ...game, promotions };
  });

  return gamesWithPromos;
}

export function getSyncStatus() {
  const row = db.prepare('SELECT MAX(updated_at) as last_update FROM games').get() as { last_update: string };
  return row?.last_update || null;
}

export function getAdminStats() {
  const totalRecipients = db.prepare('SELECT COUNT(*) as count FROM recipients').get() as { count: number };
  const activeRecipients = db.prepare('SELECT COUNT(*) as count FROM recipients WHERE active = 1').get() as { count: number };
  const totalGames = db.prepare('SELECT COUNT(*) as count FROM games').get() as { count: number };
  const totalPromos = db.prepare('SELECT COUNT(*) as count FROM promotions').get() as { count: number };

  return {
    recipients: {
      total: totalRecipients.count,
      active: activeRecipients.count,
    },
    database: {
      games: totalGames.count,
      promotions: totalPromos.count,
      status: 'Connected',
    },
  };
}

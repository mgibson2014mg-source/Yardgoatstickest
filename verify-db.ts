import { getUpcomingGames, getSyncStatus } from './src/lib/db';

try {
  console.log('Verifying Database Connection...');
  const games = getUpcomingGames();
  const lastSync = getSyncStatus();

  console.log('--- DB STATS ---');
  console.log('Total Games Found:', games.length);
  console.log('Last Sync Time:', lastSync);

  if (games.length > 0) {
    console.log('--- SAMPLE GAME ---');
    console.log(JSON.stringify(games[0], null, 2));
  } else {
    console.log('No home games found in DB.');
  }

  console.log('--- VERIFICATION SUCCESSFUL ---');
} catch (error) {
  console.error('--- VERIFICATION FAILED ---');
  console.error(error);
  process.exit(1);
}

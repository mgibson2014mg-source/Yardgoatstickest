import { NextResponse } from 'next/server';
import { getUpcomingGames, getSyncStatus } from '@/lib/db';
import { getHartfordForecast, matchWeatherForGame } from '@/lib/weather';

export async function GET() {
  try {
    const games = getUpcomingGames();
    const lastSync = getSyncStatus();
    
    // Fetch latest forecast
    const forecast = await getHartfordForecast();

    // Attach weather to each game if available
    const gamesWithWeather = games.map((game) => {
      const weather = matchWeatherForGame(forecast, game.game_date, game.start_time);
      return { ...game, weather };
    });

    return NextResponse.json({
      success: true,
      data: gamesWithWeather,
      lastSync,
    });
  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to fetch game data' },
      { status: 500 }
    );
  }
}

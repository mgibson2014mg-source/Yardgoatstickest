export interface WeatherData {
  temp: number;
  precipitation_prob: number;
}

let weatherCache: { data: any; timestamp: number } | null = null;
const CACHE_DURATION = 60 * 60 * 1000; // 1 hour

export async function getHartfordForecast() {
  const now = Date.now();
  if (weatherCache && (now - weatherCache.timestamp < CACHE_DURATION)) {
    return weatherCache.data;
  }

  try {
    const lat = 41.7637;
    const lon = -72.6851;
    const response = await fetch(
      `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&hourly=temperature_2m,precipitation_probability&temperature_unit=fahrenheit&timezone=America%2FNew_York`
    );
    const data = await response.json();
    
    weatherCache = { data, timestamp: now };
    return data;
  } catch (error) {
    console.error('Weather API Error:', error);
    return null;
  }
}

export function matchWeatherForGame(forecast: any, gameDate: string, startTime: string): WeatherData | null {
  if (!forecast || !forecast.hourly) return null;

  // Start time format from DB is typically "7:05 PM"
  // We need to convert this to an hour (e.g., 19)
  const hourMatch = startTime.match(/(\d+):/);
  if (!hourMatch) return null;
  
  let hour = parseInt(hourMatch[1]);
  const isPM = startTime.toLowerCase().includes('pm');
  if (isPM && hour !== 12) hour += 12;
  if (!isPM && hour === 12) hour = 0;

  // Format targets: "2026-04-10T19:00"
  const targetIso = `${gameDate}T${hour.toString().padStart(2, '0')}:00`;

  const index = forecast.hourly.time.findIndex((t: string) => t.startsWith(targetIso));
  
  if (index !== -1) {
    return {
      temp: forecast.hourly.temperature_2m[index],
      precipitation_prob: forecast.hourly.precipitation_probability[index],
    };
  }

  return null;
}

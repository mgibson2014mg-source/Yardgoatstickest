import React from 'react';
import { PromoBadge } from './PromoBadge';
import { ShareButton } from './ShareButton';
import { WeatherBadge } from './WeatherBadge';
import { PerfectDayBadge } from './PerfectDayBadge';

interface Promotion {
  id: number;
  promo_type: string;
  description: string;
}

interface WeatherData {
  temp: number;
  precipitation_prob: number;
}

interface GameCardProps {
  id: number;
  date: string;
  day: string;
  time: string;
  opponent: string;
  ticketUrl: string;
  promotions: Promotion[];
  weather?: WeatherData | null;
}

export const GameCard: React.FC<GameCardProps> = ({ id, date, day, time, opponent, ticketUrl, promotions, weather }) => {
  const hasHighValuePromo = promotions.some(p => 
    p.description.toLowerCase().includes('jersey') || 
    p.promo_type.toLowerCase().includes('fireworks')
  );

  const isPerfectDay = weather && 
    weather.temp >= 70 && 
    weather.temp <= 80 && 
    weather.precipitation_prob < 10;

  const mainPromo = promotions[0]?.description || 'Yard Goats Game';
  const btnColor = hasHighValuePromo ? 'bg-[#009933] hover:bg-[#007722]' : 'bg-[#003366] hover:bg-[#002244]';

  return (
    <div className="w-full bg-white border border-slate-100 rounded-[32px] p-6 shadow-sm mb-4 relative overflow-hidden">
      {isPerfectDay && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10">
          <PerfectDayBadge />
        </div>
      )}
      
      <div className="flex justify-between items-start mb-4">
        <div>
          <p className="text-[#003366] font-black text-sm uppercase tracking-wider">{day}</p>
          <h3 className="text-2xl font-black text-slate-900">{date}</h3>
        </div>
        <div className="flex flex-col items-end">
          <ShareButton 
            gameId={id} 
            date={date} 
            opponent={opponent} 
            promoDescription={mainPromo} 
          />
          <div className="text-right mt-2">
            <p className="text-slate-500 text-xs font-bold uppercase tracking-tighter">Start Time</p>
            <p className="text-lg font-black text-slate-900">{time}</p>
          </div>
        </div>
      </div>

      <div className="mb-6 flex justify-between items-center">
        <p className="text-slate-400 text-xs font-bold uppercase mb-1 italic">vs. {opponent}</p>
        {weather && (
          <WeatherBadge temp={weather.temp} precipitationProb={weather.precipitation_prob} />
        )}
      </div>

      <div className="flex flex-wrap gap-2 mb-8">
        {promotions.length > 0 ? (
          promotions.map((promo) => (
            <PromoBadge key={promo.id} type={promo.promo_type} description={promo.description} />
          ))
        ) : (
          <div className="px-3 py-1.5 bg-slate-50 text-slate-400 rounded-full border border-slate-100">
            <p className="text-[10px] font-bold uppercase tracking-widest italic">Promotions TBD</p>
          </div>
        )}
      </div>

      <a
        href={ticketUrl}
        target="_blank"
        rel="noopener noreferrer"
        className={`block w-full py-4 ${btnColor} text-white text-center rounded-2xl font-black text-sm tracking-widest transition-all active:scale-95 shadow-lg`}
      >
        GET TICKETS
      </a>
    </div>
  );
};

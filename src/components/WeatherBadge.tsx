'use client';

import React, { useState } from 'react';
import { CloudRain, Flame, Info } from 'lucide-react';

interface WeatherBadgeProps {
  temp: number;
  precipitationProb: number;
}

export const WeatherBadge: React.FC<WeatherBadgeProps> = ({ temp, precipitationProb }) => {
  const [showDetails, setShowDetails] = useState(false);
  
  const isRainRisk = precipitationProb > 40;
  const isHeatRisk = temp > 90;

  if (!isRainRisk && !isHeatRisk) return null;

  const config = isRainRisk 
    ? {
        bgColor: 'bg-blue-100',
        textColor: 'text-blue-800',
        icon: <CloudRain size={14} />,
        label: `Risk: Rain (${precipitationProb}%)`,
      }
    : {
        bgColor: 'bg-orange-100',
        textColor: 'text-orange-800',
        icon: <Flame size={14} />,
        label: `Extreme Heat (${Math.round(temp)}°)`,
      };

  return (
    <div className="relative">
      <button
        onClick={() => setShowDetails(!showDetails)}
        className={`flex items-center space-x-2 px-3 py-1.5 rounded-full ${config.bgColor} ${config.textColor} transition-all active:scale-95 shadow-sm`}
      >
        <span className="flex-shrink-0">{config.icon}</span>
        <span className="text-[10px] font-black uppercase tracking-tighter whitespace-nowrap">
          {config.label}
        </span>
        <Info size={10} className="opacity-50" />
      </button>

      {showDetails && (
        <div className="absolute bottom-full left-0 mb-2 p-3 bg-white border border-slate-100 rounded-2xl shadow-xl z-20 min-w-[180px] animate-in fade-in slide-in-from-bottom-2">
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 border-b border-slate-50 pb-1">
            Game Time Forecast
          </p>
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-slate-500 font-medium">Temperature:</span>
              <span className="text-slate-900 font-black">{Math.round(temp)}°F</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-500 font-medium">Precipitation:</span>
              <span className="text-slate-900 font-black">{precipitationProb}%</span>
            </div>
          </div>
          <button 
            onClick={(e) => { e.stopPropagation(); setShowDetails(false); }}
            className="mt-3 w-full py-1 text-[8px] font-black text-slate-400 uppercase tracking-tighter hover:text-slate-600"
          >
            Close
          </button>
        </div>
      )}
    </div>
  );
};

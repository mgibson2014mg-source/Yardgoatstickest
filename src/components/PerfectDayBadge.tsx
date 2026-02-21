import React from 'react';

export const PerfectDayBadge: React.FC = () => {
  return (
    <div className="flex items-center space-x-1 px-3 py-1 bg-[#009933] text-white rounded-full shadow-lg border border-white/20 animate-in fade-in zoom-in duration-500">
      <span className="text-sm">⚾</span>
      <span className="text-[10px] font-black uppercase tracking-tighter whitespace-nowrap">
        Perfect Day
      </span>
    </div>
  );
};

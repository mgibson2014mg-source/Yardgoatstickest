import React from 'react';

interface PromoBadgeProps {
  type: string;
  description: string;
}

export const PromoBadge: React.FC<PromoBadgeProps> = ({ type, description }) => {
  const isJersey = description.toLowerCase().includes('jersey');
  const isFireworks = type.toLowerCase().includes('fireworks') || description.toLowerCase().includes('fireworks');
  
  let bgColor = 'bg-slate-100';
  let textColor = 'text-slate-700';
  let icon = '⚾';
  let animation = '';

  if (isJersey) {
    bgColor = 'bg-[#FFD700]'; // Jersey Gold
    textColor = 'text-black';
    icon = '🎁';
    animation = 'animate-pulse shadow-[0_0_15px_rgba(255,215,0,0.5)]';
  } else if (isFireworks) {
    bgColor = 'bg-[#00FFCC]'; // Fireworks Neon
    textColor = 'text-black';
    icon = '🎆';
  } else if (type.toLowerCase() === 'giveaway') {
    bgColor = 'bg-blue-50';
    textColor = 'text-blue-700';
    icon = '🎁';
  }

  return (
    <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full ${bgColor} ${textColor} ${animation} transition-all duration-500`}>
      <span className="text-sm">{icon}</span>
      <span className="text-[10px] font-black uppercase tracking-tighter whitespace-nowrap">
        {isJersey ? 'Jersey Giveaway' : description}
      </span>
    </div>
  );
};

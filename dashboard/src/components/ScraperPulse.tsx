'use client';

import React from 'react';
import { CheckCircle2, AlertCircle, XCircle } from 'lucide-react';

interface ScraperPulseProps {
  lastSync: string | null;
}

export const ScraperPulse: React.FC<ScraperPulseProps> = ({ lastSync }) => {
  if (!lastSync) {
    return (
      <div className="flex items-center space-x-2 text-slate-400">
        <XCircle size={20} />
        <span className="text-sm font-black uppercase tracking-tighter">No Data</span>
      </div>
    );
  }

  const syncDate = new Date(lastSync);
  const now = new Date();
  const diffHours = (now.getTime() - syncDate.getTime()) / (1000 * 60 * 60);

  let status = {
    label: 'Healthy',
    icon: <CheckCircle2 size={20} className="text-green-500" />,
    textColor: 'text-green-600',
    bgColor: 'bg-green-50',
  };

  if (diffHours > 48) {
    status = {
      label: 'Stale',
      icon: <XCircle size={20} className="text-red-500" />,
      textColor: 'text-red-600',
      bgColor: 'bg-red-50',
    };
  } else if (diffHours > 24) {
    status = {
      label: 'Delayed',
      icon: <AlertCircle size={20} className="text-amber-500" />,
      textColor: 'text-amber-600',
      bgColor: 'bg-amber-50',
    };
  }

  return (
    <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-xl ${status.bgColor} border border-white/50 shadow-inner`}>
      {status.icon}
      <span className={`text-[10px] font-black uppercase tracking-widest ${status.textColor}`}>
        {status.label}
      </span>
    </div>
  );
};

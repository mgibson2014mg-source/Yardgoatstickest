'use client';

import React, { useEffect, useState } from 'react';

interface SyncStatusProps {
  lastSync: string | null;
}

export const SyncStatus: React.FC<SyncStatusProps> = ({ lastSync }) => {
  const [isStale, setIsStale] = useState(false);
  const [formattedDate, setFormattedDate] = useState<string>('Never');

  useEffect(() => {
    if (!lastSync) return;

    const syncDate = new Date(lastSync);
    const now = new Date();
    const diffHours = (now.getTime() - syncDate.getTime()) / (1000 * 60 * 60);

    setIsStale(diffHours > 48);
    setFormattedDate(syncDate.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    }));
  }, [lastSync]);

  const statusColor = isStale ? 'bg-amber-500' : 'bg-green-500 animate-pulse';
  const statusText = isStale ? 'Sync Stale' : 'Live Sync';

  return (
    <div className="flex items-center space-x-2 px-3 py-1 bg-slate-50 rounded-full border border-slate-100">
      <div className={`w-2 h-2 rounded-full ${statusColor}`} title={statusText}></div>
      <p className="text-[10px] font-black uppercase tracking-tighter text-slate-500">
        Last Scrape: <span className="text-slate-900">{formattedDate}</span>
      </p>
    </div>
  );
};

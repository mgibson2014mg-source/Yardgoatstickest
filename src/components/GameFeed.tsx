'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { GameCard } from './GameCard';
import { SyncStatus } from './SyncStatus';

interface Game {
  id: number;
  game_date: string;
  day_of_week: string;
  start_time: string;
  opponent: string;
  ticket_url: string;
  promotions: any[];
  weather?: { temp: number; precipitation_prob: number } | null;
}

export const GameFeed = () => {
  const [games, setGames] = useState<Game[]>([]);
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  const lastSyncRef = useRef<string | null>(null);

  const fetchGames = useCallback(async (isAutoRefresh = false) => {
    try {
      if (isAutoRefresh) setIsRefreshing(true);
      
      const response = await fetch('/api/games');
      const result = await response.json();
      
      if (result.success) {
        // Only update state if data has actually changed to prevent unnecessary re-renders
        if (result.lastSync !== lastSyncRef.current) {
          setGames(result.data);
          setLastSync(result.lastSync);
          lastSyncRef.current = result.lastSync;
        }
      } else {
        if (!isAutoRefresh) setError('Failed to load games');
      }
    } catch (err) {
      if (!isAutoRefresh) setError('Error connecting to API');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  // Initial Load
  useEffect(() => {
    fetchGames();
  }, [fetchGames]);

  // Polling Loop (NFR2: Refresh every 60 seconds)
  useEffect(() => {
    const interval = setInterval(() => {
      // Only poll if the tab is active to save resources
      if (document.visibilityState === 'visible') {
        fetchGames(true);
      }
    }, 60000);

    return () => clearInterval(interval);
  }, [fetchGames]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="mt-4 text-slate-500 font-bold uppercase tracking-tighter text-xs animate-pulse">
          Scouting Home Stands...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 text-red-600 rounded-[32px] border border-red-100 text-center mx-4 mt-8">
        <p className="font-bold uppercase tracking-tighter">Connection Error</p>
        <p className="text-sm opacity-80">{error}</p>
        <button 
          onClick={() => fetchGames()}
          className="mt-4 px-6 py-2 bg-red-600 text-white rounded-full font-black text-xs uppercase"
        >
          Retry Sync
        </button>
      </div>
    );
  }

  return (
    <div className="w-full max-w-2xl mx-auto px-4 py-8">
      <div className="mb-8 flex flex-col items-center">
        <SyncStatus lastSync={lastSync} />
        {isRefreshing && (
          <p className="text-[8px] font-black text-blue-500 uppercase mt-2 tracking-widest animate-pulse">
            Syncing Real-Time...
          </p>
        )}
      </div>

      <div className="space-y-4">
        {games.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-slate-400 italic">No upcoming home games found. Check back later!</p>
          </div>
        ) : (
          games.map((game, index) => (
            <div 
              key={`${game.id}-${lastSync}`} 
              className="animate-in slide-in-from-top-4 fade-in duration-700 fill-mode-both"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <GameCard
                id={game.id}
                date={game.game_date}
                day={game.day_of_week}
                time={game.start_time}
                opponent={game.opponent}
                ticketUrl={game.ticket_url}
                promotions={game.promotions}
                weather={game.weather}
              />
            </div>
          ))
        )}
      </div>
    </div>
  );
};

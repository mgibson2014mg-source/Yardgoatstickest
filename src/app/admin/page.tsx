'use client';

import React, { useEffect, useState } from 'react';
import { ShieldCheck, Database, Users, Activity, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { ScraperPulse } from '@/components/ScraperPulse';

export default function AdminPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('/api/admin/stats');
        const result = await response.json();
        if (result.success) {
          setData(result);
        } else {
          setError(result.error || 'Unauthorized');
        }
      } catch (err) {
        setError('Connection failed');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) return <div className="p-12 text-center font-black animate-pulse uppercase tracking-widest text-slate-400">Loading System Metrics...</div>;

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-slate-50">
        <div className="bg-white p-8 rounded-[32px] shadow-xl border border-red-100 text-center max-w-sm">
          <ShieldCheck size={48} className="mx-auto text-red-500 mb-4" />
          <h1 className="text-xl font-black text-slate-900 uppercase mb-2">Access Denied</h1>
          <p className="text-sm text-slate-500 mb-6">{error === 'Unauthorized' ? 'Admin key missing or invalid.' : error}</p>
          <Link href="/" className="px-6 py-3 bg-slate-900 text-white rounded-2xl font-bold text-xs uppercase">Return Home</Link>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        <header className="flex justify-between items-center mb-12">
          <div>
            <h1 className="text-3xl font-black text-[#003366] uppercase tracking-tighter">System Health</h1>
            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">Operational Cockpit</p>
          </div>
          <Link href="/" className="flex items-center space-x-2 text-slate-400 hover:text-slate-900 transition-colors">
            <ArrowLeft size={16} />
            <span className="text-xs font-black uppercase">Dashboard</span>
          </Link>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {/* Database Card */}
          <div className="bg-white p-6 rounded-[32px] border border-slate-100 shadow-sm">
            <div className="flex justify-between items-start mb-4">
              <div className="p-3 bg-blue-50 text-blue-600 rounded-2xl">
                <Database size={24} />
              </div>
              <span className="px-2 py-1 bg-green-100 text-green-700 text-[8px] font-black uppercase rounded">Connected</span>
            </div>
            <h2 className="text-sm font-black text-slate-400 uppercase mb-1">Persistence</h2>
            <p className="text-2xl font-black text-slate-900">{data.stats.database.games} Games</p>
            <p className="text-xs font-bold text-slate-500 mt-1">{data.stats.database.promotions} Promotions</p>
          </div>

          {/* Recipients Card */}
          <div className="bg-white p-6 rounded-[32px] border border-slate-100 shadow-sm">
            <div className="flex justify-between items-start mb-4">
              <div className="p-3 bg-green-50 text-green-600 rounded-2xl">
                <Users size={24} />
              </div>
            </div>
            <h2 className="text-sm font-black text-slate-400 uppercase mb-1">Reach</h2>
            <p className="text-2xl font-black text-slate-900">{data.stats.recipients.active} Active</p>
            <p className="text-xs font-bold text-slate-500 mt-1">{data.stats.recipients.total} Total Recipients</p>
          </div>

          {/* Scraper Card */}
          <div className="bg-white p-6 rounded-[32px] border border-slate-100 shadow-sm">
            <div className="flex justify-between items-start mb-4">
              <div className="p-3 bg-purple-50 text-purple-600 rounded-2xl">
                <Activity size={24} />
              </div>
              <ScraperPulse lastSync={data.lastSync} />
            </div>
            <h2 className="text-sm font-black text-slate-400 uppercase mb-1">Scraper Pulse</h2>
            <p className="text-sm font-black text-slate-900 leading-tight">
              {data.lastSync ? new Date(data.lastSync).toLocaleString() : 'Never'}
            </p>
            <p className="text-xs font-bold text-slate-500 mt-1">Last Data Ingestion</p>
          </div>
        </div>

        <div className="bg-white p-8 rounded-[32px] border border-slate-100 shadow-sm">
          <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">Environment Info</h3>
          <pre className="bg-slate-50 p-4 rounded-2xl text-[10px] text-slate-600 overflow-x-auto">
{`Platform: Vercel / Next.js
Engine: better-sqlite3 (Read-Only)
Source: ../data/yardgoats.db
Status: Healthy`}
          </pre>
        </div>
      </div>
    </main>
  );
}

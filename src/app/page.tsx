import { GameFeed } from '@/components/GameFeed';
import Link from 'next/link';
import { Bell } from 'lucide-react';

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-100 py-6 px-4 md:px-8 flex items-center justify-between sticky top-0 z-10 shadow-sm">
        <div className="flex-1"></div>
        <div className="text-center flex-1">
          <h1 className="text-2xl font-black text-[#003366] tracking-tighter uppercase leading-none">
            Yard Goats Tracker
          </h1>
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">
            Intelligence Hub
          </p>
        </div>
        <div className="flex-1 flex justify-end">
          <Link 
            href="/signup" 
            className="flex items-center space-x-2 bg-blue-50 text-[#003366] px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest hover:bg-blue-100 transition-all border border-blue-100 shadow-sm"
          >
            <Bell size={14} />
            <span className="hidden md:inline">Join Alerts</span>
          </Link>
        </div>
      </header>

      <div className="container mx-auto">
        <GameFeed />
      </div>

      <footer className="py-12 text-center border-t border-slate-100 bg-white">
        <p className="text-xs text-slate-400 font-bold uppercase tracking-widest">
          Created with AI — BMad Master
        </p>
      </footer>
    </main>
  );
}

import { GameFeed } from '@/components/GameFeed';

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-100 py-6 px-4 text-center sticky top-0 z-10 shadow-sm">
        <h1 className="text-2xl font-black text-[#003366] tracking-tighter uppercase">
          Yard Goats Tracker
        </h1>
        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">
          Intelligence Hub
        </p>
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

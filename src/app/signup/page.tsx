'use client';

import React, { useState } from 'react';
import { Bell, ArrowLeft, Send, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';

export default function SignupPage() {
  const [formData, setFormData] = useState({ name: '', phone: '', email: '' });
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || (!formData.phone && !formData.email)) {
      setStatus('error');
      setMessage('Name and at least one contact method (Phone or Email) are required.');
      return;
    }

    setStatus('loading');
    try {
      const res = await fetch('/api/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      const data = await res.json();
      if (data.success) {
        setStatus('success');
      } else {
        setStatus('error');
        setMessage(data.error || 'Failed to sign up. Please try again.');
      }
    } catch (err) {
      setStatus('error');
      setMessage('Network error. Please check your connection.');
    }
  };

  if (status === 'success') {
    return (
      <main className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="bg-white p-8 md:p-12 rounded-[40px] shadow-2xl border border-slate-100 text-center max-w-md w-full">
          <div className="w-20 h-20 bg-green-50 text-green-500 rounded-3xl flex items-center justify-center mx-auto mb-6">
            <CheckCircle2 size={40} />
          </div>
          <h1 className="text-3xl font-black text-slate-900 uppercase tracking-tighter mb-4">You're In!</h1>
          <p className="text-slate-500 font-medium mb-8 leading-relaxed">
            We've received your request. Our automated system is now updating the alert registry. 
            You'll be active in about 60 seconds!
          </p>
          <Link href="/" className="inline-flex items-center space-x-2 px-8 py-4 bg-slate-900 text-white rounded-2xl font-black text-sm uppercase tracking-widest hover:bg-slate-800 transition-all shadow-lg shadow-slate-200">
            <span>Back to Dashboard</span>
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 p-4 md:p-8 flex flex-col items-center justify-center">
      <div className="w-full max-w-lg">
        <Link href="/" className="inline-flex items-center space-x-2 text-slate-400 hover:text-slate-900 transition-colors mb-8 group">
          <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
          <span className="text-xs font-black uppercase tracking-widest">Back to Dashboard</span>
        </Link>

        <div className="bg-white p-8 md:p-12 rounded-[48px] shadow-2xl border border-slate-100">
          <header className="mb-10 text-center">
            <div className="inline-flex p-4 bg-blue-50 text-[#003366] rounded-3xl mb-6">
              <Bell size={32} />
            </div>
            <h1 className="text-4xl font-black text-[#003366] uppercase tracking-tighter leading-none mb-2">Join the Alerts</h1>
            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Get notified 5 days before home games</p>
          </header>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 ml-1">Your Name</label>
              <input
                type="text"
                required
                placeholder="e.g. Hartford Fan"
                className="w-full px-6 py-4 bg-slate-50 border-2 border-transparent focus:border-blue-100 focus:bg-white rounded-2xl outline-none transition-all font-bold text-slate-900 placeholder:text-slate-300"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 ml-1">SMS (Phone)</label>
                <input
                  type="tel"
                  placeholder="+1860..."
                  className="w-full px-6 py-4 bg-slate-50 border-2 border-transparent focus:border-blue-100 focus:bg-white rounded-2xl outline-none transition-all font-bold text-slate-900 placeholder:text-slate-300"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 ml-1">Email Address</label>
                <input
                  type="email"
                  placeholder="fan@example.com"
                  className="w-full px-6 py-4 bg-slate-50 border-2 border-transparent focus:border-blue-100 focus:bg-white rounded-2xl outline-none transition-all font-bold text-slate-900 placeholder:text-slate-300"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>
            </div>

            {status === 'error' && (
              <div className="p-4 bg-red-50 text-red-600 rounded-2xl text-xs font-bold text-center border border-red-100">
                {message}
              </div>
            )}

            <button
              type="submit"
              disabled={status === 'loading'}
              className="w-full py-5 bg-[#003366] text-white rounded-[24px] font-black text-sm uppercase tracking-widest shadow-xl shadow-blue-100 hover:bg-[#002244] hover:-translate-y-1 transition-all disabled:opacity-50 disabled:translate-y-0 flex items-center justify-center space-x-3"
            >
              {status === 'loading' ? (
                <span className="animate-pulse">Processing...</span>
              ) : (
                <>
                  <span>Initialize Signup</span>
                  <Send size={18} />
                </>
              )}
            </button>
          </form>

          <footer className="mt-10 pt-10 border-t border-slate-50 text-center">
            <p className="text-[9px] font-black text-slate-300 uppercase tracking-[0.2em] leading-relaxed">
              Automated Registry Update<br />
              Powered by GitHub Actions Persistence
            </p>
          </footer>
        </div>
      </div>
    </main>
  );
}

'use client';

import React, { useState, useEffect } from 'react';
import { Share2, Copy, Check } from 'lucide-react';

interface ShareButtonProps {
  gameId: number;
  date: string;
  opponent: string;
  promoDescription: string;
}

export const ShareButton: React.FC<ShareButtonProps> = ({ gameId, date, opponent, promoDescription }) => {
  const [copied, setCopied] = useState(false);
  const [canShare, setCanShare] = useState(false);

  useEffect(() => {
    setCanShare(!!navigator.share);
  }, []);

  const shareData = {
    title: 'Yard Goats Game Alert!',
    text: `${date}: ${opponent} @ Yard Goats - ${promoDescription}`,
    url: typeof window !== 'undefined' ? `${window.location.origin}${window.location.pathname}?game=${gameId}` : '',
  };

  const handleShare = async () => {
    if (canShare) {
      try {
        await navigator.share(shareData);
      } catch (err) {
        // User may have cancelled sharing, which is fine
        if ((err as Error).name !== 'AbortError') {
          console.error('Error sharing:', err);
        }
      }
    } else {
      try {
        await navigator.clipboard.writeText(shareData.url);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (err) {
        console.error('Error copying to clipboard:', err);
      }
    }
  };

  return (
    <button
      onClick={handleShare}
      className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-full transition-all active:scale-90"
      title={canShare ? "Share Game" : "Copy Link"}
    >
      {copied ? (
        <div className="flex items-center space-x-1">
          <Check size={18} className="text-green-500" />
          <span className="text-[10px] font-black uppercase text-green-500">Copied</span>
        </div>
      ) : (
        canShare ? <Share2 size={18} /> : <Copy size={18} />
      )}
    </button>
  );
};

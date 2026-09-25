'use client';

import { useState } from 'react';

type ConfirmationStrength = 'WEAK' | 'MODERATE' | 'STRONG' | 'VERY_STRONG';

export default function RCMCard() {
  const [score] = useState(0.78);
  const [confirmed] = useState(true);
  const [strength] = useState<ConfirmationStrength>('STRONG');

  const strengthConfig: Record<ConfirmationStrength, { color: string; bg: string }> = {
    WEAK: { color: 'text-gray-400', bg: 'bg-gray-700' },
    MODERATE: { color: 'text-amber-400', bg: 'bg-amber-900' },
    STRONG: { color: 'text-cyan-400', bg: 'bg-cyan-900' },
    VERY_STRONG: { color: 'text-emerald-400', bg: 'bg-emerald-900' },
  };

  const config = strengthConfig[strength];

  return (
    <div className="card">
      <div className="card-title">RCM - Rotation Confirmation Model</div>
      <div className="space-y-3">
        <div className={`${config.bg} rounded p-3 mb-4`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-300">Confirmation Status</span>
            <span className={`text-sm font-bold ${config.color}`}>
              {confirmed ? '✓ CONFIRMED' : '✗ UNCONFIRMED'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-400 text-xs">Strength</span>
            <span className={`text-xs font-mono ${config.color}`}>{strength}</span>
          </div>
        </div>

        <div className="flex items-center justify-between mb-3">
          <span className="text-gray-400">RCM Score</span>
          <span className="text-lg font-bold text-cyan-400">
            {(score * 100).toFixed(0)}/100
          </span>
        </div>

        {/* Components Grid */}
        <div className="space-y-2 text-xs">
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-gray-900 rounded p-2">
              <div className="text-gray-500 mb-1">Capital Flow</div>
              <div className="w-full bg-gray-700 rounded h-1.5 overflow-hidden">
                <div className="bg-cyan-500 h-full" style={{ width: '80%' }} />
              </div>
              <div className="text-cyan-400 font-mono text-xs mt-1">0.80</div>
            </div>
            <div className="bg-gray-900 rounded p-2">
              <div className="text-gray-500 mb-1">Rel. Strength</div>
              <div className="w-full bg-gray-700 rounded h-1.5 overflow-hidden">
                <div className="bg-purple-500 h-full" style={{ width: '75%' }} />
              </div>
              <div className="text-purple-400 font-mono text-xs mt-1">0.75</div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-gray-900 rounded p-2">
              <div className="text-gray-500 mb-1">Narrative Acc.</div>
              <div className="w-full bg-gray-700 rounded h-1.5 overflow-hidden">
                <div className="bg-emerald-500 h-full" style={{ width: '78%' }} />
              </div>
              <div className="text-emerald-400 font-mono text-xs mt-1">0.78</div>
            </div>
            <div className="bg-gray-900 rounded p-2">
              <div className="text-gray-500 mb-1">Fundamental</div>
              <div className="w-full bg-gray-700 rounded h-1.5 overflow-hidden">
                <div className="bg-amber-500 h-full" style={{ width: '72%' }} />
              </div>
              <div className="text-amber-400 font-mono text-xs mt-1">0.72</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

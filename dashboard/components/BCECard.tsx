'use client';

import { useState } from 'react';

export default function BCECard() {
  const [score] = useState(5);
  const maxScore = 6;
  const validated = score >= 5;

  return (
    <div className="card">
      <div className="card-title">Bottom Confirmation Engine (BCE)</div>
      <div className="space-y-3">
        <div className="flex items-center justify-between mb-4">
          <span className="text-gray-400">Confirmation Score</span>
          <span className={`text-lg font-bold ${validated ? 'text-emerald-400' : 'text-amber-400'}`}>
            {score}/{maxScore}
          </span>
        </div>

        {/* Score Bar */}
        <div className="space-y-2">
          <div className="flex gap-1">
            {Array.from({ length: maxScore }).map((_, i) => (
              <div
                key={i}
                className={`flex-1 h-2 rounded ${
                  i < score ? 'bg-emerald-400' : 'bg-gray-700'
                }`}
              />
            ))}
          </div>
          <div className="text-xs text-gray-500">
            {validated ? '✓ Entry Valid' : '⚠ Below Threshold'}
          </div>
        </div>

        {/* Components */}
        <div className="space-y-2 text-xs">
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-gray-900 rounded p-2">
              <div className="text-gray-500">Structure</div>
              <div className="text-cyan-400 font-mono">✓</div>
            </div>
            <div className="bg-gray-900 rounded p-2">
              <div className="text-gray-500">Volume</div>
              <div className="text-cyan-400 font-mono">✓</div>
            </div>
            <div className="bg-gray-900 rounded p-2">
              <div className="text-gray-500">Exhaustion</div>
              <div className="text-cyan-400 font-mono">✓</div>
            </div>
            <div className="bg-gray-900 rounded p-2">
              <div className="text-gray-500">Accumulation</div>
              <div className="text-cyan-400 font-mono">✓</div>
            </div>
            <div className="bg-gray-900 rounded p-2">
              <div className="text-gray-500">Market</div>
              <div className="text-cyan-400 font-mono">✓</div>
            </div>
            <div className="bg-gray-900 rounded p-2">
              <div className="text-gray-500">Momentum</div>
              <div className="text-amber-400 font-mono">→</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

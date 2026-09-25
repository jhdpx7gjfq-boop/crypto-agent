'use client';

import { useState } from 'react';

export default function X20Card() {
  const [score] = useState(0.72);
  const [fundamental] = useState(0.78);
  const [narrative] = useState(0.68);
  const [quantitative] = useState(0.70);

  const getScoreColor = (s: number) => {
    if (s >= 0.75) return 'text-emerald-400';
    if (s >= 0.50) return 'text-cyan-400';
    if (s >= 0.25) return 'text-amber-400';
    return 'text-red-400';
  };

  return (
    <div className="card">
      <div className="card-title">X20 Engine - Opportunity Detection</div>
      <div className="space-y-3">
        <div className="flex items-center justify-between mb-4">
          <span className="text-gray-400">Composite Score</span>
          <span className={`text-lg font-bold ${getScoreColor(score)}`}>
            {(score * 100).toFixed(0)}/100
          </span>
        </div>

        {/* Composite Progress */}
        <div className="bg-gray-900 rounded p-2">
          <div className="flex gap-1">
            {Array.from({ length: 10 }).map((_, i) => (
              <div
                key={i}
                className={`flex-1 h-1 rounded-sm ${
                  i < score * 10 ? 'bg-cyan-400' : 'bg-gray-700'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Dimensions */}
        <div className="space-y-2 text-xs">
          <div className="bg-gray-900 rounded p-3">
            <div className="flex justify-between mb-1">
              <span className="text-gray-500">Fundamental (35%)</span>
              <span className={`font-mono font-bold ${getScoreColor(fundamental)}`}>
                {(fundamental * 100).toFixed(0)}
              </span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-emerald-500 h-full"
                style={{ width: `${fundamental * 100}%` }}
              />
            </div>
          </div>

          <div className="bg-gray-900 rounded p-3">
            <div className="flex justify-between mb-1">
              <span className="text-gray-500">Narrative (35%)</span>
              <span className={`font-mono font-bold ${getScoreColor(narrative)}`}>
                {(narrative * 100).toFixed(0)}
              </span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-purple-500 h-full"
                style={{ width: `${narrative * 100}%` }}
              />
            </div>
          </div>

          <div className="bg-gray-900 rounded p-3">
            <div className="flex justify-between mb-1">
              <span className="text-gray-500">Quantitative (30%)</span>
              <span className={`font-mono font-bold ${getScoreColor(quantitative)}`}>
                {(quantitative * 100).toFixed(0)}
              </span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-cyan-500 h-full"
                style={{ width: `${quantitative * 100}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

'use client';

import { useState } from 'react';

type RevivalStage = 'DEAD' | 'STIRRING' | 'AWAKENING' | 'REVIVING';

export default function RRPCard() {
  const [stage] = useState<RevivalStage>('AWAKENING');
  const [score] = useState(0.64);
  const [dormancyDays] = useState(180);

  const stageConfig: Record<RevivalStage, { color: string; emoji: string; label: string }> = {
    DEAD: { color: 'text-gray-500', emoji: '⚰️', label: 'Dead' },
    STIRRING: { color: 'text-amber-400', emoji: '🌙', label: 'Stirring' },
    AWAKENING: { color: 'text-cyan-400', emoji: '🌅', label: 'Awakening' },
    REVIVING: { color: 'text-emerald-400', emoji: '🚀', label: 'Reviving' },
  };

  const config = stageConfig[stage];

  return (
    <div className="card">
      <div className="card-title">RRP - Revival Radar Pipeline</div>
      <div className="space-y-3">
        <div className="flex items-center justify-between mb-4">
          <span className="text-gray-400">Revival Stage</span>
          <div className="text-right">
            <div className={`text-2xl mb-1 text-center`}>{config.emoji}</div>
            <div className={`text-sm font-bold ${config.color}`}>
              {config.label}
            </div>
          </div>
        </div>

        {/* Score Gauge */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-500">Revival Score</span>
            <span className="text-cyan-400 font-mono font-bold">
              {(score * 100).toFixed(0)}/100
            </span>
          </div>
          <div className="relative h-3 bg-gradient-to-r from-gray-700 via-amber-700 to-emerald-700 rounded-full overflow-hidden">
            <div
              className="absolute top-0 left-0 h-full bg-white opacity-20 rounded-full"
              style={{ width: `${score * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-500">
            <span>Dead (0.30)</span>
            <span>Stirring</span>
            <span>Awakening</span>
            <span>Reviving (0.75)</span>
          </div>
        </div>

        {/* Metrics */}
        <div className="space-y-2 text-xs">
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-gray-900 rounded p-2">
              <div className="text-gray-500">Dormancy</div>
              <div className="text-cyan-400 font-mono">{dormancyDays}d</div>
            </div>
            <div className="bg-gray-900 rounded p-2">
              <div className="text-gray-500">Confidence</div>
              <div className="text-cyan-400 font-mono">78%</div>
            </div>
            <div className="bg-gray-900 rounded p-2">
              <div className="text-gray-500">Volume Spike</div>
              <div className="text-emerald-400 font-mono">2.4x</div>
            </div>
            <div className="bg-gray-900 rounded p-2">
              <div className="text-gray-500">Whale Activity</div>
              <div className="text-amber-400 font-mono">↗</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

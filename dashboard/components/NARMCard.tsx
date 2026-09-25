'use client';

import { useState } from 'react';

type RotationPhase = 'EMERGING' | 'ACCELERATING' | 'MATURE' | 'DECLINING';

export default function NARMCard() {
  const [score] = useState(72);
  const [phase] = useState<RotationPhase>('ACCELERATING');

  const phaseConfig: Record<RotationPhase, { color: string; range: string }> = {
    EMERGING: { color: 'text-blue-400', range: '0-25' },
    ACCELERATING: { color: 'text-emerald-400', range: '25-60' },
    MATURE: { color: 'text-amber-400', range: '60-85' },
    DECLINING: { color: 'text-red-400', range: '85-100' },
  };

  const config = phaseConfig[phase];

  return (
    <div className="card">
      <div className="card-title">NARM-P+ - Narrative Rotation</div>
      <div className="space-y-3">
        <div className="flex items-center justify-between mb-4">
          <span className="text-gray-400">Rotation Score</span>
          <div className="text-right">
            <div className={`text-lg font-bold ${config.color}`}>
              {score}/100
            </div>
            <div className="text-xs text-gray-500">{phase}</div>
          </div>
        </div>

        {/* Score Timeline */}
        <div className="space-y-2">
          <div className="relative h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              className="absolute h-full bg-gradient-to-r from-blue-500 via-emerald-500 via-amber-500 to-red-500"
              style={{ width: `${score}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-500">
            <span>Emerging</span>
            <span>Accelerating</span>
            <span>Mature</span>
            <span>Declining</span>
          </div>
        </div>

        {/* Components */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="bg-gray-900 rounded p-2">
            <div className="text-gray-500">Strength</div>
            <div className="text-cyan-400 font-mono">68%</div>
          </div>
          <div className="bg-gray-900 rounded p-2">
            <div className="text-gray-500">Adoption</div>
            <div className="text-cyan-400 font-mono">75%</div>
          </div>
          <div className="bg-gray-900 rounded p-2">
            <div className="text-gray-500">Rotation</div>
            <div className="text-emerald-400 font-mono">↗</div>
          </div>
          <div className="bg-gray-900 rounded p-2">
            <div className="text-gray-500">Fundamental</div>
            <div className="text-amber-400 font-mono">72%</div>
          </div>
        </div>
      </div>
    </div>
  );
}

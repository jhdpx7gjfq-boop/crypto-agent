'use client';

import { useState, useEffect } from 'react';

type RegimeType = 'RISK_ON' | 'RISK_OFF' | 'TRANSITIONAL';

export default function RegimeCard() {
  const [regime, setRegime] = useState<RegimeType>('RISK_ON');
  const [confidence, setConfidence] = useState(0.85);

  const regimeConfig: Record<RegimeType, { color: string; label: string }> = {
    RISK_ON: { color: 'text-emerald-400', label: 'Risk On' },
    RISK_OFF: { color: 'text-red-400', label: 'Risk Off' },
    TRANSITIONAL: { color: 'text-amber-400', label: 'Transitional' },
  };

  const config = regimeConfig[regime];

  return (
    <div className="card">
      <div className="card-title">Market Regime Detection</div>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-gray-400">Current Regime</span>
          <span className={`text-sm font-bold ${config.color}`}>
            {config.label}
          </span>
        </div>
        <div className="bg-gray-900 rounded p-2">
          <div className="text-xs text-gray-500 mb-1">Confidence</div>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-gray-700 rounded-full h-2 overflow-hidden">
              <div
                className="bg-gradient-to-r from-cyan-500 to-cyan-400 h-full"
                style={{ width: `${confidence * 100}%` }}
              />
            </div>
            <span className="text-xs font-mono">{(confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div className="bg-gray-900 rounded p-2 text-center">
            <div className="text-gray-500">DXY</div>
            <div className="font-mono">104.2</div>
          </div>
          <div className="bg-gray-900 rounded p-2 text-center">
            <div className="text-gray-500">US10Y</div>
            <div className="font-mono">4.3%</div>
          </div>
          <div className="bg-gray-900 rounded p-2 text-center">
            <div className="text-gray-500">BTC.D</div>
            <div className="font-mono">61.5%</div>
          </div>
        </div>
      </div>
    </div>
  );
}

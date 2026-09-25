'use client';

import { useEffect, useState } from 'react';
import RegimeCard from '@/components/RegimeCard';
import BCECard from '@/components/BCECard';
import X20Card from '@/components/X20Card';
import NARMCard from '@/components/NARMCard';
import RCMCard from '@/components/RCMCard';
import RRPCard from '@/components/RRPCard';
import AlertPanel from '@/components/AlertPanel';

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<string>('');

  useEffect(() => {
    setLoading(false);
    setLastUpdate(new Date().toLocaleTimeString());
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-xl text-cyan-400 mb-2">Loading Dashboard</div>
          <div className="text-xs text-gray-500">IGWT-PF26 Quant Intelligence OS</div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-3 py-4 sm:px-4 sm:py-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-lg sm:text-2xl font-bold text-cyan-400 mb-1">Quant Research Dashboard</h1>
        <div className="text-xs text-gray-500">
          Last update: {lastUpdate}
        </div>
      </div>

      {/* Alert Panel */}
      <div className="mb-6">
        <AlertPanel />
      </div>

      {/* Grid Layout - Mobile first */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Regime Detection */}
        <RegimeCard />

        {/* BCE Score */}
        <BCECard />
      </div>

      {/* Opportunity Detection */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* X20 Engine */}
        <X20Card />

        {/* NARM-P+ */}
        <NARMCard />
      </div>

      {/* Rotation Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* RCM Confirmation */}
        <RCMCard />

        {/* RRP Revival */}
        <RRPCard />
      </div>

      {/* Footer */}
      <div className="text-xs text-gray-600 border-t border-gray-700 pt-4 mt-8">
        <div>IGWT-PF26 — Quant Intelligence Operating System</div>
        <div>Layer 1-7: Data Intelligence • Regime Detection • Wyckoff/BCE • X20 • NARM-P+ • RCM/RPM • RRP</div>
      </div>
    </div>
  );
}

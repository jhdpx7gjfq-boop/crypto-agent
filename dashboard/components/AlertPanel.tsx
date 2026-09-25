'use client';

interface Alert {
  id: string;
  type: 'signal' | 'warning' | 'info' | 'opportunity';
  title: string;
  description: string;
  timestamp: string;
}

export default function AlertPanel() {
  const alerts: Alert[] = [
    {
      id: '1',
      type: 'opportunity',
      title: 'X20 Asymmetric Opportunity Detected',
      description: 'SOL showing strong opportunity profile: Fundamental 78%, Narrative 82%, Quant 75%',
      timestamp: '2 min ago',
    },
    {
      id: '2',
      type: 'signal',
      title: 'RCM Rotation Confirmed',
      description: 'Capital rotation from Large Cap to Alt narratives confirmed at 0.78 score',
      timestamp: '5 min ago',
    },
    {
      id: '3',
      type: 'warning',
      title: 'Regime Transition Risk',
      description: 'Market transitioning from RISK_ON to mixed signals. Monitor positioning.',
      timestamp: '12 min ago',
    },
  ];

  const typeConfig: Record<Alert['type'], { bg: string; border: string; icon: string }> = {
    signal: { bg: 'bg-cyan-900', border: 'border-cyan-700', icon: '📡' },
    warning: { bg: 'bg-amber-900', border: 'border-amber-700', icon: '⚠️' },
    info: { bg: 'bg-blue-900', border: 'border-blue-700', icon: 'ℹ️' },
    opportunity: { bg: 'bg-emerald-900', border: 'border-emerald-700', icon: '💎' },
  };

  return (
    <div className="space-y-2">
      <div className="text-sm font-semibold text-gray-200 px-1">Active Signals</div>
      <div className="space-y-2">
        {alerts.map((alert) => {
          const config = typeConfig[alert.type];
          return (
            <div
              key={alert.id}
              className={`${config.bg} border ${config.border} rounded-lg p-3 text-sm`}
            >
              <div className="flex items-start gap-3">
                <div className="text-lg flex-shrink-0">{config.icon}</div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-100 truncate">
                    {alert.title}
                  </div>
                  <div className="text-xs text-gray-300 mt-1">
                    {alert.description}
                  </div>
                  <div className="text-xs text-gray-500 mt-2">
                    {alert.timestamp}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

import React from 'react';

export function MetricStrip({ metrics = [], columns = 4, className = '' }) {
  const colClass = {
    2: 'grid-cols-2',
    3: 'grid-cols-2 sm:grid-cols-3',
    4: 'grid-cols-2 sm:grid-cols-4',
    5: 'grid-cols-2 sm:grid-cols-5',
    6: 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-6',
  }[columns] || 'grid-cols-2 sm:grid-cols-4';

  return (
    <div className={`grid ${colClass} gap-3 ${className}`}>
      {metrics.map((item, idx) => {
        const Icon = item.icon;
        return (
          <div
            key={idx}
            className={`bg-white border border-zinc-200/90 rounded-md p-3.5 shadow-card hover:shadow-bento hover:border-zinc-300 transition-all ${
              item.onClick ? 'cursor-pointer hover:bg-zinc-50/50' : ''
            }`}
            onClick={item.onClick}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
                {item.label}
              </span>
              {Icon && (
                <div className="p-1 rounded-md bg-zinc-100 text-zinc-700">
                  <Icon className={`w-3.5 h-3.5 ${item.iconColor || 'text-zinc-600'}`} />
                </div>
              )}
            </div>
            <div className="flex items-baseline gap-2 mt-2">
              <span className={`text-xl font-bold tracking-tight ${item.valueColor || 'text-zinc-900'}`}>
                {item.value ?? 0}
              </span>
              {item.change && (
                <span
                  className={`text-[10px] font-semibold px-1.5 py-0.2 rounded-full ${
                    item.changeType === 'increase'
                      ? 'bg-emerald-50 text-emerald-700'
                      : item.changeType === 'decrease'
                      ? 'bg-rose-50 text-rose-700'
                      : 'bg-zinc-100 text-zinc-600'
                  }`}
                >
                  {item.change}
                </span>
              )}
            </div>
            {item.subtext && (
              <p className="text-[10px] text-zinc-400 mt-1 truncate font-medium">{item.subtext}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default MetricStrip;


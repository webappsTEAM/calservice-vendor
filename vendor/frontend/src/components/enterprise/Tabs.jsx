import React from 'react';

export function Tabs({ tabs = [], activeTab = '', onChange = () => {}, className = '', variant = 'underline' }) {
  if (variant === 'pills') {
    return (
      <div className={`p-1 bg-zinc-100/90 rounded-lg flex items-center gap-1 overflow-x-auto scrollbar-none ${className}`}>
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onChange(tab.id)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold whitespace-nowrap flex items-center gap-2 transition-all select-none ${
                isActive
                  ? 'bg-white text-zinc-950 shadow-xs'
                  : 'text-zinc-600 hover:text-zinc-900 hover:bg-white/50'
              }`}
            >
              {Icon && (
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-zinc-950' : 'text-zinc-400'}`} />
              )}
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span
                  className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                    isActive ? 'bg-zinc-100 text-zinc-900' : 'bg-zinc-200/80 text-zinc-600'
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className={`border-b border-zinc-200/90 bg-white px-2 overflow-x-auto scrollbar-none flex gap-1 ${className}`}>
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        const Icon = tab.icon;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={`py-2.5 px-3.5 text-xs font-semibold whitespace-nowrap border-b-2 -mb-px flex items-center gap-2 transition-all select-none ${
              isActive
                ? 'border-zinc-950 text-zinc-950 font-bold bg-zinc-50/50'
                : 'border-transparent text-zinc-500 hover:text-zinc-900 hover:border-zinc-300'
            }`}
          >
            {Icon && <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-zinc-950' : 'text-zinc-400'}`} />}
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span
                className={`ml-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                  isActive ? 'bg-zinc-900 text-white' : 'bg-zinc-100 text-zinc-600'
                }`}
              >
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export default Tabs;


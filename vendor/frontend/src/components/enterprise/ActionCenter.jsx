import React from 'react';
import { AlertCircle, Clock, FileCheck, Send, ShieldAlert, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export function ActionCenter({
  items = [],
  title = 'Action Center',
  subtitle = 'Items requiring immediate operational attention',
  className = '',
}) {
  if (!items || items.length === 0) {
    return null;
  }

  return (
    <div className={`bg-white border border-zinc-200/90 rounded-md shadow-card overflow-hidden ${className}`}>
      <div className="px-4 py-3 bg-zinc-50/70 border-b border-zinc-200/80 flex items-center justify-between">
        <div>
          <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider flex items-center gap-2">
            <AlertCircle className="w-3.5 h-3.5 text-zinc-700" />
            <span>{title}</span>
          </h2>
          {subtitle && <p className="text-[11px] text-zinc-500 mt-0.5">{subtitle}</p>}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-zinc-100">
        {items.map((item, idx) => {
          const count = Number(item.count || 0);
          const isUrgent = count > 0;
          const content = (
            <div
              className={`p-4 hover:bg-zinc-50/80 transition-colors flex items-center justify-between group ${
                item.to || item.onClick ? 'cursor-pointer' : ''
              }`}
              onClick={item.onClick}
            >
              <div className="min-w-0 pr-2">
                <p className="text-xs font-bold text-zinc-800 group-hover:text-zinc-950 truncate transition-colors">{item.title}</p>
                <p className="text-[10px] text-zinc-500 mt-0.5 truncate leading-tight">{item.description}</p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span
                  className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                    isUrgent
                      ? item.badgeClass || 'bg-zinc-900 text-white'
                      : 'bg-zinc-100 text-zinc-500'
                  }`}
                >
                  {count}
                </span>
                {(item.to || item.onClick) && <ChevronRight className="w-4 h-4 text-zinc-400 group-hover:text-zinc-700 transition-colors" />}
              </div>
            </div>
          );

          return item.to ? (
            <Link key={idx} to={item.to} className="block">
              {content}
            </Link>
          ) : (
            <div key={idx}>{content}</div>
          );
        })}
      </div>
    </div>
  );
}

export default ActionCenter;


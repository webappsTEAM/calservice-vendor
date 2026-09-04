import React from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';

export function Breadcrumbs({ items = [], className = '' }) {
  if (!items || items.length === 0) return null;

  return (
    <nav className={`flex items-center gap-1.5 text-[11px] text-zinc-500 font-medium ${className}`}>
      <Link to="/" className="hover:text-zinc-900 flex items-center gap-1 transition-colors p-1 rounded-md hover:bg-zinc-200/60">
        <Home className="w-3 h-3 text-zinc-400" />
        <span>Workforce</span>
      </Link>
      {items.map((item, idx) => {
        const isLast = idx === items.length - 1;
        return (
          <React.Fragment key={idx}>
            <ChevronRight className="w-3 h-3 text-zinc-400 shrink-0" />
            {item.to && !isLast ? (
              <Link to={item.to} className="hover:text-zinc-900 transition-colors truncate max-w-xs p-1 rounded-md hover:bg-zinc-200/60">
                {item.label}
              </Link>
            ) : (
              <span className={`truncate max-w-xs px-1 py-0.5 ${isLast ? 'text-zinc-900 font-bold' : ''}`}>
                {item.label}
              </span>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}

export default Breadcrumbs;


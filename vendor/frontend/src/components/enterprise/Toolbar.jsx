import React from 'react';
import { Search, RefreshCw, X } from 'lucide-react';

export function Toolbar({
  searchValue = '',
  onSearchChange = null,
  searchPlaceholder = 'Search records...',
  filters = [],
  activeFilters = {},
  onFilterChange = null,
  onRefresh = null,
  isRefreshing = false,
  actions = null,
  className = '',
}) {
  return (
    <div
      className={`bg-white border border-zinc-200/90 rounded-md p-3 shadow-card flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 ${className}`}
    >
      {/* Left: Search and Filters */}
      <div className="flex flex-1 flex-wrap items-center gap-2.5">
        {onSearchChange && (
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
            <input
              type="text"
              value={searchValue}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder={searchPlaceholder}
              className="w-full pl-9 pr-8 py-1.5 min-h-[36px] bg-white border border-zinc-300 rounded-lg text-xs text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs transition-all"
            />
            {searchValue && (
              <button
                type="button"
                onClick={() => onSearchChange('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 rounded-full text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        )}

        {/* Filter dropdowns */}
        {filters.map((filter) => (
          <div key={filter.key} className="flex items-center gap-1.5">
            {filter.label && (
              <span className="text-[11px] font-semibold text-zinc-500 hidden lg:inline">
                {filter.label}:
              </span>
            )}
            <select
              value={activeFilters[filter.key] ?? ''}
              onChange={(e) => onFilterChange && onFilterChange(filter.key, e.target.value)}
              className="py-1.5 px-3 min-h-[36px] bg-white border border-zinc-300 rounded-lg text-xs text-zinc-800 font-medium focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs transition-all"
            >
              {filter.options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>

      {/* Right: Refresh CTA and custom action buttons */}
      <div className="flex items-center gap-2 self-end md:self-auto shrink-0">
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-2 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg border border-zinc-200 hover:bg-zinc-50 active:bg-zinc-100 text-zinc-600 hover:text-zinc-900 transition-all disabled:opacity-50 shadow-xs"
            title="Refresh Data"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        )}
        {actions}
      </div>
    </div>
  );
}

export default Toolbar;


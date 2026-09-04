import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

export function Pagination({
  currentPage = 1,
  totalItems = 0,
  pageSize = 10,
  onPageChange = () => {},
  className = '',
}) {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const startItem = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(totalItems, currentPage * pageSize);

  return (
    <div
      className={`px-4 py-3 bg-white border border-zinc-200/90 rounded-md shadow-card flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-zinc-600 ${className}`}
    >
      <div>
        <span>
          Showing <strong className="text-zinc-900 font-bold">{startItem}</strong> to{' '}
          <strong className="text-zinc-900 font-bold">{endItem}</strong> of{' '}
          <strong className="text-zinc-900 font-bold">{totalItems}</strong> records
        </span>
      </div>

      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          className="py-1 px-2.5 rounded-lg border border-zinc-300 bg-white hover:bg-zinc-50 active:bg-zinc-100 disabled:opacity-40 disabled:hover:bg-white flex items-center gap-1 font-semibold text-zinc-800 transition-all shadow-xs disabled:shadow-none"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          <span>Previous</span>
        </button>

        <span className="px-3 font-semibold text-zinc-900">
          Page {currentPage} of {totalPages}
        </span>

        <button
          type="button"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          className="py-1 px-2.5 rounded-lg border border-zinc-300 bg-white hover:bg-zinc-50 active:bg-zinc-100 disabled:opacity-40 disabled:hover:bg-white flex items-center gap-1 font-semibold text-zinc-800 transition-all shadow-xs disabled:shadow-none"
        >
          <span>Next</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

export default Pagination;


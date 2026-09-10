import React from 'react';
import { ChevronUp, ChevronDown, Inbox } from 'lucide-react';

export function DataTable({
  columns = [],
  data = [],
  keyField = 'id',
  isLoading = false,
  emptyMessage = 'No records found.',
  onRowClick = null,
  sortColumn = null,
  sortDirection = 'asc',
  onSort = null,
  compact = false,
  className = '',
}) {
  if (isLoading) {
    return (
      <div className="bg-white border border-zinc-200/90 rounded-md shadow-card overflow-hidden">
        <div className="divide-y divide-zinc-100">
          {[1, 2, 3, 4, 5].map((idx) => (
            <div key={idx} className="p-4 flex items-center justify-between animate-pulse">
              <div className="flex items-center gap-3 w-1/3">
                <div className="w-6 h-6 rounded-lg bg-zinc-200" />
                <div className="h-3 w-32 bg-zinc-200 rounded-md" />
              </div>
              <div className="h-3 w-24 bg-zinc-100 rounded-md" />
              <div className="h-3 w-20 bg-zinc-100 rounded-md" />
              <div className="h-5 w-16 bg-zinc-200 rounded-full" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white border border-zinc-200/90 rounded-md p-10 text-center shadow-card">
        <div className="w-10 h-10 rounded-full bg-zinc-100 text-zinc-400 flex items-center justify-center mx-auto mb-3">
          <Inbox className="w-5 h-5" />
        </div>
        <p className="text-xs font-semibold text-zinc-700">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className={`bg-white border border-zinc-200/90 rounded-md shadow-card overflow-hidden ${className}`}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-zinc-50/90 border-b border-zinc-200 text-zinc-700 text-[11px] font-semibold uppercase tracking-wider select-none">
              {columns.map((col) => {
                const isSortable = Boolean(col.sortable && onSort);
                const isCurrentSort = sortColumn === col.key;

                return (
                  <th
                    key={col.key}
                    onClick={() => isSortable && onSort(col.key)}
                    className={`${compact ? 'px-3 py-2.5' : 'px-4 py-3'} ${
                      col.align === 'right'
                        ? 'text-right'
                        : col.align === 'center'
                        ? 'text-center'
                        : 'text-left'
                    } ${isSortable ? 'cursor-pointer hover:bg-zinc-100 transition-colors' : ''} ${
                      col.className || ''
                    }`}
                  >
                    <div
                      className={`inline-flex items-center gap-1.5 ${
                        col.align === 'right' ? 'justify-end' : col.align === 'center' ? 'justify-center' : ''
                      }`}
                    >
                      <span>{col.header}</span>
                      {isSortable && (
                        <span className="text-zinc-400 inline-flex flex-col">
                          {isCurrentSort ? (
                            sortDirection === 'asc' ? (
                              <ChevronUp className="w-3.5 h-3.5 text-zinc-900 stroke-[2.5]" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5 text-zinc-900 stroke-[2.5]" />
                            )
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5 opacity-30" />
                          )}
                        </span>
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {data.map((row, index) => {
              const rowKey = row[keyField] || index;
              return (
                <tr
                  key={rowKey}
                  onClick={() => onRowClick && onRowClick(row)}
                  className={`hover:bg-zinc-50/80 transition-colors ${
                    onRowClick ? 'cursor-pointer' : ''
                  }`}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={`${compact ? 'px-3 py-2.5' : 'px-4 py-3'} ${
                        col.align === 'right'
                          ? 'text-right'
                          : col.align === 'center'
                          ? 'text-center'
                          : 'text-left'
                      } ${col.cellClassName || ''}`}
                    >
                      {col.render ? col.render(row[col.key], row, index) : row[col.key] ?? '—'}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default DataTable;


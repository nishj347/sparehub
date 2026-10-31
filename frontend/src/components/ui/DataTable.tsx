import React from 'react';
import { LoadingState } from './LoadingState';

export interface Column<T> {
  header: string;
  accessor?: keyof T | ((row: T) => React.ReactNode);
  sortKey?: string;
  className?: string;
  align?: 'left' | 'center' | 'right';
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (row: T) => string | number;
  isLoading?: boolean;
  sort?: { field: string; order: 'asc' | 'desc' };
  onSort?: (field: string) => void;
  emptyState?: React.ReactNode;
  onRowClick?: (row: T) => void;
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  isLoading = false,
  sort,
  onSort,
  emptyState,
  onRowClick,
}: DataTableProps<T>): React.ReactElement {
  if (isLoading && data.length === 0) {
    return <LoadingState />;
  }

  return (
    <div className="w-full overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50/75">
            {columns.map((col, index) => {
              const isSorted = sort && col.sortKey && sort.field === col.sortKey;
              const alignClass =
                col.align === 'center'
                  ? 'text-center'
                  : col.align === 'right'
                  ? 'text-right'
                  : 'text-left';

              return (
                <th
                  key={index}
                  scope="col"
                  onClick={() => col.sortKey && onSort && onSort(col.sortKey)}
                  className={`px-6 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500 ${alignClass} ${
                    col.sortKey && onSort
                      ? 'cursor-pointer select-none hover:text-slate-900 transition-colors'
                      : ''
                  } ${col.className || ''}`}
                >
                  <div
                    className={`inline-flex items-center gap-1 ${
                      col.align === 'center'
                        ? 'justify-center'
                        : col.align === 'right'
                        ? 'justify-end'
                        : 'justify-start'
                    }`}
                  >
                    <span>{col.header}</span>
                    {col.sortKey && onSort && (
                      <span className="text-slate-400">
                        {isSorted ? (
                          sort.order === 'asc' ? (
                            <svg className="w-3.5 h-3.5 text-primary-600" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clipRule="evenodd" />
                            </svg>
                          ) : (
                            <svg className="w-3.5 h-3.5 text-primary-600" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                            </svg>
                          )
                        ) : (
                          <svg className="w-3.5 h-3.5 opacity-40 hover:opacity-100" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M5 10a1 1 0 011-1h8a1 1 0 110 2H6a1 1 0 01-1-1z" clipRule="evenodd" />
                          </svg>
                        )}
                      </span>
                    )}
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 text-sm text-slate-700">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-6 py-12 text-center text-slate-400">
                {emptyState || 'No records found'}
              </td>
            </tr>
          ) : (
            data.map((row) => (
              <tr
                key={keyExtractor(row)}
                onClick={() => onRowClick && onRowClick(row)}
                className={`hover:bg-slate-50/75 transition-colors ${
                  onRowClick ? 'cursor-pointer' : ''
                }`}
              >
                {columns.map((col, index) => {
                  const alignClass =
                    col.align === 'center'
                      ? 'text-center'
                      : col.align === 'right'
                      ? 'text-right'
                      : 'text-left';

                  let cellContent: React.ReactNode = null;
                  if (typeof col.accessor === 'function') {
                    cellContent = col.accessor(row);
                  } else if (col.accessor) {
                    cellContent = row[col.accessor] as unknown as React.ReactNode;
                  }

                  return (
                    <td
                      key={index}
                      className={`px-6 py-4 whitespace-nowrap ${alignClass} ${col.className || ''}`}
                    >
                      {cellContent}
                    </td>
                  );
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}


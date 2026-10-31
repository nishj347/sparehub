import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';

type ParamValue = string | number | null | undefined;

/**
 * Thin wrapper around React Router's useSearchParams that keeps filters/page/sort
 * in the URL so the browser back button and page refresh restore the same state.
 */
export function useUrlSearchState() {
  const [searchParams, setSearchParams] = useSearchParams();

  const get = useCallback(
    (key: string, fallback = '') => searchParams.get(key) ?? fallback,
    [searchParams],
  );

  const getInt = useCallback(
    (key: string, fallback: number) => {
      const v = searchParams.get(key);
      if (!v) return fallback;
      const n = parseInt(v, 10);
      return isNaN(n) ? fallback : n;
    },
    [searchParams],
  );

  const set = useCallback(
    (updates: Record<string, ParamValue>, resetPage = true) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        Object.entries(updates).forEach(([k, v]) => {
          if (v == null || v === '') {
            next.delete(k);
          } else {
            next.set(k, String(v));
          }
        });
        if (resetPage && !('page' in updates)) {
          next.delete('page');
        }
        return next;
      }, { replace: false });
    },
    [setSearchParams],
  );

  const clear = useCallback(() => {
    setSearchParams(new URLSearchParams(), { replace: false });
  }, [setSearchParams]);

  return { get, getInt, set, clear, searchParams };
}


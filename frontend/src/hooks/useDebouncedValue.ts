import { useEffect, useState } from 'react';

/**
 * Custom hook to debounce rapid value updates (e.g. search inputs).
 * @param value The value to debounce
 * @param delay Milliseconds to delay updating the returned value (default 300ms)
 */
export function useDebouncedValue<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}


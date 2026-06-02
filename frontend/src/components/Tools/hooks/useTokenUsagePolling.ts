import { useEffect, useRef } from 'react';

export function useTokenUsagePolling(
  fetchSummary: (opts: { silent: boolean }) => Promise<void>,
  intervalMs: number = 30_000
): void {
  const inFlightRef = useRef(false);
  const timerRef = useRef<number | null>(null);
  const cancelledRef = useRef(false);
  const fetchRef = useRef(fetchSummary);
  fetchRef.current = fetchSummary;

  useEffect(() => {
    cancelledRef.current = false;

    const clear = () => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };

    const schedule = (delay: number) => {
      if (cancelledRef.current) return;
      clear();
      timerRef.current = window.setTimeout(run, delay);
    };

    const run = async () => {
      if (cancelledRef.current) return;
      if (document.hidden) {
        schedule(intervalMs);
        return;
      }
      if (inFlightRef.current) {
        schedule(intervalMs);
        return;
      }
      inFlightRef.current = true;
      try {
        await fetchRef.current({ silent: true });
        schedule(intervalMs);
      } catch {
        schedule(intervalMs * 2);
      } finally {
        inFlightRef.current = false;
      }
    };

    const onVisibility = () => {
      if (document.hidden) return;
      clear();
      run();
    };

    document.addEventListener('visibilitychange', onVisibility);
    schedule(intervalMs);

    return () => {
      cancelledRef.current = true;
      clear();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [intervalMs]);
}

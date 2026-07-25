"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type LiveDataState<T> = {
  data: T | null;
  error: string | null;
  isLoading: boolean;
  isRefreshing: boolean;
  updatedAt: Date | null;
  refresh: () => void;
};

export function useLiveData<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  refreshMs = 60_000,
): LiveDataState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const hasDataRef = useRef(false);

  const refresh = useCallback(async () => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    if (hasDataRef.current) setIsRefreshing(true);
    else setIsLoading(true);

    try {
      const nextData = await loader(controller.signal);
      setData(nextData);
      hasDataRef.current = true;
      setError(null);
      setUpdatedAt(new Date());
    } catch (caught) {
      if (controller.signal.aborted) return;
      setError(
        caught instanceof Error ? caught.message : "Unable to load live data.",
      );
    } finally {
      if (!controller.signal.aborted) {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    }
  }, [loader]);

  useEffect(() => {
    const kickoff = window.setTimeout(() => void refresh(), 0);
    const timer = window.setInterval(() => void refresh(), refreshMs);
    return () => {
      window.clearTimeout(kickoff);
      window.clearInterval(timer);
      controllerRef.current?.abort();
    };
  }, [refresh, refreshMs]);

  return { data, error, isLoading, isRefreshing, updatedAt, refresh };
}

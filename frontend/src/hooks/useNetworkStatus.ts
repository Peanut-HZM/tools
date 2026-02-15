import { useState, useEffect, useCallback } from 'react';
import type { NetworkStatus } from '../types/offlineCache';

interface UseNetworkStatusReturn {
  networkStatus: NetworkStatus;
  checkConnection: () => Promise<boolean>;
}

export function useNetworkStatus(): UseNetworkStatusReturn {
  const [networkStatus, setNetworkStatus] = useState<NetworkStatus>({
    isOnline: navigator.onLine,
    isSyncing: false,
  });

  useEffect(() => {
    const connection = (navigator as Navigator & { connection?: NetworkInformation }).connection;

    const updateNetworkStatus = () => {
      const newStatus: NetworkStatus = {
        isOnline: navigator.onLine,
        isSyncing: networkStatus.isSyncing,
        connectionType: connection?.effectiveType as NetworkStatus['connectionType'],
        rtt: connection?.rtt,
      };
      setNetworkStatus(newStatus);
    };

    const handleOnline = () => {
      setNetworkStatus((prev) => ({ ...prev, isOnline: true }));
    };

    const handleOffline = () => {
      setNetworkStatus((prev) => ({ ...prev, isOnline: false }));
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    if (connection) {
      connection.addEventListener('change', updateNetworkStatus);
    }

    updateNetworkStatus();

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      if (connection) {
        connection.removeEventListener('change', updateNetworkStatus);
      }
    };
  }, [networkStatus.isSyncing]);

  const checkConnection = useCallback(async (): Promise<boolean> => {
    if (!navigator.onLine) {
      return false;
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch('/api/health', {
        method: 'HEAD',
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      return response.ok;
    } catch {
      return false;
    }
  }, []);

  return {
    networkStatus,
    checkConnection,
  };
}

export default useNetworkStatus;

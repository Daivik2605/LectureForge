'use client';

import { useQuery } from '@tanstack/react-query';
import { getJobStatus, JobStatus } from '@/lib/api';

interface UseJobStatusReturn {
  status: JobStatus | null;
  isLoading: boolean;
  error: string | null;
}

export function useJobStatus(jobId: string): UseJobStatusReturn {
  const { data, isLoading, error } = useQuery({
    queryKey: ['jobStatus', jobId],
    queryFn: () => getJobStatus(jobId),
    retry: false,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // Stop polling if job is complete or failed
      if (status === 'completed' || status === 'failed') {
        return false;
      }
      return 2000; // Poll every 2 seconds
    },
    enabled: !!jobId,
  });

  return {
    status: data || null,
    isLoading,
    error: error ? (error as Error).message : null,
  };
}

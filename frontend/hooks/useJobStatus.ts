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
      // Use exact strings from your backend Redis updates
      if (status === 'Completed' || status === 'Failed') {
        return false; // Stop polling
      }
      return 2000; // Poll every 2 seconds while processing
    },
    enabled: !!jobId,
  });

  return {
    status: data || null,
    isLoading,
    error: error ? (error as Error).message : null,
  };
}

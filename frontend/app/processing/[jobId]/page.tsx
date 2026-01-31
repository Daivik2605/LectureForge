'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Loader2, CheckCircle, XCircle, Clock } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useJobStatus } from '@/hooks/useJobStatus';
import { useJobWebSocket } from '@/hooks/useWebSocket';
import { SlideProgressList } from '@/components/processing/SlideProgressList';

export default function ProcessingPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.jobId as string;
  
  const { status: pollStatus, isLoading, error } = useJobStatus(jobId);
  const [wsRetry, setWsRetry] = useState(0);
  const [wsRetrying, setWsRetrying] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const { status: wsStatus, isConnected, error: wsError } = useJobWebSocket(jobId, wsRetry);
  const jobNotFoundRetryDelayMs = 2000;
  const jobNotFoundMaxRetries = 3;
  const isJobNotLoaded = retryCount > 0 && !pollStatus && !wsStatus;
  
  // Merge WebSocket and polling status - prefer WS for real-time, poll for reliability
// Merge status objects only if they exist
  // Merge status objects by explicitly casting the sources to objects
  const status = {
    ...((pollStatus as object) || {}),
    ...((wsStatus as object) || {}),
    // Explicitly handle slides_progress with fallback
    slides_progress: (wsStatus as any)?.slides_progress || (pollStatus as any)?.slides_progress || [],
    status: (wsStatus as any)?.status || (pollStatus as any)?.status || 'Queued',
    progress: (wsStatus as any)?.progress || (pollStatus as any)?.progress || 0,
  };

  // 2. Check completion - Updated to match Redis strings ('Completed' and 'Failed')
  const isCompleted = status?.status === 'Completed' || status?.status === 'completed';
  const isFailed = status?.status === 'Failed' || status?.status === 'failed';

  useEffect(() => {
    if (isCompleted) {
      // Small delay to show 100% before redirecting
      const timer = setTimeout(() => {
        router.push(`/results/${jobId}`);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [isCompleted, jobId, router]);

  if (isLoading && !pollStatus && !wsStatus) {
    return (
      <div className="container mx-auto py-10 px-4">
        <div className="flex flex-col items-center justify-center min-h-[400px] gap-3 text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <div className="text-sm">
            {isJobNotLoaded ? (
              <span className="inline-flex items-center gap-2">
                Establishing connection... (Attempt {retryCount}/3)
                <Loader2 className="h-4 w-4 animate-spin" />
              </span>
            ) : (
              'Loading...'
            )}
          </div>
        </div>
      </div>
    );
  }

  useEffect(() => {
    if (!wsError) {
      setWsRetrying(false);
      return;
    }
    if (wsError.toLowerCase().includes('job not found') && wsRetry < jobNotFoundMaxRetries) {
      setWsRetrying(true);
      setRetryCount((prev) => Math.min(prev + 1, jobNotFoundMaxRetries));
      const timer = setTimeout(() => {
        setWsRetry((prev) => prev + 1);
      }, jobNotFoundRetryDelayMs);
      return () => clearTimeout(timer);
    }
    setWsRetrying(false);
  }, [wsError, wsRetry]);

  if (error && !wsRetrying) {
    return (
      <div className="container mx-auto py-10 px-4">
        <Card className="max-w-2xl mx-auto">
          <CardContent className="py-10 text-center">
            <XCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">Error Loading Job</h2>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button onClick={() => router.push('/upload')}>
              Try Again
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isFailed && !wsRetrying) {
    return (
      <div className="container mx-auto py-10 px-4">
        <Card className="max-w-2xl mx-auto">
          <CardContent className="py-10 text-center">
            <XCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">
              {isJobNotLoaded ? (
                <span className="inline-flex items-center gap-2">
                  Establishing connection... (Attempt {retryCount}/3)
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </span>
              ) : (
                'Processing Failed'
              )}
            </h2>
            <p className="text-muted-foreground mb-4">{status?.error || 'An error occurred'}</p>
            <Button onClick={() => router.push('/upload')}>
              Try Again
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Show completion state briefly before redirect
  if (isCompleted) {
    return (
      <div className="container mx-auto py-10 px-4">
        <Card className="max-w-2xl mx-auto">
          <CardContent className="py-10 text-center">
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">Processing Complete!</h2>
            <p className="text-muted-foreground mb-4">Redirecting to results...</p>
            <Loader2 className="h-6 w-6 animate-spin mx-auto text-primary" />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-10 px-4">
      <div className="max-w-2xl mx-auto space-y-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Processing...
                </CardTitle>
                <CardDescription>
                  {status?.current_step || 'Preparing...'}
                </CardDescription>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-yellow-500'}`} />
                {wsRetrying ? 'Reconnecting' : isConnected ? 'Live' : 'Polling'}
              </div>
            </div>
          </CardHeader>
          
          <CardContent className="space-y-6">
            {/* Overall Progress */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Overall Progress</span>
                <span>{status?.progress || 0}%</span>
              </div>
              <Progress value={status?.progress || 0} className="h-3" />
            </div>

            {/* Current Slide Info */}
            {status?.current_slide && status?.total_slides && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Clock className="h-4 w-4" />
                Processing slide {status.current_slide} of {status.total_slides}
              </div>
            )}

            {/* Slide Progress */}
            {status?.slides_progress && status.slides_progress.length > 0 && (
              <SlideProgressList slides={status.slides_progress} />
            )}

            {/* Cancel Button */}
            <Button variant="outline" className="w-full" onClick={() => router.push('/upload')}>
              Cancel
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

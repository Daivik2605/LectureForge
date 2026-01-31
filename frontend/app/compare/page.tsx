'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Play, Pause, Gauge, DollarSign, Cpu } from 'lucide-react';

import { getApiBaseUrl, getFileUrl } from '@/lib/api';

type BenchmarkSummary = {
  avg_tps?: number | null;
  final_cost?: number | null;
};

type BenchmarkEntry = {
  job_id: string;
  model_name: string;
  summary?: BenchmarkSummary;
};

type JobResult = {
  job_id: string;
  filename: string;
  final_video_path?: string | null;
  finalVideoPath?: string | null;
};

type SelectedJob = {
  jobId: string;
  modelName: string;
  avgTps: number;
  finalCost: number;
  videoUrl: string | null;
};

const formatMoney = (value: number) => {
  if (!Number.isFinite(value)) {
    return '$0.00';
  }
  return `$${value.toFixed(4)}`;
};

const formatNumber = (value: number, digits = 2) => {
  if (!Number.isFinite(value)) {
    return '—';
  }
  return value.toFixed(digits);
};

export default function ComparePage() {
  const [history, setHistory] = useState<BenchmarkEntry[]>([]);
  const [leftJobId, setLeftJobId] = useState<string>('');
  const [rightJobId, setRightJobId] = useState<string>('');
  const [leftData, setLeftData] = useState<SelectedJob | null>(null);
  const [rightData, setRightData] = useState<SelectedJob | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [loading, setLoading] = useState(true);

  const leftRef = useRef<HTMLVideoElement | null>(null);
  const rightRef = useRef<HTMLVideoElement | null>(null);
  const syncingRef = useRef(false);

  useEffect(() => {
    const loadHistory = async () => {
      setLoading(true);
      try {
        const response = await fetch(`${getApiBaseUrl()}/api/v1/benchmarks/history?limit=10`);
        if (!response.ok) {
          throw new Error('Failed to load benchmark history');
        }
        const payload = (await response.json()) as BenchmarkEntry[];
        setHistory(payload);
        if (payload[0]?.job_id && !leftJobId) {
          setLeftJobId(payload[0].job_id);
        }
        if (payload[1]?.job_id && !rightJobId) {
          setRightJobId(payload[1].job_id);
        }
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };
    loadHistory();
  }, [leftJobId, rightJobId]);

  const jobOptions = useMemo(
    () =>
      history.map((entry) => ({
        value: entry.job_id,
        label: `${entry.model_name} · ${entry.job_id.slice(0, 8)}`,
      })),
    [history]
  );

  useEffect(() => {
    const fetchJobData = async (jobId: string, setState: (value: SelectedJob | null) => void) => {
      if (!jobId) {
        setState(null);
        return;
      }
      try {
        const [benchmarkRes, resultRes] = await Promise.all([
          fetch(`${getApiBaseUrl()}/api/v1/benchmarks/compare?job_ids=${jobId}`),
          fetch(`${getApiBaseUrl()}/api/v1/jobs/${jobId}/result`),
        ]);
        if (!benchmarkRes.ok || !resultRes.ok) {
          throw new Error('Failed to load job data');
        }
        const benchmarkPayload = (await benchmarkRes.json()) as BenchmarkEntry[];
        const jobResult = (await resultRes.json()) as JobResult;
        const benchmark = benchmarkPayload[0];
        const videoPath = jobResult.final_video_path || jobResult.finalVideoPath || null;
        setState({
          jobId,
          modelName: benchmark?.model_name || 'Unknown',
          avgTps: benchmark?.summary?.avg_tps ?? 0,
          finalCost: benchmark?.summary?.final_cost ?? 0,
          videoUrl: videoPath ? getFileUrl(videoPath) : null,
        });
      } catch (error) {
        console.error(error);
        setState(null);
      }
    };
    fetchJobData(leftJobId, setLeftData);
  }, [leftJobId]);

  useEffect(() => {
    const fetchJobData = async (jobId: string, setState: (value: SelectedJob | null) => void) => {
      if (!jobId) {
        setState(null);
        return;
      }
      try {
        const [benchmarkRes, resultRes] = await Promise.all([
          fetch(`${getApiBaseUrl()}/api/v1/benchmarks/compare?job_ids=${jobId}`),
          fetch(`${getApiBaseUrl()}/api/v1/jobs/${jobId}/result`),
        ]);
        if (!benchmarkRes.ok || !resultRes.ok) {
          throw new Error('Failed to load job data');
        }
        const benchmarkPayload = (await benchmarkRes.json()) as BenchmarkEntry[];
        const jobResult = (await resultRes.json()) as JobResult;
        const benchmark = benchmarkPayload[0];
        const videoPath = jobResult.final_video_path || jobResult.finalVideoPath || null;
        setState({
          jobId,
          modelName: benchmark?.model_name || 'Unknown',
          avgTps: benchmark?.summary?.avg_tps ?? 0,
          finalCost: benchmark?.summary?.final_cost ?? 0,
          videoUrl: videoPath ? getFileUrl(videoPath) : null,
        });
      } catch (error) {
        console.error(error);
        setState(null);
      }
    };
    fetchJobData(rightJobId, setRightData);
  }, [rightJobId]);

  const handleMasterToggle = () => {
    const left = leftRef.current;
    const right = rightRef.current;
    if (!left || !right) {
      return;
    }
    syncingRef.current = true;
    if (isPlaying) {
      left.pause();
      right.pause();
      setIsPlaying(false);
    } else {
      void left.play();
      void right.play();
      setIsPlaying(true);
    }
    window.setTimeout(() => {
      syncingRef.current = false;
    }, 150);
  };

  const handleSyncPlay = (source: 'left' | 'right') => {
    if (syncingRef.current) {
      return;
    }
    const left = leftRef.current;
    const right = rightRef.current;
    if (!left || !right) {
      return;
    }
    syncingRef.current = true;
    if (source === 'left') {
      void right.play();
    } else {
      void left.play();
    }
    setIsPlaying(true);
    window.setTimeout(() => {
      syncingRef.current = false;
    }, 150);
  };

  const handleSyncPause = (source: 'left' | 'right') => {
    if (syncingRef.current) {
      return;
    }
    const left = leftRef.current;
    const right = rightRef.current;
    if (!left || !right) {
      return;
    }
    syncingRef.current = true;
    if (source === 'left') {
      right.pause();
    } else {
      left.pause();
    }
    setIsPlaying(false);
    window.setTimeout(() => {
      syncingRef.current = false;
    }, 150);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-10">
        <header className="flex flex-col gap-4">
          <div className="text-sm uppercase tracking-[0.4em] text-slate-400">Model Arena</div>
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <h1 className="text-3xl font-semibold text-slate-50">Side-by-Side Video Comparison</h1>
            <button
              type="button"
              onClick={handleMasterToggle}
              className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:border-slate-500"
            >
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
              Master {isPlaying ? 'Pause' : 'Play'}
            </button>
          </div>
        </header>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
            <label className="text-xs uppercase tracking-[0.2em] text-slate-400">
              Left Job
            </label>
            <select
              value={leftJobId}
              onChange={(event) => setLeftJobId(event.target.value)}
              className="mt-2 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100"
            >
              <option value="">Select a job</option>
              {jobOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
            <label className="text-xs uppercase tracking-[0.2em] text-slate-400">
              Right Job
            </label>
            <select
              value={rightJobId}
              onChange={(event) => setRightJobId(event.target.value)}
              className="mt-2 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100"
            >
              <option value="">Select a job</option>
              {jobOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {loading && (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 text-sm text-slate-300">
            Loading benchmarks…
          </div>
        )}

        <div className="grid gap-6 md:grid-cols-2">
          {[leftData, rightData].map((entry, index) => (
            <div
              key={entry?.jobId || index}
              className="relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/70"
            >
              <div className="absolute left-4 top-4 z-10 rounded-full bg-slate-950/80 px-3 py-1 text-xs uppercase tracking-[0.2em] text-slate-300">
                {index === 0 ? 'Left' : 'Right'}
              </div>
              <div className="absolute right-4 top-4 z-10 flex flex-col gap-2 rounded-2xl bg-slate-950/80 p-3 text-xs text-slate-200">
                <div className="text-sm font-semibold text-slate-100">
                  {entry?.modelName || 'Select a job'}
                </div>
                <div className="flex items-center gap-2">
                  <Gauge className="h-3 w-3 text-emerald-300" />
                  {entry ? `${formatNumber(entry.avgTps)} TPS` : '—'}
                </div>
                <div className="flex items-center gap-2">
                  <DollarSign className="h-3 w-3 text-amber-300" />
                  {entry ? formatMoney(entry.finalCost) : '—'}
                </div>
                <div className="flex items-center gap-2 text-slate-400">
                  <Cpu className="h-3 w-3" />
                  {entry?.jobId ? entry.jobId.slice(0, 8) : '—'}
                </div>
              </div>
              {entry?.videoUrl ? (
                <video
                  ref={index === 0 ? leftRef : rightRef}
                  className="aspect-video w-full"
                  src={entry.videoUrl}
                  controls
                  onPlay={() => handleSyncPlay(index === 0 ? 'left' : 'right')}
                  onPause={() => handleSyncPause(index === 0 ? 'left' : 'right')}
                />
              ) : (
                <div className="flex aspect-video items-center justify-center text-sm text-slate-400">
                  No video loaded
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

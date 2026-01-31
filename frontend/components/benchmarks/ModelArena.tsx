'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Cpu,
  Gauge,
  ShieldCheck,
  Trophy,
  Sparkles,
  Zap,
  Leaf,
  Coins,
  Banknote,
} from 'lucide-react';

import { getApiBaseUrl } from '@/lib/api';

type SlideMetric = {
  tps?: number | null;
  ttft?: number | null;
  word_count?: number | null;
  json_valid?: boolean | null;
  hallucination_ok?: boolean | null;
  memory_kb?: number | null;
  token_count?: number | null;
};

type BenchmarkPayload = {
  job_id: string;
  model_name: string;
  timestamp: number;
  summary?: {
    avg_tps?: number | null;
    avg_ttft?: number | null;
    avg_duration?: number | null;
    avg_memory_kb?: number | null;
    json_adherence_rate?: number | null;
    hallucination_ok_rate?: number | null;
    slides_count?: number | null;
  };
  meta?: {
    slide_metrics?: SlideMetric[];
  };
};

type ModelArenaProps = {
  jobIds: string[];
  pricingOverrides?: Record<string, number>;
};

type DerivedBenchmark = {
  jobId: string;
  modelName: string;
  avgTps: number;
  avgTtft: number;
  avgMemoryKb: number;
  reliability: number;
  efficiency: number;
  estimatedCost: number;
  valueForMoney: number;
  slides: number;
  slideMetrics: SlideMetric[];
};

const defaultPricingPer1M: Record<string, number> = {
  gpt: 10,
  openai: 10,
  claude: 15,
  anthropic: 15,
};

const modelBadgeClasses = (modelName: string) => {
  const name = modelName.toLowerCase();
  if (name.includes('llama')) {
    return 'bg-emerald-500/15 text-emerald-200 border-emerald-400/40';
  }
  if (name.includes('mistral')) {
    return 'bg-sky-500/15 text-sky-200 border-sky-400/40';
  }
  if (name.includes('mixtral')) {
    return 'bg-teal-500/15 text-teal-200 border-teal-400/40';
  }
  if (name.includes('gemma')) {
    return 'bg-amber-500/15 text-amber-200 border-amber-400/40';
  }
  if (name.includes('phi')) {
    return 'bg-fuchsia-500/15 text-fuchsia-200 border-fuchsia-400/40';
  }
  if (name.includes('qwen')) {
    return 'bg-indigo-500/15 text-indigo-200 border-indigo-400/40';
  }
  return 'bg-slate-500/15 text-slate-200 border-slate-400/40';
};

const isPaidModel = (modelName: string) => {
  const name = modelName.toLowerCase();
  return name.includes('gpt') || name.includes('openai') || name.includes('claude') || name.includes('anthropic');
};

const isLocalModel = (modelName: string) => !isPaidModel(modelName);

const formatNumber = (value: number, digits = 2) => {
  if (!Number.isFinite(value)) {
    return '—';
  }
  return value.toFixed(digits);
};

const safeAverage = (values: Array<number | null | undefined>) => {
  const cleaned = values.filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
  if (!cleaned.length) {
    return 0;
  }
  return cleaned.reduce((sum, v) => sum + v, 0) / cleaned.length;
};

const getEstimatedTokens = (metrics: SlideMetric[]) => {
  const explicitTokens = metrics
    .map((m) => m.token_count)
    .filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
  if (explicitTokens.length) {
    return explicitTokens.reduce((sum, v) => sum + v, 0);
  }
  const wordCounts = metrics
    .map((m) => m.word_count)
    .filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
  if (!wordCounts.length) {
    return 0;
  }
  const words = wordCounts.reduce((sum, v) => sum + v, 0);
  return Math.round(words * 1.3);
};

const getEstimatedCost = (
  modelName: string,
  metrics: SlideMetric[],
  pricingOverrides?: Record<string, number>
) => {
  if (!metrics.length) {
    return 0;
  }
  const name = modelName.toLowerCase();
  if (!isPaidModel(modelName)) {
    return 0;
  }
  const tokens = getEstimatedTokens(metrics);
  let rate = 0;
  const pricing = pricingOverrides ?? defaultPricingPer1M;
  for (const key of Object.keys(pricing)) {
    if (name.includes(key)) {
      rate = pricing[key];
      break;
    }
  }
  if (!rate) {
    rate = 12;
  }
  return (tokens / 1_000_000) * rate;
};

const getReliabilityScore = (
  metrics: SlideMetric[],
  summary?: { json_adherence_rate?: number | null; hallucination_ok_rate?: number | null }
) => {
  if (!metrics.length) {
    const jsonRate = summary?.json_adherence_rate ?? 0;
    const hallucRate = summary?.hallucination_ok_rate ?? 0;
    return ((jsonRate + hallucRate) / 2) * 100;
  }
  const jsonRate =
    metrics.filter((m) => m.json_valid === true).length / Math.max(metrics.length, 1);
  const hallucRate =
    metrics.filter((m) => m.hallucination_ok === true).length / Math.max(metrics.length, 1);
  return ((jsonRate + hallucRate) / 2) * 100;
};

export function ModelArena({ jobIds, pricingOverrides }: ModelArenaProps) {
  const [viewMode, setViewMode] = useState<'technical' | 'economic'>('technical');
  const [benchmarks, setBenchmarks] = useState<BenchmarkPayload[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobIds.length) {
      setBenchmarks([]);
      return;
    }
    const controller = new AbortController();
    const fetchBenchmarks = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        params.set('job_ids', jobIds.join(','));
        const response = await fetch(
          `${getApiBaseUrl()}/api/v1/benchmarks/compare?${params.toString()}`,
          { signal: controller.signal }
        );
        if (!response.ok) {
          throw new Error('Failed to fetch benchmark data');
        }
        const payload = (await response.json()) as BenchmarkPayload[];
        setBenchmarks(payload);
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          setError((err as Error).message || 'Unable to load benchmarks');
        }
      } finally {
        setLoading(false);
      }
    };
    fetchBenchmarks();
    return () => controller.abort();
  }, [jobIds]);

  const derived = useMemo<DerivedBenchmark[]>(() => {
    return benchmarks.map((entry) => {
      const slideMetrics = entry.meta?.slide_metrics ?? [];
      const avgTps = entry.summary?.avg_tps ?? safeAverage(slideMetrics.map((m) => m.tps));
      const avgTtft = entry.summary?.avg_ttft ?? safeAverage(slideMetrics.map((m) => m.ttft));
      const avgMemoryKb =
        entry.summary?.avg_memory_kb ?? safeAverage(slideMetrics.map((m) => m.memory_kb));
      const reliability = getReliabilityScore(slideMetrics, entry.summary);
      const memoryMb = avgMemoryKb ? avgMemoryKb / 1024 : 0;
      const efficiency = memoryMb ? (avgTps / memoryMb) * 100 : 0;
      const estimatedCost = getEstimatedCost(entry.model_name, slideMetrics, pricingOverrides);
      const valueForMoney = (reliability * 2) / (estimatedCost + 0.001);
      return {
        jobId: entry.job_id,
        modelName: entry.model_name || 'Unknown',
        avgTps: avgTps || 0,
        avgTtft: avgTtft || 0,
        avgMemoryKb: avgMemoryKb || 0,
        reliability,
        efficiency,
        estimatedCost,
        valueForMoney,
        slides: slideMetrics.length,
        slideMetrics,
      };
    });
  }, [benchmarks, pricingOverrides]);

  const maxTps = Math.max(...derived.map((d) => d.avgTps), 1);
  const maxReliability = Math.max(...derived.map((d) => d.reliability), 1);
  const maxEfficiency = Math.max(...derived.map((d) => d.efficiency), 1);
  const maxValue = Math.max(...derived.map((d) => d.valueForMoney), 1);

  const fastestModel = derived.reduce<DerivedBenchmark | null>((best, item) => {
    if (!best || item.avgTps > best.avgTps) {
      return item;
    }
    return best;
  }, null);

  const mostReliable = derived.reduce<DerivedBenchmark | null>((best, item) => {
    if (!best || item.reliability > best.reliability) {
      return item;
    }
    return best;
  }, null);

  const maxPaidReliability = Math.max(
    ...derived.filter((d) => isPaidModel(d.modelName)).map((d) => d.reliability),
    0
  );

  return (
    <section className="relative overflow-hidden rounded-3xl border border-slate-800/70 bg-slate-950 text-slate-100 shadow-[0_30px_90px_-60px_rgba(56,189,248,0.5)]">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.2),_transparent_45%),radial-gradient(circle_at_bottom,_rgba(16,185,129,0.15),_transparent_55%)]" />
      <div className="absolute -left-32 top-12 h-64 w-64 rounded-full bg-emerald-400/10 blur-3xl" />
      <div className="absolute -right-20 bottom-10 h-48 w-48 rounded-full bg-sky-400/10 blur-3xl" />
      <div className="relative z-10 space-y-8 p-8 md:p-10">
        <header className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-3 text-sm uppercase tracking-[0.4em] text-emerald-200/80">
              <Sparkles className="h-4 w-4" />
              Model Arena
            </div>
            <h2 className="text-3xl font-semibold tracking-tight text-slate-50 md:text-4xl">
              Command Center: Benchmark League
            </h2>
            <p className="max-w-2xl text-sm text-slate-300/80">
              Compare models head-to-head on speed, reliability, and efficiency. This is your
              MacBook Air scoreboard for real-world narration performance.
            </p>
          </div>
          <div className="flex flex-col gap-4 rounded-2xl border border-slate-800/70 bg-slate-900/80 p-4">
            <div className="flex items-center justify-between gap-3 text-sm text-slate-300">
              <div className="flex items-center gap-2">
                <Trophy className="h-4 w-4 text-emerald-300" />
                <span>Leaderboard</span>
              </div>
              <div className="flex rounded-full border border-slate-700/70 bg-slate-900/90 p-1 text-xs text-slate-300">
                <button
                  type="button"
                  onClick={() => setViewMode('technical')}
                  className={`rounded-full px-3 py-1 transition ${
                    viewMode === 'technical' ? 'bg-slate-700 text-slate-100' : 'text-slate-400'
                  }`}
                >
                  Technical View
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('economic')}
                  className={`rounded-full px-3 py-1 transition ${
                    viewMode === 'economic' ? 'bg-slate-700 text-slate-100' : 'text-slate-400'
                  }`}
                >
                  Economic View
                </button>
              </div>
            </div>
            <div className="flex flex-col gap-3 text-sm">
              <div className="flex items-center gap-3">
                <Gauge className="h-4 w-4 text-sky-300" />
                <div>
                  <div className="text-xs uppercase text-slate-400">Fastest Model</div>
                  <div className="font-medium text-slate-100">
                    {fastestModel ? fastestModel.modelName : '—'}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <ShieldCheck className="h-4 w-4 text-emerald-300" />
                <div>
                  <div className="text-xs uppercase text-slate-400">Most Reliable</div>
                  <div className="font-medium text-slate-100">
                    {mostReliable ? mostReliable.modelName : '—'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </header>

        {loading && (
          <div className="rounded-2xl border border-slate-800/60 bg-slate-900/70 p-6 text-sm text-slate-300">
            Loading benchmark data…
          </div>
        )}
        {error && (
          <div className="rounded-2xl border border-rose-500/40 bg-rose-500/10 p-6 text-sm text-rose-200">
            {error}
          </div>
        )}

        {!loading && !error && !derived.length && (
          <div className="rounded-2xl border border-slate-800/60 bg-slate-900/70 p-6 text-sm text-slate-300">
            Provide job IDs to compare benchmark runs.
          </div>
        )}

        {!!derived.length && (
          <div className="space-y-6">
            <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr_1fr]">
              <div className="rounded-2xl border border-slate-800/70 bg-slate-900/70 p-5">
                <div className="flex items-center gap-3 text-sm text-slate-300">
                  <Gauge className="h-4 w-4 text-sky-300" />
                  Speed Leader
                </div>
                <div className="mt-3 text-2xl font-semibold text-slate-100">
                  {fastestModel ? fastestModel.modelName : '—'}
                </div>
                <div className="mt-1 text-xs text-slate-400">
                  {fastestModel ? `${formatNumber(fastestModel.avgTps)} TPS` : 'No data'}
                </div>
              </div>
              <div className="rounded-2xl border border-slate-800/70 bg-slate-900/70 p-5">
                <div className="flex items-center gap-3 text-sm text-slate-300">
                  <ShieldCheck className="h-4 w-4 text-emerald-300" />
                  Reliability Leader
                </div>
                <div className="mt-3 text-2xl font-semibold text-slate-100">
                  {mostReliable ? mostReliable.modelName : '—'}
                </div>
                <div className="mt-1 text-xs text-slate-400">
                  {mostReliable ? `${formatNumber(mostReliable.reliability, 1)}%` : 'No data'}
                </div>
              </div>
              <div className="rounded-2xl border border-slate-800/70 bg-slate-900/70 p-5">
                <div className="flex items-center gap-3 text-sm text-slate-300">
                  <Leaf className="h-4 w-4 text-emerald-200" />
                  MacBook Air Optimizer
                </div>
                <div className="mt-3 text-2xl font-semibold text-slate-100">
                  {derived.find((d) => d.efficiency === maxEfficiency)?.modelName || '—'}
                </div>
                <div className="mt-1 text-xs text-slate-400">
                  {maxEfficiency ? `${formatNumber(maxEfficiency, 1)} score` : 'No data'}
                </div>
              </div>
            </div>

            <div className="overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-900/70">
              <div
                className={`grid ${
                  viewMode === 'technical'
                    ? 'grid-cols-[1.2fr_1fr_1fr_1fr_1fr]'
                    : 'grid-cols-[1.2fr_1fr_1fr_1fr_1fr]'
                } gap-3 border-b border-slate-800/70 px-6 py-4 text-xs uppercase tracking-[0.2em] text-slate-400`}
              >
                <span>Model</span>
                {viewMode === 'technical' ? (
                  <>
                    <span>Speed (TPS)</span>
                    <span>Latency (TTFT)</span>
                    <span>Reliability</span>
                    <span>Efficiency</span>
                  </>
                ) : (
                  <>
                    <span>Estimated Cost</span>
                    <span>Value for Money</span>
                    <span>Reliability</span>
                    <span>Efficiency</span>
                  </>
                )}
              </div>
              <div className="divide-y divide-slate-800/60">
                {derived.map((entry) => {
                  const speedPct = Math.min((entry.avgTps / maxTps) * 100, 100);
                  const efficiencyPct = Math.min((entry.efficiency / maxEfficiency) * 100, 100);
                  const reliabilityPct = Math.min((entry.reliability / maxReliability) * 100, 100);
                  const valuePct = Math.min((entry.valueForMoney / maxValue) * 100, 100);
                  const isFastest = entry.avgTps === maxTps;
                  const isReliable = entry.reliability === maxReliability;
                  const isEfficient = entry.efficiency === maxEfficiency;
                  const isPrivacyHero =
                    isLocalModel(entry.modelName) && entry.reliability >= maxPaidReliability - 0.5;
                  return (
                    <div
                      key={entry.jobId}
                      className={`grid ${
                        viewMode === 'technical'
                          ? 'grid-cols-[1.2fr_1fr_1fr_1fr_1fr]'
                          : 'grid-cols-[1.2fr_1fr_1fr_1fr_1fr]'
                      } items-center gap-3 px-6 py-5`}
                    >
                      <div className="space-y-2">
                        <div className="flex items-center gap-3">
                          <span
                            className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${modelBadgeClasses(
                              entry.modelName
                            )}`}
                          >
                            {entry.modelName}
                          </span>
                          {isEfficient && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/20 px-2 py-1 text-[11px] font-semibold text-emerald-200">
                              <Leaf className="h-3 w-3" />
                              MacBook Air Optimizer
                            </span>
                          )}
                          {isPrivacyHero && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-indigo-500/20 px-2 py-1 text-[11px] font-semibold text-indigo-200">
                              <ShieldCheck className="h-3 w-3" />
                              Privacy Hero
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-slate-400">
                          {entry.slides} slides · job {entry.jobId.slice(0, 8)}
                        </div>
                      </div>
                      {viewMode === 'technical' ? (
                        <>
                          <div className="space-y-2">
                            <div
                              className={`text-sm font-semibold ${isFastest ? 'text-emerald-300' : 'text-slate-200'}`}
                            >
                              {formatNumber(entry.avgTps)} TPS
                            </div>
                            <div className="h-2 w-full rounded-full bg-slate-800/80">
                              <div
                                className={`h-2 rounded-full ${isFastest ? 'bg-emerald-400' : 'bg-sky-400/80'}`}
                                style={{ width: `${speedPct}%` }}
                              />
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="inline-flex items-center gap-1 rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold text-slate-200">
                              <Zap className="h-3 w-3 text-sky-300" />
                              {formatNumber(entry.avgTtft, 2)}s
                            </span>
                            {entry.avgTtft > 1.5 && (
                              <span className="text-xs font-semibold text-rose-300">High</span>
                            )}
                          </div>
                        </>
                      ) : (
                        <>
                          <div className="space-y-2">
                            <div className="text-sm font-semibold text-slate-200">
                              ${formatNumber(entry.estimatedCost, 4)}
                            </div>
                            <div className="flex items-center gap-2 text-xs text-slate-400">
                              <Banknote className="h-3 w-3 text-emerald-300" />
                              {isPaidModel(entry.modelName) ? 'Cloud usage' : 'Local run'}
                            </div>
                          </div>
                          <div className="space-y-2">
                            <div
                              className={`text-sm font-semibold ${
                                entry.valueForMoney === maxValue ? 'text-emerald-300' : 'text-slate-200'
                              }`}
                            >
                              {formatNumber(entry.valueForMoney, 1)}
                            </div>
                            <div className="h-2 w-full rounded-full bg-slate-800/80">
                              <div
                                className="h-2 rounded-full bg-emerald-400"
                                style={{ width: `${valuePct}%` }}
                              />
                            </div>
                          </div>
                        </>
                      )}
                      <div className="space-y-2">
                        <div
                          className={`text-sm font-semibold ${
                            isReliable ? 'text-emerald-300' : entry.reliability < 70 ? 'text-rose-300' : 'text-slate-200'
                          }`}
                        >
                          {formatNumber(entry.reliability, 1)}%
                        </div>
                        <div className="h-2 w-full rounded-full bg-slate-800/80">
                          <div
                            className={`h-2 rounded-full ${
                              isReliable ? 'bg-emerald-400' : entry.reliability < 70 ? 'bg-rose-400/80' : 'bg-slate-400/80'
                            }`}
                            style={{ width: `${reliabilityPct}%` }}
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <div
                          className={`text-sm font-semibold ${
                            isEfficient ? 'text-emerald-300' : entry.efficiency < maxEfficiency * 0.5 ? 'text-rose-300' : 'text-slate-200'
                          }`}
                        >
                          {formatNumber(entry.efficiency, 1)}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-slate-400">
                          <Cpu className="h-3 w-3" />
                          {(entry.avgMemoryKb / 1024).toFixed(1)} MB
                        </div>
                        <div className="h-2 w-full rounded-full bg-slate-800/80">
                          <div
                            className={`h-2 rounded-full ${isEfficient ? 'bg-emerald-400' : 'bg-indigo-400/80'}`}
                            style={{ width: `${efficiencyPct}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
              <Coins className="h-3 w-3 text-amber-300" />
              Estimated cost uses token counts when available; otherwise word count × 1.3. Override pricing via
              `pricingOverrides`.
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

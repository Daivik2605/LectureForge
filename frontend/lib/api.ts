export type JobState = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
export type SlideState = 'pending' | 'processing' | 'completed' | 'failed';

export interface SlideProgress {
  slide_number: number;
  narration: SlideState;
  mcq: SlideState;
  video: SlideState;
  error?: string | null;
}

export interface MCQ {
  question: string;
  options: string[];
  answer: string;
  difficulty: 'easy' | 'medium' | 'hard';
}

export interface SlideResult {
  slide_number: number;
  text: string;
  has_text: boolean;
  title?: string | null;
  bullets?: string[] | null;
  narration?: string | null;
  qa?: {
    easy?: MCQ[];
    medium?: MCQ[];
    hard?: MCQ[];
  } | null;
  audio_path?: string | null;
  image_path?: string | null;
  video_path?: string | null;
}

export interface JobStatus {
  job_id: string;
  status: JobState;
  progress: number;
  current_slide?: number | null;
  total_slides?: number | null;
  current_step?: string | null;
  slides_progress?: SlideProgress[];
  error?: string | null;
  created_at?: string;
  updated_at?: string;
  completed_at?: string | null;
}

export interface JobResult {
  job_id: string;
  status: JobState;
  filename: string;
  language: string;
  mode: string;
  slides: SlideResult[];
  final_video_path?: string | null;
  finalVideoPath?: string | null;
  processing_time_seconds?: number | null;
  cache_hits?: number;
  cache_misses?: number;
  created_at?: string;
  completed_at?: string | null;
  jobId?: string;
  durationSeconds?: number | null;
  cacheHits?: number;
  cacheMisses?: number;
}

export interface UploadResponse {
  job_id: string;
  status: JobState;
  message: string;
}

export interface UploadParams {
  file: File;
  language: 'en' | 'fr' | 'hi';
  mode: 'ppt' | 'pdf' | 'policy' | 'auto';
  maxSlides: number;
  generateVideo: boolean;
  generateMcqs: boolean;
}

const defaultBaseUrl = 'http://localhost:8000';

export const getApiBaseUrl = (): string => {
  const base = process.env.NEXT_PUBLIC_API_URL || defaultBaseUrl;
  return base.replace(/\/$/, '');
};

const joinUrl = (base: string, path: string): string => {
  if (!path) {
    return base;
  }
  if (path.startsWith('/')) {
    return `${base}${path}`;
  }
  return `${base}/${path}`;
};

export const getFileUrl = (path?: string | null): string => {
  if (!path) {
    return '';
  }
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }

  const normalized = path.replace(/\\/g, '/');
  const dataIndex = normalized.indexOf('/data/');
  const storageIndex = normalized.indexOf('/storage/');
  let relativePath = normalized;

  if (dataIndex !== -1) {
    relativePath = normalized.slice(dataIndex);
  } else if (storageIndex !== -1) {
    relativePath = normalized.slice(storageIndex);
  } else if (!normalized.startsWith('/')) {
    relativePath = `/${normalized}`;
  }

  return joinUrl(getApiBaseUrl(), relativePath);
};

export const getWebSocketUrl = (jobId: string): string => {
  return `ws://localhost:8000/ws/jobs/${jobId}`;
};

const parseError = async (response: Response, fallback: string): Promise<string> => {
  try {
    const payload = await response.json();
    if (payload?.detail) {
      return payload.detail;
    }
    if (payload?.message) {
      return payload.message;
    }
  } catch (error) {
    return fallback;
  }
  return fallback;
};

export const uploadPresentation = async (params: UploadParams): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', params.file);
  formData.append('language', params.language);
  formData.append('mode', params.mode);
  formData.append('max_slides', String(params.maxSlides));
  formData.append('generate_video', String(params.generateVideo));
  formData.append('generate_mcqs', String(params.generateMcqs));

  const response = await fetch(joinUrl(getApiBaseUrl(), '/api/v1/process'), {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseError(response, 'Upload failed'));
  }

  return response.json();
};

export const getJobStatus = async (jobId: string): Promise<JobStatus> => {
  const response = await fetch(joinUrl(getApiBaseUrl(), `/api/v1/jobs/${jobId}/status`));
  if (!response.ok) {
    throw new Error(await parseError(response, 'Failed to fetch job status'));
  }
  return response.json();
};

export const getJobResult = async (jobId: string): Promise<JobResult> => {
  const response = await fetch(joinUrl(getApiBaseUrl(), `/api/v1/jobs/${jobId}/result`));
  if (!response.ok) {
    throw new Error(await parseError(response, 'Failed to fetch job result'));
  }
  return response.json();
};

export const downloadFile = async (path: string): Promise<Blob> => {
  const response = await fetch(getFileUrl(path));
  if (!response.ok) {
    throw new Error(await parseError(response, 'Failed to download file'));
  }
  return response.blob();
};

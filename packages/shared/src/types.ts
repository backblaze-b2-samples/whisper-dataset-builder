export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Dataset builder ---

export type JobStatus =
  | "queued"
  | "loading"
  | "detecting"
  | "filtering"
  | "transcribing"
  | "packaging"
  | "done"
  | "error";

export type VadEngine = "auto" | "pyannote" | "energy";
export type WhisperModel = "tiny" | "base" | "small";
export type Layout = "ljspeech" | "hf_audiofolder";
export type DatasetStatus = "draft" | "building" | "ready" | "error";

export interface DatasetConfig {
  source_key: string;
  vad_engine: VadEngine;
  whisper_model: WhisperModel;
  language: string;
  layout: Layout;
  min_clip_sec: number;
  max_clip_sec: number;
  min_snr_db: number;
}

export interface Clip {
  clip_id: string;
  wav_key: string;
  start: number;
  end: number;
  duration: number;
  snr_db: number;
  transcript: string;
}

export interface DatasetStats {
  source_clips_detected: number;
  clips_kept: number;
  clips_dropped: number;
  total_clip_seconds: number;
  write_amplification: number;
  vad_engine_used: string;
  language: string | null;
}

export interface Dataset {
  id: string;
  name: string;
  description: string;
  status: DatasetStatus;
  config: DatasetConfig;
  stats: DatasetStats;
  clips: Clip[];
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface DatasetSummary {
  id: string;
  name: string;
  description: string;
  status: DatasetStatus;
  source_key: string;
  layout: Layout;
  clips_kept: number;
  total_clip_seconds: number;
  write_amplification: number;
  created_at: string;
  updated_at: string;
}

export interface BuildJob {
  id: string;
  dataset_id: string;
  status: JobStatus;
  progress: number;
  message: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface DatasetStatsSummary {
  recordings_ingested: number;
  datasets_built: number;
  total_clips: number;
  total_clip_hours: number;
  avg_write_amplification: number;
}

export interface SourceRecording {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  uploaded_at: string;
}

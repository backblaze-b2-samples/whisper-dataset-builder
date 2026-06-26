"use client";

import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useClipPreviewUrl } from "@/lib/queries";
import type { Clip } from "@whisper-dataset-builder/shared";

export function ClipRow({
  datasetId,
  clip,
  playing,
  onPlay,
  timecode,
}: {
  datasetId: string;
  clip: Clip;
  playing: boolean;
  onPlay: () => void;
  timecode: string;
}) {
  // Fetch the presigned audio URL once the user expands this clip for playback.
  const { data, isLoading } = useClipPreviewUrl(datasetId, clip.clip_id, playing);
  const audioUrl = data?.url;

  return (
    <div className="flex flex-col gap-2 p-4 sm:flex-row sm:items-start sm:gap-4">
      <div className="flex shrink-0 flex-col gap-1 sm:w-44">
        <span className="font-mono text-xs text-muted-foreground">
          {clip.clip_id}
        </span>
        <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
          {timecode}
        </span>
        <div className="flex flex-wrap gap-1.5 pt-0.5">
          <Badge variant="outline" className="text-[10px]">
            {clip.duration.toFixed(1)}s
          </Badge>
          <Badge variant="outline" className="text-[10px]">
            {clip.snr_db.toFixed(0)} dB
          </Badge>
        </div>
        {playing ? (
          isLoading || !audioUrl ? (
            <span className="flex items-center gap-1.5 pt-1 text-xs text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" /> Loading audio…
            </span>
          ) : (
            // Native player paints once the presigned URL resolves.
            <audio controls autoPlay src={audioUrl} className="mt-1 h-8 w-full max-w-[220px]" />
          )
        ) : (
          <button
            type="button"
            onClick={onPlay}
            className="mt-1 self-start text-xs font-medium text-primary hover:underline"
          >
            ▶ Play clip
          </button>
        )}
      </div>
      <p className="flex-1 text-sm leading-relaxed">{clip.transcript}</p>
    </div>
  );
}

"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  ArrowLeft,
  AudioLines,
  Layers,
  Pencil,
  Play,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import {
  useDataset,
  useBuildJobs,
  useBuildDataset,
  useDatasetSnippet,
} from "@/lib/queries";
import { formatDuration, formatTimestamp, layoutLabel } from "@/lib/dataset-format";
import { ClipRow } from "./clip-row";

export function DatasetDetail({ datasetId }: { datasetId: string }) {
  const { data: ds, isLoading, error, refetch } = useDataset(datasetId);
  const { data: jobs = [] } = useBuildJobs(true);
  const buildMutation = useBuildDataset();
  const { data: snippetData } = useDatasetSnippet(
    datasetId,
    ds?.status === "ready",
  );
  const [playingId, setPlayingId] = useState<string | null>(null);

  const job = jobs.find((j) => j.dataset_id === datasetId);
  const busy =
    ds?.status === "building" ||
    (!!job && job.status !== "done" && job.status !== "error");

  const handleBuild = () => {
    buildMutation.mutate(datasetId, {
      onSuccess: () => toast.success("Build started"),
      onError: (err) => toast.error(err.message || "Failed to start build"),
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }
  if (error || !ds) {
    return <ErrorState error={error ?? new Error("Not found")} onRetry={() => refetch()} />;
  }

  const stats = ds.stats;

  return (
    <div className="space-y-6">
      <div className="animate-fade-in border-b border-border pb-5">
        <Button asChild variant="ghost" size="sm" className="h-7 -ml-2 mb-2 text-xs">
          <Link href="/datasets">
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Datasets
          </Link>
        </Button>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="page-title flex items-center gap-2">
              <AudioLines className="h-5 w-5 text-muted-foreground" />
              {ds.name}
            </h1>
            {ds.description && (
              <p className="text-sm text-muted-foreground mt-1.5">{ds.description}</p>
            )}
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
              <Badge variant="outline">{layoutLabel(ds.config.layout)}</Badge>
              <Badge variant="outline" className="capitalize">{ds.status}</Badge>
              {busy && job && (
                <Badge variant="secondary" className="gap-1 capitalize">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  {job.status} {Math.round(job.progress * 100)}%
                </Badge>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button asChild variant="outline" size="sm" className="h-8">
              <Link href={`/datasets/${ds.id}/edit`}>
                <Pencil className="h-3.5 w-3.5" />
                Edit
              </Link>
            </Button>
            <Button size="sm" className="h-8" disabled={busy} onClick={handleBuild}>
              <Play className="h-3.5 w-3.5" />
              {ds.status === "ready" ? "Rebuild" : "Build"}
            </Button>
          </div>
        </div>
      </div>

      {ds.status === "error" && ds.error && (
        <Card className="border-destructive/40">
          <CardContent className="p-4 text-sm text-destructive">
            Build failed: {ds.error}
          </CardContent>
        </Card>
      )}

      {/* Stats — the write-amplification headline */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Clips kept", value: stats.clips_kept },
          {
            label: "Write amplification",
            value: `${stats.write_amplification.toFixed(0)}×`,
          },
          { label: "Clip-time", value: formatDuration(stats.total_clip_seconds) },
          { label: "VAD engine", value: stats.vad_engine_used || ds.config.vad_engine },
        ].map((s) => (
          <Card key={s.label} className="card-hover">
            <CardHeader className="pt-4 pb-2 px-4">
              <CardTitle className="text-xs font-semibold text-muted-foreground">
                {s.label}
              </CardTitle>
            </CardHeader>
            <CardContent className="pb-5 px-4">
              <div className="stat-value">{s.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {snippetData?.snippet && (
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title flex items-center gap-2">
              <Layers className="h-4 w-4 text-muted-foreground" />
              Load directly from B2
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5">
            <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs font-mono">
              {snippetData.snippet}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* Clip ↔ transcript pairs with in-browser audio playback */}
      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">
            Clips ({ds.clips.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {ds.clips.length === 0 ? (
            <EmptyState
              icon={AudioLines}
              title="No clips yet"
              description={
                ds.status === "draft"
                  ? "Run a build to segment, filter, transcribe, and package this recording."
                  : "This build produced no clips that passed the quality filters."
              }
            />
          ) : (
            <div className="divide-y divide-border">
              {ds.clips.map((clip) => (
                <ClipRow
                  key={clip.clip_id}
                  datasetId={ds.id}
                  clip={clip}
                  playing={playingId === clip.clip_id}
                  onPlay={() => setPlayingId(clip.clip_id)}
                  timecode={`${formatTimestamp(clip.start)}–${formatTimestamp(clip.end)}`}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

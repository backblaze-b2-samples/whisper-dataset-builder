"use client";

import { AudioLines, Database, Scissors, Clock, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { useDatasetStats } from "@/lib/queries";

export function DatasetStatsCards() {
  const { data: stats, isLoading, error, refetch } = useDatasetStats();

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const cards = [
    {
      title: "Recordings ingested",
      value: stats?.recordings_ingested ?? 0,
      icon: AudioLines,
    },
    { title: "Datasets built", value: stats?.datasets_built ?? 0, icon: Database },
    { title: "Total clips", value: stats?.total_clips ?? 0, icon: Scissors },
    {
      title: "Total clip-hours",
      value: stats?.total_clip_hours ?? 0,
      icon: Clock,
    },
    {
      title: "Avg write-amplification",
      value: stats ? `${stats.avg_write_amplification.toFixed(1)}×` : "0×",
      icon: TrendingUp,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {cards.map((card, i) => (
        <Card
          key={card.title}
          className={`card-hover animate-fade-in-up stagger-${i + 1}`}
        >
          <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
            <CardTitle className="text-xs font-semibold text-muted-foreground">
              {card.title}
            </CardTitle>
            <div className="stat-icon-wrap">
              <card.icon className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pb-5 px-4">
            {isLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="stat-value">{card.value}</div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

import Link from "next/link";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { DatasetsList } from "@/components/datasets/datasets-list";

export default function DatasetsPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Datasets</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Training-ready speech datasets built from your B2 recordings. Each
            build fans one recording out into many labeled clip/transcript pairs
            under its own <code className="font-mono text-xs">datasets/&lt;id&gt;/</code>{" "}
            prefix.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/datasets/new">
            <Plus className="h-3.5 w-3.5" />
            New dataset
          </Link>
        </Button>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <DatasetsList />
      </div>
    </div>
  );
}

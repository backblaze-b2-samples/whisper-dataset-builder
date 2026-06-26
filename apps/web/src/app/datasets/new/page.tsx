import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { DatasetForm } from "@/components/datasets/dataset-form";

export default function NewDatasetPage() {
  return (
    <div className="space-y-6">
      <div className="animate-fade-in border-b border-border pb-5">
        <Button asChild variant="ghost" size="sm" className="h-7 -ml-2 mb-2 text-xs">
          <Link href="/datasets">
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Datasets
          </Link>
        </Button>
        <h1 className="page-title">New dataset</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Pick a source recording and pipeline settings. The defaults are tuned
          for a quick, no-token test run — you can build right after creating.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <DatasetForm />
      </div>
    </div>
  );
}

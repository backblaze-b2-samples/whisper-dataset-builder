"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useSources, useCreateDataset, useUpdateDataset } from "@/lib/queries";
import type { Dataset } from "@whisper-dataset-builder/shared";

const LANGUAGES = ["auto", "en", "es", "fr", "de", "pt", "it", "ja", "zh"];

const schema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters").max(80),
  description: z.string().max(280).optional(),
  source_key: z.string().min(1, "Pick a source recording"),
  vad_engine: z.enum(["auto", "pyannote", "energy"]),
  whisper_model: z.enum(["tiny", "base", "small"]),
  language: z.string().min(1),
  layout: z.enum(["ljspeech", "hf_audiofolder"]),
  min_clip_sec: z.coerce.number().positive().max(60),
  max_clip_sec: z.coerce.number().positive().max(120),
  min_snr_db: z.coerce.number().min(0).max(60),
});

type FormValues = z.infer<typeof schema>;

const CREATE_DEFAULTS: FormValues = {
  name: "",
  description: "",
  source_key: "",
  vad_engine: "auto",
  whisper_model: "base",
  language: "auto",
  layout: "ljspeech",
  min_clip_sec: 1.0,
  max_clip_sec: 20.0,
  min_snr_db: 10,
};

function fromDataset(ds: Dataset): FormValues {
  return {
    name: ds.name,
    description: ds.description,
    source_key: ds.config.source_key,
    vad_engine: ds.config.vad_engine,
    whisper_model: ds.config.whisper_model,
    language: ds.config.language,
    layout: ds.config.layout,
    min_clip_sec: ds.config.min_clip_sec,
    max_clip_sec: ds.config.max_clip_sec,
    min_snr_db: ds.config.min_snr_db,
  };
}

export function DatasetForm({ dataset }: { dataset?: Dataset }) {
  const router = useRouter();
  const isEdit = !!dataset;
  // Config is locked once a build has materialized clips.
  const configLocked = isEdit && dataset.status !== "draft";
  const { data: sources = [] } = useSources();
  const create = useCreateDataset();
  const update = useUpdateDataset(dataset?.id ?? "");
  const [submitting, setSubmitting] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: isEdit ? fromDataset(dataset) : CREATE_DEFAULTS,
  });

  const onSubmit = async (values: FormValues) => {
    setSubmitting(true);
    const config = {
      source_key: values.source_key,
      vad_engine: values.vad_engine,
      whisper_model: values.whisper_model,
      language: values.language,
      layout: values.layout,
      min_clip_sec: values.min_clip_sec,
      max_clip_sec: values.max_clip_sec,
      min_snr_db: values.min_snr_db,
    };
    try {
      if (isEdit) {
        await update.mutateAsync({
          name: values.name,
          description: values.description ?? "",
          // Don't send config once it's locked (server would 409).
          ...(configLocked ? {} : { config }),
        });
        toast.success("Dataset updated");
        router.push(`/datasets/${dataset.id}`);
      } else {
        const created = await create.mutateAsync({
          name: values.name,
          description: values.description ?? "",
          config,
        });
        toast.success("Dataset created — run a build to generate clips");
        router.push(`/datasets/${created.id}`);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Details</CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. Field recordings — Quechua v1" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="What this corpus is for (optional)"
                      className="resize-none"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Build configuration</CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-6">
            {configLocked && (
              <p className="text-sm text-[var(--attention)]">
                Build config is locked because this dataset has already produced
                clips. Create a new dataset to use different settings.
              </p>
            )}

            <FormField
              control={form.control}
              name="source_key"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Source recording</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    value={field.value}
                    disabled={configLocked}
                  >
                    <FormControl>
                      <SelectTrigger className="w-full max-w-md">
                        <SelectValue placeholder="Select an uploaded recording…" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {sources.length === 0 ? (
                        <SelectItem value="__none" disabled>
                          No recordings — upload one first
                        </SelectItem>
                      ) : (
                        sources.map((s) => (
                          <SelectItem key={s.key} value={s.key}>
                            {s.filename} ({s.size_human})
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    Recordings you uploaded land under the <code>sources/</code>{" "}
                    prefix on B2.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid gap-6 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="vad_engine"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>VAD engine</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      value={field.value}
                      disabled={configLocked}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="auto">auto</SelectItem>
                        <SelectItem value="pyannote">pyannote</SelectItem>
                        <SelectItem value="energy">energy</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Default <strong>auto</strong>: uses pyannote when an
                      HF_TOKEN is set, else the token-free energy fallback.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="whisper_model"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Whisper model</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      value={field.value}
                      disabled={configLocked}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="tiny">tiny</SelectItem>
                        <SelectItem value="base">base</SelectItem>
                        <SelectItem value="small">small</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Default <strong>base</strong> — good CPU/quality balance.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="language"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Language</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      value={field.value}
                      disabled={configLocked}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {LANGUAGES.map((l) => (
                          <SelectItem key={l} value={l}>
                            {l}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Default <strong>auto</strong> — Whisper detects it.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="layout"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Dataset layout</FormLabel>
                    <FormControl>
                      <RadioGroup
                        onValueChange={field.onChange}
                        value={field.value}
                        className="flex gap-6 pt-1"
                        disabled={configLocked}
                      >
                        <label className="flex items-center gap-2 text-sm cursor-pointer">
                          <RadioGroupItem value="ljspeech" />
                          LJSpeech
                        </label>
                        <label className="flex items-center gap-2 text-sm cursor-pointer">
                          <RadioGroupItem value="hf_audiofolder" />
                          HF audiofolder
                        </label>
                      </RadioGroup>
                    </FormControl>
                    <FormDescription>
                      Default <strong>LJSpeech</strong> (metadata.csv).
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid gap-6 sm:grid-cols-3">
              <FormField
                control={form.control}
                name="min_clip_sec"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Min clip (s)</FormLabel>
                    <FormControl>
                      <Input type="number" step="0.5" min={0} disabled={configLocked} {...field} />
                    </FormControl>
                    <FormDescription>Default 1.0</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="max_clip_sec"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Max clip (s)</FormLabel>
                    <FormControl>
                      <Input type="number" step="0.5" min={0} disabled={configLocked} {...field} />
                    </FormControl>
                    <FormDescription>Default 20.0</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="min_snr_db"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Min SNR (dB)</FormLabel>
                    <FormControl>
                      <Input type="number" step="1" min={0} disabled={configLocked} {...field} />
                    </FormControl>
                    <FormDescription>Default 10</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
          </CardContent>
        </Card>

        <div className="flex items-center justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Saving…" : isEdit ? "Save changes" : "Create dataset"}
          </Button>
        </div>
      </form>
    </Form>
  );
}

"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
import { DangerZone } from "./danger-zone";

// These are the defaults the dataset create form pre-selects. They mirror the
// backend pipeline knobs in services/api/app/config/settings.py. The form is
// the exemplar for the dataset create/edit forms: selectors for finite fields,
// number inputs for bounds.
const settingsSchema = z.object({
  vadEngine: z.enum(["auto", "pyannote", "energy"]),
  whisperModel: z.enum(["tiny", "base", "small"]),
  device: z.enum(["auto", "cpu", "cuda", "mps"]),
  layout: z.enum(["ljspeech", "hf_audiofolder"]),
  minClipSec: z.string().regex(/^\d+(\.\d+)?$/, "Must be a number"),
  maxClipSec: z.string().regex(/^\d+(\.\d+)?$/, "Must be a number"),
  minSnrDb: z.string().regex(/^\d+(\.\d+)?$/, "Must be a number"),
});

type SettingsValues = z.infer<typeof settingsSchema>;

const defaultValues: SettingsValues = {
  vadEngine: "auto",
  whisperModel: "base",
  device: "auto",
  layout: "ljspeech",
  minClipSec: "1.0",
  maxClipSec: "20.0",
  minSnrDb: "10",
};

export function SettingsForm() {
  const [submitting, setSubmitting] = useState(false);
  const form = useForm<SettingsValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues,
  });

  const onSubmit = async (values: SettingsValues) => {
    setSubmitting(true);
    // Demo-only — these defaults live in .env on the server. Wire to a real
    // settings endpoint when you add one.
    await new Promise((r) => setTimeout(r, 400));
    setSubmitting(false);
    toast.success("Pipeline defaults saved", {
      description: `VAD ${values.vadEngine} · Whisper ${values.whisperModel}`,
    });
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Pipeline defaults</CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-6">
            <div className="grid gap-6 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="vadEngine"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>VAD engine</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
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
                      auto uses pyannote when HF_TOKEN is set, else the
                      token-free energy fallback.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="whisperModel"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Whisper model</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
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
                    <FormDescription>Larger = slower but more accurate.</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="device"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Device</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="auto">auto</SelectItem>
                        <SelectItem value="cpu">cpu</SelectItem>
                        <SelectItem value="cuda">cuda</SelectItem>
                        <SelectItem value="mps">mps</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      auto picks CUDA → Apple MPS → CPU. faster-whisper has no
                      MPS backend, so it maps MPS → CPU.
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
                    <FormLabel>Default layout</FormLabel>
                    <FormControl>
                      <RadioGroup
                        onValueChange={field.onChange}
                        value={field.value}
                        className="flex gap-6 pt-1"
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
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid gap-6 sm:grid-cols-3">
              <FormField
                control={form.control}
                name="minClipSec"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Min clip (s)</FormLabel>
                    <FormControl>
                      <Input type="number" step="0.5" className="font-mono tabular-nums" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="maxClipSec"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Max clip (s)</FormLabel>
                    <FormControl>
                      <Input type="number" step="0.5" className="font-mono tabular-nums" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="minSnrDb"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Min SNR (dB)</FormLabel>
                    <FormControl>
                      <Input type="number" step="1" className="font-mono tabular-nums" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
          </CardContent>
        </Card>

        <DangerZone />

        <div className="flex items-center justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => form.reset(defaultValues)}
          >
            Reset
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : "Save changes"}
          </Button>
        </div>
      </form>
    </Form>
  );
}

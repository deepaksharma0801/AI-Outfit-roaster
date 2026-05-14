"use client";

import {
  Activity,
  Camera,
  Check,
  Flame,
  ImagePlus,
  Loader2,
  PanelRight,
  RefreshCw,
  Sparkles,
  Trash2,
  Upload,
  Zap,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { analyzeFits, demoAnalyze, fetchHistory, fetchStyleHistory } from "@/lib/api";
import type { OutfitRecord, StyleHistory } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { cn, scoreLabel } from "@/lib/utils";

type FitUpload = {
  id: string;
  file: File;
  previewUrl: string;
};

const userId = "demo-user";

export function DripJudgeApp() {
  const [uploads, setUploads] = useState<FitUpload[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [records, setRecords] = useState<OutfitRecord[]>([]);
  const [history, setHistory] = useState<StyleHistory | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState("Ready");
  const [cameraOpen, setCameraOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const activeRecord = useMemo(() => {
    return records.find((record) => record.id === activeId) ?? records[0] ?? null;
  }, [records, activeId]);

  const addFiles = useCallback(async (fileList: FileList | File[]) => {
    const imageFiles = Array.from(fileList).filter((file) => file.type.startsWith("image/"));
    const compressed = await Promise.all(imageFiles.map(compressImage));
    const nextUploads = compressed.map((file) => ({
      id: crypto.randomUUID(),
      file,
      previewUrl: URL.createObjectURL(file),
    }));

    setUploads((current) => [...nextUploads, ...current].slice(0, 6));
    setStatusText(nextUploads.length > 1 ? "Fits loaded" : "Fit loaded");
  }, []);

  useEffect(() => {
    void refreshHistory();
  }, []);

  async function refreshHistory() {
    const [historyRecords, summary] = await Promise.all([
      fetchHistory(userId).catch(() => []),
      fetchStyleHistory(userId).catch(() => null),
    ]);
    if (historyRecords.length) {
      setRecords(historyRecords);
      setActiveId((current) => current ?? historyRecords[0]?.id ?? null);
    }
    setHistory(summary);
  }

  async function runAnalysis() {
    if (!uploads.length) return;

    setLoading(true);
    setStatusText("Judging the fit");

    try {
      const response = await analyzeFits(
        uploads.map((upload) => upload.file),
        userId,
      );
      setRecords(response.results);
      setActiveId(response.results[0]?.id ?? null);
      setStatusText("Analysis complete");
      await refreshHistory();
    } catch {
      const response = demoAnalyze(uploads);
      setRecords(response.results);
      setActiveId(response.results[0]?.id ?? null);
      setStatusText("Demo analysis loaded");
    } finally {
      setLoading(false);
    }
  }

  function removeUpload(id: string) {
    setUploads((current) => {
      const target = current.find((upload) => upload.id === id);
      if (target) URL.revokeObjectURL(target.previewUrl);
      return current.filter((upload) => upload.id !== id);
    });
  }

  return (
    <main className="min-h-screen overflow-hidden text-bone">
      <div className="grid-texture fixed inset-0 opacity-35" />
      <div className="relative mx-auto flex min-h-screen w-full max-w-[1600px] flex-col px-4 py-4 sm:px-6 lg:px-8">
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-bone/10 pb-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-acid text-ink">
              <Flame size={22} aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <h1 className="truncate text-xl font-black tracking-normal sm:text-2xl">DripJudge AI</h1>
              <p className="truncate text-xs font-medium uppercase text-bone/55">Multimodal fit intelligence</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <SystemPill label={statusText} active={loading} />
            <Button variant="ghost" size="icon" title="Refresh history" onClick={() => void refreshHistory()}>
              <RefreshCw size={18} aria-hidden="true" />
            </Button>
          </div>
        </header>

        <section className="grid flex-1 grid-cols-1 gap-4 xl:grid-cols-[360px_minmax(0,1fr)_390px]">
          <aside className="panel rounded-lg p-4">
            <UploadDock
              dragging={dragging}
              uploads={uploads}
              loading={loading}
              onDragState={setDragging}
              onFiles={addFiles}
              onAnalyze={() => void runAnalysis()}
              onOpenPicker={() => fileInputRef.current?.click()}
              onOpenCamera={() => setCameraOpen(true)}
              onRemove={removeUpload}
            />
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(event) => {
                if (event.target.files) void addFiles(event.target.files);
                event.currentTarget.value = "";
              }}
            />
          </aside>

          <motion.section layout className="panel relative min-h-[560px] overflow-hidden rounded-lg">
            <FitStage record={activeRecord} loading={loading} />
          </motion.section>

          <aside className="flex min-h-[620px] flex-col gap-4">
            <InsightPanel record={activeRecord} />
            <HistoryPanel history={history} records={records} activeId={activeId} onSelect={setActiveId} />
          </aside>
        </section>
      </div>

      <CameraModal
        open={cameraOpen}
        onClose={() => setCameraOpen(false)}
        onCapture={(file) => void addFiles([file])}
      />
    </main>
  );
}

function UploadDock({
  dragging,
  uploads,
  loading,
  onDragState,
  onFiles,
  onAnalyze,
  onOpenPicker,
  onOpenCamera,
  onRemove,
}: {
  dragging: boolean;
  uploads: FitUpload[];
  loading: boolean;
  onDragState: (dragging: boolean) => void;
  onFiles: (files: FileList | File[]) => Promise<void>;
  onAnalyze: () => void;
  onOpenPicker: () => void;
  onOpenCamera: () => void;
  onRemove: (id: string) => void;
}) {
  return (
    <div className="flex h-full min-h-[560px] flex-col">
      <div
        className={cn(
          "relative flex min-h-[220px] flex-col items-center justify-center rounded-lg border border-dashed p-5 text-center transition",
          dragging ? "border-acid bg-acid/10" : "border-bone/20 bg-bone/[0.03]",
        )}
        onDragEnter={(event) => {
          event.preventDefault();
          onDragState(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => onDragState(false)}
        onDrop={(event) => {
          event.preventDefault();
          onDragState(false);
          void onFiles(event.dataTransfer.files);
        }}
      >
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-md bg-bone text-ink">
          <ImagePlus size={26} aria-hidden="true" />
        </div>
        <h2 className="text-lg font-black">Drop fits</h2>
        <p className="mt-1 max-w-[260px] text-sm leading-6 text-bone/62">JPEG, PNG, WebP. Batch up to six looks.</p>
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          <Button type="button" variant="accent" onClick={onOpenPicker}>
            <Upload size={17} aria-hidden="true" />
            Upload
          </Button>
          <Button type="button" variant="dark" onClick={onOpenCamera}>
            <Camera size={17} aria-hidden="true" />
            Camera
          </Button>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between">
        <h3 className="text-sm font-bold uppercase text-bone/60">Queue</h3>
        <span className="font-mono text-xs text-bone/45">{uploads.length}/6</span>
      </div>

      <div className="mt-3 grid gap-2">
        <AnimatePresence initial={false}>
          {uploads.map((upload) => (
            <motion.div
              key={upload.id}
              layout
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="flex items-center gap-3 rounded-md border border-bone/10 bg-bone/[0.04] p-2"
            >
              <img
                src={upload.previewUrl}
                alt="Queued outfit"
                className="h-14 w-14 rounded-md object-cover"
              />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">{upload.file.name}</p>
                <p className="font-mono text-xs text-bone/45">{Math.round(upload.file.size / 1024)} KB</p>
              </div>
              <Button type="button" variant="ghost" size="icon" title="Remove" onClick={() => onRemove(upload.id)}>
                <Trash2 size={16} aria-hidden="true" />
              </Button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <div className="mt-auto pt-4">
        <Button type="button" className="h-12 w-full" variant="default" disabled={!uploads.length || loading} onClick={onAnalyze}>
          {loading ? <Loader2 className="animate-spin" size={18} aria-hidden="true" /> : <Zap size={18} aria-hidden="true" />}
          Judge Fit
        </Button>
      </div>
    </div>
  );
}

function FitStage({ record, loading }: { record: OutfitRecord | null; loading: boolean }) {
  const analysis = record?.analysis;
  const score = analysis?.drip_score ?? 0;

  return (
    <div className="relative grid min-h-[560px] grid-cols-1 lg:grid-cols-[minmax(0,1fr)_260px]">
      <div className="relative flex min-h-[420px] items-center justify-center overflow-hidden bg-[#101820]">
        <div className="scanline absolute inset-0 opacity-20" />
        {record?.image_preview_url ? (
          <motion.img
            key={record.id}
            src={record.image_preview_url}
            alt="Analyzed outfit"
            initial={{ opacity: 0.2, scale: 1.02 }}
            animate={{ opacity: 1, scale: 1 }}
            className="relative z-10 h-full max-h-[760px] w-full object-contain"
          />
        ) : (
          <EmptyStage loading={loading} />
        )}
      </div>

      <div className="border-t border-bone/10 bg-ink/80 p-4 lg:border-l lg:border-t-0">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase text-bone/55">Drip score</span>
          <Activity size={18} className="text-cyan" aria-hidden="true" />
        </div>
        <div className="mt-4 flex items-end gap-2">
          <span className="text-6xl font-black">{score ? score.toFixed(1) : "--"}</span>
          <span className="pb-2 text-sm font-bold text-bone/45">/10</span>
        </div>
        <p className="mt-2 text-sm font-semibold text-acid">{score ? scoreLabel(score) : "Awaiting fit"}</p>

        <div className="mt-6 h-3 overflow-hidden rounded-full bg-bone/10">
          <motion.div
            className="h-full rounded-full bg-acid"
            initial={false}
            animate={{ width: `${Math.min(score * 10, 100)}%` }}
          />
        </div>

        <div className="mt-6 grid grid-cols-2 gap-2">
          <Metric label="Style" value={analysis?.style ?? "--"} />
          <Metric label="Aesthetic" value={analysis?.aesthetic ?? "--"} />
          <Metric label="Confidence" value={analysis ? `${Math.round(analysis.confidence * 100)}%` : "--"} />
          <Metric label="Items" value={analysis ? String(analysis.detected_items.length) : "--"} />
        </div>

        <div className="mt-6 flex flex-wrap gap-2">
          {(analysis?.color_palette ?? ["#181d24", "#f5f0e8", "#7de2d1", "#ff6f61", "#c6ff4a"]).map((color) => (
            <span
              key={color}
              title={color}
              className="h-8 w-8 rounded-md border border-bone/20"
              style={{ backgroundColor: color }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function EmptyStage({ loading }: { loading: boolean }) {
  return (
    <div className="relative z-10 flex w-full max-w-md flex-col items-center px-6 text-center">
      <div className="mb-5 grid h-36 w-28 place-items-center rounded-lg border border-bone/15 bg-bone/[0.04]">
        {loading ? <Loader2 className="animate-spin text-acid" size={40} /> : <Sparkles className="text-acid" size={40} />}
      </div>
      <h2 className="text-2xl font-black">Fit canvas</h2>
      <p className="mt-2 text-sm leading-6 text-bone/60">Load an outfit to start the roast, score, and styling pass.</p>
    </div>
  );
}

function InsightPanel({ record }: { record: OutfitRecord | null }) {
  const analysis = record?.analysis;

  return (
    <section className="panel rounded-lg p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-black uppercase text-bone/60">Judgement</h2>
        <PanelRight size={18} className="text-coral" aria-hidden="true" />
      </div>

      {analysis ? (
        <div className="space-y-4">
          <div className="rounded-md bg-coral p-4 text-ink">
            <p className="text-sm font-black uppercase">Roast</p>
            <p className="mt-2 text-lg font-black leading-6">{analysis.roast}</p>
          </div>

          <p className="text-sm leading-6 text-bone/72">{analysis.explanation}</p>

          <div>
            <h3 className="mb-2 text-xs font-bold uppercase text-bone/48">Detected</h3>
            <div className="grid gap-2">
              {analysis.detected_items.map((item) => (
                <div key={`${item.category}-${item.name}`} className="flex items-center gap-3 rounded-md bg-bone/[0.04] p-2">
                  <span className="h-8 w-8 rounded-md border border-bone/20" style={{ backgroundColor: item.color }} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{item.name}</p>
                    <p className="text-xs text-bone/45">{item.category} · {Math.round(item.confidence * 100)}%</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <InsightList title="Fixes" items={analysis.issues.map((issue) => `${issue.title}: ${issue.fix}`)} tone="issue" />
          <InsightList title="Wins" items={analysis.strengths.map((strength) => strength.detail)} tone="win" />
          <InsightList title="Upgrades" items={analysis.recommendations.map((item) => item.title)} tone="upgrade" />
        </div>
      ) : (
        <div className="grid min-h-[360px] place-items-center text-center text-sm text-bone/55">
          <span>Analysis appears here.</span>
        </div>
      )}
    </section>
  );
}

function InsightList({ title, items, tone }: { title: string; items: string[]; tone: "issue" | "win" | "upgrade" }) {
  const toneClass = {
    issue: "bg-coral",
    win: "bg-cyan",
    upgrade: "bg-acid",
  }[tone];

  return (
    <div>
      <h3 className="mb-2 text-xs font-bold uppercase text-bone/48">{title}</h3>
      <div className="space-y-2">
        {items.slice(0, 3).map((item) => (
          <div key={item} className="flex gap-2 rounded-md bg-bone/[0.04] p-3">
            <span className={cn("mt-1 h-2.5 w-2.5 shrink-0 rounded-sm", toneClass)} />
            <p className="text-sm leading-5 text-bone/74">{item}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function HistoryPanel({
  history,
  records,
  activeId,
  onSelect,
}: {
  history: StyleHistory | null;
  records: OutfitRecord[];
  activeId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <section className="panel flex-1 rounded-lg p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-black uppercase text-bone/60">Style history</h2>
        <Check size={18} className="text-acid" aria-hidden="true" />
      </div>

      <div className="grid grid-cols-3 gap-2">
        <Metric label="Avg" value={history?.average_score ? history.average_score.toFixed(1) : "--"} />
        <Metric label="Best" value={history?.best_score ? history.best_score.toFixed(1) : "--"} />
        <Metric label="Fits" value={String(history?.total_outfits ?? records.length)} />
      </div>

      <div className="mt-4 flex h-24 items-end gap-2 rounded-md bg-bone/[0.04] p-3">
        {(history?.timeline.length ? history.timeline : records.map((record) => ({
          drip_score: record.analysis?.drip_score ?? 0,
          date: record.created_at,
          style: record.analysis?.style ?? "",
          aesthetic: record.analysis?.aesthetic ?? "",
        }))).slice(-12).map((point, index) => (
          <div key={`${point.date}-${index}`} className="flex flex-1 items-end">
            <div
              className="w-full rounded-t-sm bg-cyan"
              style={{ height: `${Math.max(8, point.drip_score * 8)}%` }}
              title={`${point.drip_score}/10`}
            />
          </div>
        ))}
      </div>

      <div className="mt-4 space-y-2">
        {records.slice(0, 4).map((record) => (
          <button
            type="button"
            key={record.id}
            onClick={() => onSelect(record.id)}
            className={cn(
              "flex w-full items-center gap-3 rounded-md border p-2 text-left transition",
              activeId === record.id ? "border-acid bg-acid/10" : "border-bone/10 bg-bone/[0.04] hover:bg-bone/[0.08]",
            )}
          >
            {record.image_preview_url ? (
              <img src={record.image_preview_url} alt="History outfit" className="h-12 w-12 rounded-md object-cover" />
            ) : (
              <div className="h-12 w-12 rounded-md bg-bone/10" />
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">{record.analysis?.style ?? record.status}</p>
              <p className="text-xs text-bone/45">{record.analysis?.aesthetic ?? "Processing"}</p>
            </div>
            <span className="font-mono text-sm font-bold text-acid">{record.analysis?.drip_score.toFixed(1) ?? "--"}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md border border-bone/10 bg-bone/[0.04] p-3">
      <p className="text-[10px] font-bold uppercase text-bone/45">{label}</p>
      <p className="mt-1 truncate text-sm font-black">{value}</p>
    </div>
  );
}

function SystemPill({ label, active }: { label: string; active: boolean }) {
  return (
    <div className="flex h-10 items-center gap-2 rounded-md border border-bone/10 bg-bone/[0.04] px-3">
      <span className={cn("h-2 w-2 rounded-full", active ? "animate-pulse bg-acid" : "bg-cyan")} />
      <span className="text-xs font-bold uppercase text-bone/65">{label}</span>
    </div>
  );
}

function CameraModal({
  open,
  onClose,
  onCapture,
}: {
  open: boolean;
  onClose: () => void;
  onCapture: (file: File) => void;
}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;

    let liveStream: MediaStream | null = null;
    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: "environment" }, audio: false })
      .then((nextStream) => {
        liveStream = nextStream;
        setStream(nextStream);
        if (videoRef.current) videoRef.current.srcObject = nextStream;
      })
      .catch(() => setError("Camera unavailable"));

    return () => {
      liveStream?.getTracks().forEach((track) => track.stop());
      setStream(null);
      setError(null);
    };
  }, [open]);

  async function capture() {
    const video = videoRef.current;
    if (!video) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const context = canvas.getContext("2d");
    if (!context) return;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.88));
    if (!blob) return;
    onCapture(new File([blob], `camera-fit-${Date.now()}.jpg`, { type: "image/jpeg" }));
    stream?.getTracks().forEach((track) => track.stop());
    onClose();
  }

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-50 grid place-items-center bg-ink/85 p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="panel w-full max-w-2xl overflow-hidden rounded-lg"
            initial={{ scale: 0.96, y: 16 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.96, y: 16 }}
          >
            <div className="flex items-center justify-between border-b border-bone/10 p-4">
              <h2 className="text-sm font-black uppercase text-bone/65">Camera</h2>
              <Button variant="ghost" size="sm" onClick={onClose}>Close</Button>
            </div>
            <div className="aspect-video bg-black">
              {error ? (
                <div className="grid h-full place-items-center text-sm text-bone/60">{error}</div>
              ) : (
                <video ref={videoRef} autoPlay playsInline muted className="h-full w-full object-cover" />
              )}
            </div>
            <div className="flex justify-end gap-2 p-4">
              <Button variant="accent" onClick={() => void capture()} disabled={Boolean(error)}>
                <Camera size={17} aria-hidden="true" />
                Capture
              </Button>
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

async function compressImage(file: File): Promise<File> {
  if (!file.type.startsWith("image/")) return file;

  const bitmap = await createImageBitmap(file).catch(() => null);
  if (!bitmap) return file;

  const maxSide = 1600;
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
  const width = Math.round(bitmap.width * scale);
  const height = Math.round(bitmap.height * scale);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) return file;

  context.drawImage(bitmap, 0, 0, width, height);
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.86));
  bitmap.close();
  if (!blob) return file;

  return new File([blob], file.name.replace(/\.[^.]+$/, ".jpg"), { type: "image/jpeg" });
}

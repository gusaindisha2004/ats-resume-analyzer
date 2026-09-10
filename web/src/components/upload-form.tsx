"use client";

import { useRef, useState, type DragEvent } from "react";
import { FileUp, Loader2, TriangleAlert, X } from "lucide-react";
import { analyzeResume, ApiError } from "@/lib/api";
import type { AnalysisResponse } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";

const MAX_BYTES = 5 * 1024 * 1024;
const ACCEPTED = [".pdf", ".docx"];

/** Client-side guard so obvious mistakes don't cost a round trip. The backend
 *  validates independently — this is convenience, not enforcement. */
function validateFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!ACCEPTED.some((ext) => name.endsWith(ext))) {
    return "Upload a PDF or DOCX file. Legacy .doc isn't supported — re-save it first.";
  }
  if (file.size > MAX_BYTES) {
    return `That file is ${(file.size / 1024 / 1024).toFixed(1)} MB. The limit is 5 MB.`;
  }
  if (file.size === 0) return "That file is empty.";
  return null;
}

export function UploadForm({
  onComplete,
}: {
  onComplete: (analysis: AnalysisResponse) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function selectFile(next: File | undefined) {
    if (!next) return;
    const problem = validateFile(next);
    setError(problem);
    setFile(problem ? null : next);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    selectFile(event.dataTransfer.files[0]);
  }

  async function handleSubmit() {
    if (!file) return;
    setPending(true);
    setError(null);
    try {
      onComplete(await analyzeResume(file, jobDescription.trim()));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not reach the analysis service. Is the backend running?",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardBody className="space-y-6">
          {/* Dropzone ------------------------------------------------- */}
          <div>
            <label className="mb-2 block text-sm font-medium">Resume</label>
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              className={cn(
                "rounded-lg border-2 border-dashed transition-colors",
                dragging
                  ? "border-primary bg-primary/5"
                  : "border-border bg-surface-muted/40",
              )}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".pdf,.docx"
                className="sr-only"
                onChange={(e) => selectFile(e.target.files?.[0])}
              />

              {file ? (
                <div className="flex items-center gap-3 px-4 py-4">
                  <FileUp className="size-5 shrink-0 text-primary" aria-hidden />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(file.size / 1024).toFixed(0)} KB
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => {
                      setFile(null);
                      if (inputRef.current) inputRef.current.value = "";
                    }}
                    aria-label="Remove file"
                  >
                    <X className="size-4" aria-hidden />
                  </Button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => inputRef.current?.click()}
                  className="flex w-full flex-col items-center gap-2 px-4 py-10 text-center"
                >
                  <FileUp
                    className="size-7 text-muted-foreground"
                    aria-hidden
                  />
                  <span className="text-sm font-medium">
                    Drop your resume here, or click to browse
                  </span>
                  <span className="text-xs text-muted-foreground">
                    PDF or DOCX, up to 5 MB
                  </span>
                </button>
              )}
            </div>
          </div>

          {/* Job description ------------------------------------------ */}
          <div>
            <label
              htmlFor="jd"
              className="mb-2 flex items-baseline justify-between text-sm font-medium"
            >
              Job description
              <span className="text-xs font-normal text-muted-foreground">
                Optional — unlocks keyword and semantic matching
              </span>
            </label>
            <textarea
              id="jd"
              rows={7}
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the full job posting here…"
              className="w-full resize-y rounded-lg border border-border bg-surface px-3 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-2 focus:outline-offset-0 focus:outline-primary"
            />
            {jobDescription.trim().length > 0 && (
              <p className="mt-1.5 text-xs text-muted-foreground">
                {jobDescription.trim().length.toLocaleString()} characters
              </p>
            )}
          </div>

          {error && (
            <div
              role="alert"
              className="flex gap-2.5 rounded-lg bg-rose-50 px-3 py-2.5 text-sm text-rose-800 dark:bg-rose-950/50 dark:text-rose-300"
            >
              <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
              <span>{error}</span>
            </div>
          )}

          <Button
            size="lg"
            className="w-full"
            disabled={!file || pending}
            onClick={handleSubmit}
          >
            {pending && <Loader2 className="size-4 animate-spin" aria-hidden />}
            {pending ? "Analyzing…" : "Analyze resume"}
          </Button>

          {pending && (
            <p className="text-center text-xs text-muted-foreground">
              Parsing the document and running the language models — this
              usually takes 10–30 seconds.
            </p>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

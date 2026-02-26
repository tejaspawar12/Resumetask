"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { uploadResumes, startRun } from "@/lib/api";

const MAX_FILES = 250;
const MAX_SIZE_MB = 10;

type Props = { runId: string; status: string; candidateCount: number };

export default function RunActions({ runId, status, candidateCount }: Props) {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [uploadResult, setUploadResult] = useState<{
    accepted: number;
    rejected: number;
    errors: { file: string; reason: string }[];
    duplicate_skipped: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canUpload = status === "pending" || status === "uploaded";
  const canStart = status === "uploaded" && candidateCount > 0;

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files?.length) return;
    if (files.length > MAX_FILES) {
      setError(`Max ${MAX_FILES} files at once.`);
      return;
    }
    setUploading(true);
    setError(null);
    setUploadResult(null);
    const list = Array.from(files);
    const data = await uploadResumes(runId, list);
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (data) {
      setUploadResult(data);
      router.refresh();
    } else {
      setError("Upload failed.");
    }
  }

  async function handleStart() {
    setStarting(true);
    setError(null);
    const ok = await startRun(runId);
    setStarting(false);
    if (ok) router.refresh();
    else setError("Failed to start run.");
  }

  return (
    <div className="space-y-4">
      {canUpload && (
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            multiple
            onChange={handleUpload}
            disabled={uploading}
            className="text-sm file:mr-2 file:py-2 file:px-3 file:rounded file:border-0 file:bg-blue-600 file:text-white file:cursor-pointer hover:file:bg-blue-700"
          />
          <span className="text-sm text-gray-500">
            PDF only, max {MAX_SIZE_MB} MB per file, max {MAX_FILES} files
          </span>
        </div>
      )}
      {uploading && <p className="text-sm text-gray-600">Uploading…</p>}
      {uploadResult && (
        <p className="text-sm text-gray-600">
          Accepted: {uploadResult.accepted}, rejected: {uploadResult.rejected}
          {uploadResult.duplicate_skipped > 0 && `, duplicates skipped: ${uploadResult.duplicate_skipped}`}
          {uploadResult.errors.length > 0 && (
            <span className="block mt-1 text-amber-700">
              {uploadResult.errors.map((e) => `${e.file}: ${e.reason}`).join("; ")}
            </span>
          )}
        </p>
      )}
      {canStart && (
        <button
          type="button"
          onClick={handleStart}
          disabled={starting}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
        >
          {starting ? "Starting…" : "Start evaluation"}
        </button>
      )}
      {status === "running" && (
        <p className="text-sm text-gray-600">Run is in progress. Refresh to see updates.</p>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}

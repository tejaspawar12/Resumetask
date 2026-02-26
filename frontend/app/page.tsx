"use client";

import {
  createRun,
  createDemoRun,
  uploadResumes,
  startRun,
} from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";

const MAX_FILES = 250;
const MAX_SIZE_MB = 10;

const JD_MAX_LENGTH = 8000;

export default function HomePage() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [jobDescription, setJobDescription] = useState("");
  const [useDemo, setUseDemo] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canRun = files.length > 0 || useDemo;

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const chosen = Array.from(e.target.files ?? []);
      const valid: File[] = [];
      for (const f of chosen) {
        if (f.size > MAX_SIZE_MB * 1024 * 1024) continue;
        if (f.type !== "application/pdf") continue;
        valid.push(f);
      }
      if (valid.length + files.length > MAX_FILES) {
        setFiles((prev) => [...prev, ...valid.slice(0, MAX_FILES - prev.length)]);
      } else {
        setFiles((prev) => [...prev, ...valid]);
      }
      setError(null);
    },
    [files.length]
  );

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const runEvaluation = async () => {
    if (!canRun) return;
    setBusy(true);
    setError(null);
    try {
      const jd = jobDescription.trim() ? jobDescription.trim().slice(0, JD_MAX_LENGTH) : undefined;
      if (useDemo) {
        const data = await createDemoRun(jd);
        if (data?.run_id) {
          router.push(`/runs/${data.run_id}`);
          return;
        }
        setError("Failed to create demo run. Is the backend running?");
        setBusy(false);
        return;
      }
      const create = await createRun(jd);
      if (!create?.run_id) {
        setError("Failed to create run. Is the backend running?");
        setBusy(false);
        return;
      }
      const runId = create.run_id;
      if (files.length > 0) {
        const up = await uploadResumes(runId, files);
        if (!up) {
          setError("Upload failed.");
          setBusy(false);
          return;
        }
      }
      const started = await startRun(runId);
      if (!started) {
        setError("Failed to start evaluation.");
        setBusy(false);
        return;
      }
      router.push(`/runs/${runId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setBusy(false);
    }
  };

  return (
    <main className="max-w-2xl mx-auto px-4 py-16">
      <h1 className="text-2xl font-semibold text-gray-900 mb-2">
        Rank 200+ candidates in minutes
      </h1>
      <p className="text-gray-600 mb-6">
        Upload resume PDFs, run the AI evaluation pipeline, and get a ranked
        shortlist with evidence and risk flags. Optionally paste a job description to rank against <em>this</em> role.
      </p>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Job description (optional)
          </label>
          <textarea
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the role description or key criteria. Leave blank to use default Senior Software Engineer criteria."
            maxLength={JD_MAX_LENGTH + 100}
            rows={4}
            disabled={busy}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
          />
          {jobDescription.length > JD_MAX_LENGTH && (
            <p className="mt-1 text-xs text-amber-600">Truncated to {JD_MAX_LENGTH} characters.</p>
          )}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Resume PDFs (max {MAX_FILES} files, {MAX_SIZE_MB} MB each)
          </label>
          <input
            type="file"
            accept="application/pdf"
            multiple
            onChange={handleFileChange}
            disabled={busy}
            className="block w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          {files.length > 0 && (
            <ul className="mt-2 space-y-1 text-sm text-gray-600">
              {files.map((f, i) => (
                <li key={i} className="flex items-center gap-2">
                  <span className="truncate flex-1">{f.name}</span>
                  <button
                    type="button"
                    onClick={() => removeFile(i)}
                    disabled={busy}
                    className="text-red-600 hover:underline disabled:opacity-50"
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => {
              setUseDemo((d) => !d);
              if (!useDemo) setFiles([]);
            }}
            disabled={busy}
            className="text-blue-600 hover:underline disabled:opacity-50"
          >
            Use demo dataset
          </button>
          {useDemo && (
            <span className="text-sm text-gray-500">
              Demo run will use 3 synthetic resumes.
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={runEvaluation}
          disabled={!canRun || busy}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {busy ? "Starting…" : "Run evaluation"}
        </button>
      </div>

      {error && (
        <p className="mt-4 text-sm text-red-600">{error}</p>
      )}
      <p className="mt-8 text-sm text-gray-500">
        After starting, you’ll be redirected to the run dashboard. The pipeline
        will extract text, build profiles, shortlist, and score candidates.
      </p>
    </main>
  );
}

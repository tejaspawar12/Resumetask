"use client";

import { getRunStatus } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const POLL_INTERVAL_MS = 2500;

type Props = {
  runId: string;
  initialStatus: string;
  initialMessage?: string | null;
  initialStep?: string | null;
};

export default function RunStatusPoller({
  runId,
  initialStatus,
  initialMessage,
  initialStep,
}: Props) {
  const router = useRouter();
  const [message, setMessage] = useState(initialMessage ?? null);
  const [step, setStep] = useState(initialStep ?? null);

  useEffect(() => {
    if (initialStatus !== "running") return;

    const interval = setInterval(async () => {
      const status = await getRunStatus(runId);
      if (!status) return;
      setMessage(status.message ?? null);
      setStep(status.step ?? null);
      if (status.status === "completed" || status.status === "failed") {
        clearInterval(interval);
        router.refresh();
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [runId, initialStatus, router]);

  if (initialStatus !== "running" && initialStatus !== "uploaded") return null;

  return (
    <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded text-sm text-amber-900">
      {initialStatus === "running" ? (
        <>
          <span className="font-medium">Running</span>
          {step && <span className="ml-2">— {step}</span>}
          {message && <p className="mt-1 text-amber-800">{message}</p>}
        </>
      ) : (
        <span>Uploaded. Start evaluation to run the pipeline.</span>
      )}
    </div>
  );
}

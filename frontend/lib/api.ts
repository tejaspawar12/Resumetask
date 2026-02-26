const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Run = {
  id: string;
  status: string;
  step?: string | null;
  progress?: number | null;
  message?: string | null;
  source: string;
  config?: Record<string, unknown> | null;
  candidate_ids?: string[] | null;
  top_5_percent_ids?: string[] | null;
  backup_ids?: string[] | null;
  role_criteria_text?: string | null;
  k_shortlist_used?: number | null;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type Candidate = {
  id: string;
  run_id: string;
  candidate_id: string;
  filename?: string | null;
  status: string;
  error?: string | null;
  extraction_error?: string | null;
  rank?: number | null;
  embedding_rank?: number | null;
  embedding_score?: number | null;
  shortlist_status?: string | null;
  confidence?: string | null;
  confidence_reason?: string | null;
  scores_with_evidence?: Record<string, unknown> | null;
  risk_flags?: string[] | null;
  why_shortlisted?: string[] | null;
  why_not_top_10?: string[] | null;
  structured_profile?: Record<string, unknown> | null;
  created_at?: string | null;
  updated_at?: string | null;
};

async function fetchApi<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_URL}${path}`, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export type CreateRunResponse = { run_id: string };

const JD_MAX_LENGTH = 8000;

export async function createRun(jobDescription?: string | null): Promise<CreateRunResponse | null> {
  try {
    const body =
      jobDescription && jobDescription.trim()
        ? { job_description: jobDescription.trim().slice(0, JD_MAX_LENGTH) }
        : {};
    const res = await fetch(`${API_URL}/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) return null;
    return (await res.json()) as CreateRunResponse;
  } catch {
    return null;
  }
}

export async function getRun(runId: string): Promise<Run | null> {
  return fetchApi<Run>(`/runs/${runId}`);
}

export type RunStatus = {
  status: string;
  step?: string | null;
  progress?: number | null;
  message?: string | null;
  error_message?: string | null;
};

export async function getRunStatus(runId: string): Promise<RunStatus | null> {
  return fetchApi<RunStatus>(`/runs/${runId}/status`);
}

export type CreateDemoRunResponse = { run_id: string };

export async function createDemoRun(jobDescription?: string | null): Promise<CreateDemoRunResponse | null> {
  try {
    const body =
      jobDescription && jobDescription.trim()
        ? { job_description: jobDescription.trim().slice(0, JD_MAX_LENGTH) }
        : {};
    const res = await fetch(`${API_URL}/runs/demo`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) return null;
    return (await res.json()) as CreateDemoRunResponse;
  } catch {
    return null;
  }
}

export async function getCandidates(runId: string): Promise<Candidate[] | null> {
  const data = await fetchApi<{ candidates?: Candidate[] }>(`/runs/${runId}/candidates`);
  return data?.candidates ?? null;
}

export async function getCandidate(
  runId: string,
  candidateId: string
): Promise<Candidate | null> {
  return fetchApi<Candidate>(`/runs/${runId}/candidates/${candidateId}`);
}

export type UploadResponse = {
  accepted: number;
  rejected: number;
  errors: { file: string; reason: string }[];
  duplicate_skipped: number;
};

export async function uploadResumes(
  runId: string,
  files: File[]
): Promise<UploadResponse | null> {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  try {
    const res = await fetch(`${API_URL}/runs/${runId}/upload`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) return null;
    return (await res.json()) as UploadResponse;
  } catch {
    return null;
  }
}

export async function startRun(runId: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/runs/${runId}/start`, { method: "POST" });
    return res.status === 202;
  } catch {
    return false;
  }
}

/** URL for HTML report (open in new tab or download). Phase 9. */
export function getReportUrl(runId: string, format = "html"): string {
  return `${API_URL}/runs/${runId}/report?format=${format}`;
}

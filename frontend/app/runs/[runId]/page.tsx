import { getRun, getCandidates, getReportUrl } from "@/lib/api";
import Link from "next/link";
import RunActions from "./RunActions";
import RunStatusPoller from "./RunStatusPoller";

type Props = { params: Promise<{ runId: string }> };

export default async function RunDashboardPage({ params }: Props) {
  const { runId } = await params;
  const [run, candidates] = await Promise.all([
    getRun(runId),
    getCandidates(runId),
  ]);

  if (!run) {
    return (
      <main className="max-w-2xl mx-auto px-4 py-16">
        <h1 className="text-2xl font-semibold text-gray-900 mb-2">Run not found</h1>
        <p className="text-gray-600 mb-4">No run with id: {runId}</p>
        <Link href="/" className="text-blue-600 hover:underline">
          Back to home
        </Link>
      </main>
    );
  }

  const candidateList = candidates ?? [];
  return (
    <main className="max-w-3xl mx-auto px-4 py-16">
      <Link href="/" className="text-blue-600 hover:underline text-sm mb-6 inline-block">
        ← Home
      </Link>
      <h1 className="text-2xl font-semibold text-gray-900 mb-2">Run dashboard</h1>
      <p className="text-gray-600 mb-2">
        Run ID: <code className="bg-gray-100 px-1 rounded text-sm">{runId}</code>
        {run.status && (
          <span className="ml-2 text-sm">Status: {run.status}</span>
        )}
      </p>
      {run.role_criteria_text && run.role_criteria_text.trim() && (
        <div className="mb-4 p-3 bg-gray-50 border border-gray-200 rounded text-sm">
          <span className="font-medium text-gray-700">Ranking against:</span>
          <p className="mt-1 text-gray-600 whitespace-pre-wrap">
            {run.role_criteria_text.trim().slice(0, 300)}
            {run.role_criteria_text.length > 300 ? "…" : ""}
          </p>
        </div>
      )}
      {(!run.role_criteria_text || !run.role_criteria_text.trim()) && run.status === "completed" && (
        <p className="mb-2 text-sm text-gray-500">Using default role criteria (Senior Software Engineer).</p>
      )}
      <RunStatusPoller
        runId={runId}
        initialStatus={run.status}
        initialMessage={run.message}
        initialStep={run.step}
      />
      {run.status === "failed" && run.error_message && (
        <p className="mb-4 text-sm text-red-600">{run.error_message}</p>
      )}
      <div className="mb-8">
        <RunActions
          runId={runId}
          status={run.status}
          candidateCount={candidateList.length}
        />
      </div>
      {run.status === "completed" && (
        <p className="text-sm text-gray-600 mb-2">
          {run.top_5_percent_ids?.length ? (
            <>Top 5%: {run.top_5_percent_ids.length} · Backups: {run.backup_ids?.length ?? 0}</>
          ) : null}
          <a
            href={getReportUrl(runId)}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-4 text-blue-600 hover:underline"
          >
            Export report
          </a>
          <span className="ml-2 text-gray-400 text-xs">(Print or Save as PDF from the report page)</span>
        </p>
      )}
      {candidateList.length > 0 ? (
        <>
          <h2 className="text-lg font-medium text-gray-900 mb-2">Rankings ({candidateList.length})</h2>
          <div className="overflow-x-auto border border-gray-200 rounded">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left py-2 px-2 font-medium text-gray-700">Filename</th>
                  <th className="text-left py-2 px-2 font-medium text-gray-700">Pipeline</th>
                  <th className="text-left py-2 px-2 font-medium text-gray-700">Shortlist</th>
                  <th className="text-right py-2 px-2 font-medium text-gray-700">Final</th>
                  <th className="text-right py-2 px-2 font-medium text-gray-700">Sys</th>
                  <th className="text-right py-2 px-2 font-medium text-gray-700">Prod</th>
                  <th className="text-right py-2 px-2 font-medium text-gray-700">AI</th>
                  <th className="text-right py-2 px-2 font-medium text-gray-700">Clar</th>
                  <th className="text-right py-2 px-2 font-medium text-gray-700">Ship</th>
                  <th className="text-left py-2 px-2 font-medium text-gray-700">Confidence</th>
                  <th className="text-left py-2 px-2 font-medium text-gray-700">Risk flags</th>
                </tr>
              </thead>
              <tbody>
                {[...candidateList]
                  .sort((a, b) => {
                    const ra = a.rank ?? 999999;
                    const rb = b.rank ?? 999999;
                    if (ra !== rb) return ra - rb;
                    return (a.embedding_rank ?? 999999) - (b.embedding_rank ?? 999999);
                  })
                  .map((c) => {
                    const scores = c.scores_with_evidence as {
                      overall_score?: number;
                      dimensions?: Record<string, { score?: number }>;
                    } | null;
                    const dims = scores?.dimensions;
                    const deepScored = c.shortlist_status === "top_5" || c.shortlist_status === "backup";
                    const shortlistLabel =
                      c.shortlist_status === "top_5"
                        ? "Top 5%"
                        : c.shortlist_status === "backup"
                          ? "Backup"
                          : deepScored
                            ? "—"
                            : "Not shortlisted";
                    return (
                      <tr key={c.id} className="border-t border-gray-100 hover:bg-gray-50">
                        <td className="py-2 px-2">
                          <Link
                            href={`/runs/${runId}/candidates/${c.candidate_id}`}
                            className="text-blue-600 hover:underline truncate max-w-[180px] block"
                          >
                            {c.filename || c.candidate_id}
                          </Link>
                          {!deepScored && (c.embedding_rank != null || c.embedding_score != null) && (
                            <span className="text-xs text-gray-500 block">
                              emb #{c.embedding_rank ?? "—"} {c.embedding_score != null ? `(${c.embedding_score.toFixed(2)})` : ""}
                            </span>
                          )}
                        </td>
                        <td className="py-2 px-2">
                          <span
                            className={
                              deepScored
                                ? "text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-800"
                                : "text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600"
                            }
                          >
                            {deepScored ? "Deep Scored" : "Embedding-only"}
                          </span>
                        </td>
                        <td className="py-2 px-2 text-gray-700">{shortlistLabel}</td>
                        <td className="py-2 px-2 text-right">
                          {deepScored && typeof scores?.overall_score === "number"
                            ? scores.overall_score
                            : "—"}
                        </td>
                        {(["systems", "product", "ai", "clarity", "shipping"] as const).map((dim) => (
                          <td key={dim} className="py-2 px-2 text-right">
                            {deepScored && dims && typeof dims[dim]?.score === "number"
                              ? dims[dim].score
                              : "—"}
                          </td>
                        ))}
                        <td className="py-2 px-2 text-gray-600">{c.confidence ?? "—"}</td>
                        <td className="py-2 px-2">
                          {c.risk_flags && c.risk_flags.length > 0 ? (
                            <span className="text-amber-700 text-xs">
                              {c.risk_flags.length} flag{c.risk_flags.length !== 1 ? "s" : ""}
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <p className="text-gray-500 text-sm">Upload PDF resumes above to get started.</p>
      )}
    </main>
  );
}

import { getCandidate, getRun } from "@/lib/api";
import Link from "next/link";

type Props = { params: Promise<{ runId: string; candidateId: string }> };

export default async function CandidateDetailPage({ params }: Props) {
  const { runId, candidateId } = await params;
  const [candidate, run] = await Promise.all([
    getCandidate(runId, candidateId),
    getRun(runId),
  ]);

  if (!candidate) {
    return (
      <main className="max-w-2xl mx-auto px-4 py-16">
        <h1 className="text-2xl font-semibold text-gray-900 mb-2">Candidate not found</h1>
        <p className="text-gray-600 mb-4">
          No candidate {candidateId} in run {runId}.
        </p>
        <Link href={`/runs/${runId}`} className="text-blue-600 hover:underline">
          Back to run
        </Link>
      </main>
    );
  }

  return (
    <main className="max-w-3xl mx-auto px-4 py-16">
      <Link href={`/runs/${runId}`} className="text-blue-600 hover:underline text-sm mb-6 inline-block">
        ← Run dashboard
      </Link>
      <h1 className="text-2xl font-semibold text-gray-900 mb-2">Candidate detail</h1>
      <p className="text-gray-600 mb-4">
        {candidate.filename || candidate.candidate_id}
      </p>
      <dl className="grid grid-cols-1 gap-2 text-sm">
        <dt className="font-medium text-gray-500">Status</dt>
        <dd>{candidate.status}</dd>
        {candidate.extraction_error && (
          <>
            <dt className="font-medium text-amber-700">Profile note</dt>
            <dd className="text-amber-700">{candidate.extraction_error}</dd>
          </>
        )}
        {candidate.rank != null && (
          <>
            <dt className="font-medium text-gray-500">Rank</dt>
            <dd>{candidate.rank}</dd>
          </>
        )}
        {candidate.embedding_rank != null && (
          <>
            <dt className="font-medium text-gray-500">Relevance rank</dt>
            <dd>{candidate.embedding_rank}</dd>
          </>
        )}
        {candidate.embedding_score != null && (
          <>
            <dt className="font-medium text-gray-500">Relevance score</dt>
            <dd>{candidate.embedding_score.toFixed(4)}</dd>
          </>
        )}
        {candidate.shortlist_status && (
          <>
            <dt className="font-medium text-gray-500">Shortlist</dt>
            <dd>{candidate.shortlist_status}</dd>
          </>
        )}
        {candidate.confidence && (
          <>
            <dt className="font-medium text-gray-500">Confidence</dt>
            <dd>{candidate.confidence}</dd>
          </>
        )}
      </dl>
      {candidate.scores_with_evidence && typeof candidate.scores_with_evidence === "object" && (
        <section className="mt-6 border-t pt-6">
          <h2 className="text-lg font-medium text-gray-900 mb-3">Score breakdown</h2>
          <p className="text-sm text-gray-700 mb-4">
            Overall: <strong>{(candidate.scores_with_evidence as { overall_score?: number }).overall_score ?? "—"}</strong> / 100
          </p>
          <ul className="space-y-4 text-sm">
            {(
              [
                ["systems", "Systems thinking"],
                ["product", "Product judgment"],
                ["ai", "Applied AI fluency"],
                ["clarity", "Clarity"],
                ["shipping", "Bias toward shipping"],
              ] as const
            ).map(([dim, label]) => {
              const d = (candidate.scores_with_evidence as {
                dimensions?: Record<string, { score?: number; evidence?: string[] }>;
              }).dimensions?.[dim];
              const score = d && typeof d.score === "number" ? d.score : null;
              const evidence = Array.isArray(d?.evidence) ? d.evidence : [];
              return (
                <li key={dim} className="border-l-2 border-gray-200 pl-3">
                  <span className="font-medium text-gray-700">{label}:</span>{" "}
                  {score != null ? `${score}/5` : "—"}
                  {evidence.length > 0 && (
                    <ul className="mt-2 space-y-1 text-gray-600 list-none">
                      {evidence.slice(0, 4).map((q, i) => (
                        <li key={i} className="text-xs border-l border-gray-100 pl-2 italic">
                          &ldquo;{q.slice(0, 200)}{q.length > 200 ? "…" : ""}&rdquo;
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              );
            })}
          </ul>
          {candidate.confidence_reason && (
            <p className="mt-4 text-sm text-gray-500 italic">{candidate.confidence_reason}</p>
          )}
        </section>
      )}
      {candidate.why_shortlisted && candidate.why_shortlisted.length > 0 && (
        <section className="mt-4">
          <h3 className="font-medium text-gray-700 mb-1">Why shortlisted</h3>
          <ul className="list-disc list-inside text-sm text-gray-700">
            {candidate.why_shortlisted.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        </section>
      )}
      {candidate.why_not_top_10 && candidate.why_not_top_10.length > 0 && (
        <section className="mt-4">
          <h3 className="font-medium text-gray-700 mb-1">Why not top 10</h3>
          <ul className="list-disc list-inside text-sm text-gray-600">
            {candidate.why_not_top_10.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        </section>
      )}
      {candidate.risk_flags && candidate.risk_flags.length > 0 && (
        <section className="mt-4">
          <h3 className="font-medium text-gray-700 mb-1">Risk flags</h3>
          <ul className="list-disc list-inside text-sm text-amber-700">
            {candidate.risk_flags.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </section>
      )}
      {candidate.structured_profile && (
        <section className="mt-8 border-t pt-6">
          <h2 className="text-lg font-medium text-gray-900 mb-3">Extracted profile</h2>
          {Boolean(candidate.structured_profile.summary_or_bio) && (
            <p className="text-gray-700 mb-4 whitespace-pre-wrap">
              {String(candidate.structured_profile.summary_or_bio)}
            </p>
          )}
          {Array.isArray(candidate.structured_profile.roles_and_companies) &&
            candidate.structured_profile.roles_and_companies.length > 0 && (
              <div className="mb-4">
                <h3 className="font-medium text-gray-700 mb-1">Roles</h3>
                <ul className="list-disc list-inside text-gray-600 text-sm space-y-1">
                  {(candidate.structured_profile.roles_and_companies as { role?: string; company?: string }[]).map(
                    (r, i) => (
                      <li key={i}>
                        {r.role}
                        {r.company ? ` at ${r.company}` : ""}
                      </li>
                    )
                  )}
                </ul>
              </div>
            )}
          {Array.isArray(candidate.structured_profile.skills_tech_stack) &&
            candidate.structured_profile.skills_tech_stack.length > 0 && (
              <div className="mb-4">
                <h3 className="font-medium text-gray-700 mb-1">Skills</h3>
                <p className="text-gray-600 text-sm">
                  {(candidate.structured_profile.skills_tech_stack as string[]).join(", ")}
                </p>
              </div>
            )}
        </section>
      )}
      {!candidate.structured_profile && candidate.status !== "uploaded" && candidate.status !== "extracted" && (
        <p className="text-gray-500 text-sm mt-6">No structured profile yet. Run evaluation to extract.</p>
      )}
    </main>
  );
}

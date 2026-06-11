"use client";

import { motion } from "framer-motion";
import {
  AlertCircle,
  CheckCircle2,
  FileText,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { useEffect, useState } from "react";

import Header from "@/components/dashboard/Header";
import Sidebar from "@/components/dashboard/Sidebar";
import { useAuth } from "@/context/AuthContext";
import { Link, useRouter } from "@/i18n/routing";
import { fetchProposals, type Proposal } from "@/lib/proposalApi";
import { logger } from "@/utils/logger";

function statusLabel(status: Proposal["status"]): string {
  const labels: Record<Proposal["status"], string> = {
    pending: "Queued",
    processing: "Generating sections",
    completed: "Ready for review",
    completed_with_errors: "Ready with section errors",
    failed: "Generation failed",
  };
  return labels[status];
}

export default function ProposalsPage() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [isFetching, setIsFetching] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  const loadProposals = async () => {
    setIsFetching(true);
    try {
      setProposals(await fetchProposals());
      setError(null);
    } catch (loadError) {
      logger.error("Failed to load proposals:", loadError);
      setError("The proposal workspace could not be loaded.");
    } finally {
      setIsFetching(false);
    }
  };

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (user) void loadProposals();
  }, [user]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <Loader2 className="h-10 w-10 animate-spin text-emerald-light" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-on-background">
      <Sidebar
        isMobile={isMobile}
        isSidebarOpen={isSidebarOpen}
        setIsSidebarOpen={setIsSidebarOpen}
        setIsUploadModalOpen={() => {}}
        logout={logout}
      />
      <Header user={user} setIsSidebarOpen={setIsSidebarOpen} />

      <motion.main
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="min-h-screen px-6 pb-24 pt-12 md:ml-64 md:px-12"
      >
        <div className="mx-auto max-w-5xl">
          <div className="mb-10 flex flex-wrap items-center justify-between gap-5">
            <div>
              <h1 className="flex items-center gap-3 text-4xl font-bold text-white">
                <FileText className="text-emerald-light" />
                My Proposals
              </h1>
              <p className="mt-3 text-sm text-slate-400">
                Review AI-generated grant proposals and edit individual sections.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void loadProposals()}
              className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:bg-white/10"
            >
              <RefreshCw size={14} />
              Refresh
            </button>
          </div>

          {error && (
            <div className="mb-6 flex items-center gap-3 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-red-200">
              <AlertCircle size={18} />
              {error}
            </div>
          )}

          {isFetching ? (
            <div className="flex justify-center py-28">
              <Loader2 className="h-9 w-9 animate-spin text-emerald-light" />
            </div>
          ) : proposals.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-16 text-center">
              <FileText className="mx-auto mb-4 h-12 w-12 text-slate-600" />
              <h2 className="text-xl font-bold text-white">No proposals yet</h2>
              <p className="mx-auto mt-2 max-w-md text-sm text-slate-400">
                Open Semantic Matches on the dashboard and select Draft Proposal for a
                matching grant.
              </p>
              <button
                type="button"
                onClick={() => router.push("/dashboard")}
                className="mt-6 rounded-lg bg-emerald px-5 py-2.5 text-sm font-bold text-surface"
              >
                Open dashboard
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {proposals.map((proposal) => {
                const terminal =
                  proposal.status === "completed" ||
                  proposal.status === "completed_with_errors";
                return (
                  <Link
                    key={proposal.id}
                    href={`/proposals/${proposal.id}`}
                    className="block rounded-2xl border border-white/10 bg-surface/30 p-6 transition hover:border-emerald/30 hover:bg-surface/50"
                    data-testid={`proposal-card-${proposal.id}`}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <span className="text-xs font-bold uppercase tracking-widest text-emerald-light">
                          Proposal #{proposal.id}
                        </span>
                        <h2 className="mt-2 text-xl font-bold text-white">
                          Grant #{proposal.grant_id}
                        </h2>
                        <p className="mt-2 text-xs text-slate-500">
                          Created {new Date(proposal.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <span
                        className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold ${
                          terminal
                            ? "border-emerald/30 bg-emerald/10 text-emerald-light"
                            : proposal.status === "failed"
                              ? "border-red-500/30 bg-red-500/10 text-red-300"
                              : "border-amber/30 bg-amber/10 text-amber-light"
                        }`}
                      >
                        {terminal ? (
                          <CheckCircle2 size={14} />
                        ) : proposal.status === "failed" ? (
                          <AlertCircle size={14} />
                        ) : (
                          <Loader2 size={14} className="animate-spin" />
                        )}
                        {statusLabel(proposal.status)}
                      </span>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </motion.main>
    </div>
  );
}

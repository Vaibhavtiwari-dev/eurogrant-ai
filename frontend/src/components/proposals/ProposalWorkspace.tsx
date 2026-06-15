"use client";

import { AlertCircle, ArrowLeft, Loader2, RefreshCw, RotateCcw, FileText, Download } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import Header from "@/components/dashboard/Header";
import Sidebar from "@/components/dashboard/Sidebar";
import { useAuth } from "@/context/AuthContext";
import { Link } from "@/i18n/routing";
import { apiFetch } from "@/lib/api";
import {
  ProposalApiError,
  fetchProposal,
  fetchProposalSections,
  regenerateProposalSection,
  updateProposalSection,
  type Proposal,
  type ProposalSection,
  type TipTapDocument,
} from "@/lib/proposalApi";
import { logger } from "@/utils/logger";

import ProposalSectionEditor from "./ProposalSectionEditor";
import ProposalSectionSidebar from "./ProposalSectionSidebar";

interface ProposalWorkspaceProps {
  proposalId: number;
}

type SaveState = "saved" | "unsaved" | "saving" | "conflict" | "failed";

export default function ProposalWorkspace({ proposalId }: ProposalWorkspaceProps) {
  const t = useTranslations("Proposals");
  const { user, loading, logout } = useAuth();
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [sections, setSections] = useState<ProposalSection[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [draft, setDraft] = useState<TipTapDocument | null>(null);
  const [saveState, setSaveState] = useState<SaveState>("saved");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [isExporting, setIsExporting] = useState<"pdf" | "docx" | null>(null);
  const savingRef = useRef(false);
  const draftRef = useRef<TipTapDocument | null>(null);

  const selectedSection = useMemo(
    () => sections.find((section) => section.id === selectedId) ?? null,
    [sections, selectedId],
  );
  const canEdit = user?.role === "admin" || user?.role === "writer";

  const load = useCallback(
    async (preserveDraft = true) => {
      try {
        const [nextProposal, nextSections] = await Promise.all([
          fetchProposal(proposalId),
          fetchProposalSections(proposalId),
        ]);
        setProposal(nextProposal);
        setSections(nextSections);
        setSelectedId((current) => {
          if (current && nextSections.some((section) => section.id === current)) return current;
          return nextSections[0]?.id ?? null;
        });
        if (!preserveDraft || saveState === "saved") {
          const current =
            nextSections.find((section) => section.id === selectedId) ?? nextSections[0];
          setDraft(current?.content_json ?? null);
        }
        setError(null);
      } catch (loadError) {
        logger.error("Failed to load proposal workspace", loadError);
        setError(loadError instanceof Error ? loadError.message : t("loadFailed"));
      } finally {
        setIsLoading(false);
      }
    },
    [proposalId, saveState, selectedId, t],
  );

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(false);
    // The initial load is intentionally keyed only by the route identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [proposalId]);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  useEffect(() => {
    draftRef.current = draft;
  }, [draft]);

  const hasActiveGeneration =
    proposal?.status === "pending" ||
    proposal?.status === "processing" ||
    sections.some((section) =>
      ["pending", "generating"].includes(section.status),
    );

  useEffect(() => {
    if (!hasActiveGeneration) return;
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") void load(true);
    }, 5000);
    return () => window.clearInterval(interval);
  }, [hasActiveGeneration, load]);

  useEffect(() => {
    if (!canEdit || !selectedSection || !draft || saveState !== "unsaved") return;
    const timeout = window.setTimeout(async () => {
      if (savingRef.current) return;
      savingRef.current = true;
      setSaveState("saving");
      const serializedAtSave = JSON.stringify(draft);
      try {
        const updated = await updateProposalSection(
          proposalId,
          selectedSection.id,
          draft,
          selectedSection.version,
        );
        setSections((current) =>
          current.map((section) => (section.id === updated.id ? updated : section)),
        );
        setSaveState((current) =>
          current === "saving" &&
          JSON.stringify(draftRef.current) === serializedAtSave
            ? "saved"
            : "unsaved",
        );
      } catch (saveError) {
        if (saveError instanceof ProposalApiError && saveError.status === 409) {
          setSaveState("conflict");
        } else {
          setSaveState("failed");
          toast.error(t("saveFailed"));
        }
      } finally {
        savingRef.current = false;
      }
    }, 800);
    return () => window.clearTimeout(timeout);
  }, [canEdit, draft, proposalId, saveState, selectedSection, t]);

  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (saveState === "unsaved" || saveState === "saving" || saveState === "failed") {
        event.preventDefault();
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [saveState]);

  const selectSection = (section: ProposalSection) => {
    if (
      selectedId !== section.id &&
      ["unsaved", "saving", "failed"].includes(saveState) &&
      !window.confirm(t("discardUnsaved"))
    ) {
      return;
    }
    setSelectedId(section.id);
    setDraft(section.content_json);
    setSaveState("saved");
  };

  const regenerate = async () => {
    if (!selectedSection || !canEdit || !window.confirm(t("regenerateConfirm"))) return;
    try {
      const updated = await regenerateProposalSection(
        proposalId,
        selectedSection.id,
        selectedSection.version,
      );
      setSections((current) =>
        current.map((section) => (section.id === updated.id ? updated : section)),
      );
      toast.success(t("regenerationStarted"));
    } catch (regenerationError) {
      if (
        regenerationError instanceof ProposalApiError &&
        regenerationError.status === 409
      ) {
        setSaveState("conflict");
      } else {
        toast.error(t("regenerationFailed"));
      }
    }
  };

  const exportDocument = async (format: "pdf" | "docx") => {
    setIsExporting(format);
    try {
      const res = await apiFetch(`/proposals/${proposalId}/export/${format}`);
      if (!res.ok) {
        throw new Error(t("exportFailed", { defaultValue: "Export failed. Please try again." }));
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `EuroGrant_Proposal_${proposalId}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success(t("exportSuccess", { defaultValue: `Exported as ${format.toUpperCase()}` }));
    } catch (err) {
      logger.error(`Failed to export ${format}:`, err);
      toast.error(err instanceof Error ? err.message : "Export failed");
    } finally {
      setIsExporting(null);
    }
  };

  if (loading || !user || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
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
      <main className="min-h-screen px-6 pb-20 pt-10 md:ml-64 md:px-10">
        <div className="mx-auto max-w-7xl">
          <Link
            href="/proposals"
            className="mb-6 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"
          >
            <ArrowLeft size={16} />
            {t("back")}
          </Link>

          <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-emerald-light">
                {t("proposalLabel", { id: proposalId })}
              </p>
              <h1 className="mt-2 text-3xl font-bold text-white">{t("workspaceTitle")}</h1>
              <p className="mt-2 text-sm text-slate-400">
                {t("grantLabel", { id: proposal?.grant_id ?? 0 })}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 mr-4 border-r border-white/10 pr-4">
                <button
                  type="button"
                  onClick={() => void exportDocument("pdf")}
                  disabled={isExporting !== null}
                  className="rounded-lg border border-white/10 px-3 py-2 text-xs font-bold uppercase tracking-wider text-slate-300 hover:bg-white/5 disabled:opacity-50 flex items-center gap-2"
                >
                  {isExporting === "pdf" ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />}
                  PDF
                </button>
                <button
                  type="button"
                  onClick={() => void exportDocument("docx")}
                  disabled={isExporting !== null}
                  className="rounded-lg border border-white/10 px-3 py-2 text-xs font-bold uppercase tracking-wider text-slate-300 hover:bg-white/5 disabled:opacity-50 flex items-center gap-2"
                >
                  {isExporting === "docx" ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
                  DOCX
                </button>
              </div>
              <span
                aria-live="polite"
                className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold text-slate-300"
              >
                {t(`saveState.${saveState}`)}
              </span>
              <button
                type="button"
                onClick={() => void load(saveState !== "saved")}
                className="rounded-lg border border-white/10 p-2.5 text-slate-300 hover:bg-white/5"
                aria-label={t("refresh")}
              >
                <RefreshCw size={16} />
              </button>
            </div>
          </div>

          {error && (
            <div className="mb-6 flex items-center gap-3 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-red-200">
              <AlertCircle size={18} />
              {error}
            </div>
          )}

          {sections.length === 0 ? (
            <div className="rounded-2xl border border-white/10 bg-surface/30 p-8">
              {proposal?.content ? (
                <>
                  <h2 className="mb-4 text-xl font-bold text-white">{t("legacyTitle")}</h2>
                  <pre className="whitespace-pre-wrap font-sans text-sm leading-7 text-slate-300">
                    {proposal.content}
                  </pre>
                </>
              ) : (
                <div className="flex items-center gap-3 text-slate-300">
                  {hasActiveGeneration && <Loader2 className="animate-spin" size={18} />}
                  {hasActiveGeneration ? t("generating") : t("noSections")}
                </div>
              )}
            </div>
          ) : (
            <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
              <aside className="rounded-2xl border border-white/10 bg-surface/30 p-4">
                <ProposalSectionSidebar
                  sections={sections}
                  selectedId={selectedId}
                  onSelect={selectSection}
                />
              </aside>
              <section className="rounded-2xl border border-white/10 bg-surface/30 p-5">
                {selectedSection && draft && (
                  <>
                    <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <h2 className="text-2xl font-bold text-white">
                          {selectedSection.name}
                        </h2>
                        {selectedSection.description && (
                          <p className="mt-2 text-sm text-slate-400">
                            {selectedSection.description}
                          </p>
                        )}
                      </div>
                      {canEdit && (
                        <button
                          type="button"
                          disabled={
                            selectedSection.status === "generating" ||
                            saveState === "unsaved" ||
                            saveState === "saving"
                          }
                          onClick={() => void regenerate()}
                          className="inline-flex items-center gap-2 rounded-lg border border-copper/40 bg-copper/10 px-4 py-2 text-xs font-bold text-gold disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          <RotateCcw size={14} />
                          {t("regenerate")}
                        </button>
                      )}
                    </div>

                    {saveState === "conflict" && (
                      <div className="mb-4 rounded-lg border border-amber/30 bg-amber/10 p-4 text-sm text-amber-light">
                        <p>{t("conflict")}</p>
                        <button
                          type="button"
                          onClick={() => {
                            void load(false);
                            setSaveState("saved");
                          }}
                          className="mt-3 rounded-md border border-amber/30 px-3 py-1.5 font-semibold"
                        >
                          {t("reloadLatest")}
                        </button>
                      </div>
                    )}

                    <ProposalSectionEditor
                      key={selectedSection.id}
                      document={draft}
                      editable={canEdit && saveState !== "conflict"}
                      onChange={(nextDocument) => {
                        setDraft(nextDocument);
                        setSaveState("unsaved");
                      }}
                    />
                    {!canEdit && (
                      <p className="mt-3 text-xs text-slate-500">{t("viewerReadOnly")}</p>
                    )}
                  </>
                )}
              </section>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

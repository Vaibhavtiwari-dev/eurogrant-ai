"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { containerVariants, itemVariants } from "@/lib/animations";
import Sidebar from "@/components/dashboard/Sidebar";
import Header from "@/components/dashboard/Header";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "@/i18n/routing";
import { apiFetch } from "@/lib/api";
import { FileText, Loader2, AlertCircle, ArrowUpRight, CheckCircle2, RefreshCw } from "lucide-react";

interface ProposalMock {
  id: string;
  title: string;
  grantName: string;
  requestedAmount: string;
  status: "GENERATING" | "COMPLETED" | "DRAFT";
  progress: number;
  subtext: string;
  updatedAt: string;
}

export default function ProposalsPage() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [proposals, setProposals] = useState<ProposalMock[]>([]);
  const [isFetching, setIsFetching] = useState(true);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Fetch / Simulate active proposals based on organization uploads
  useEffect(() => {
    const fetchProposals = async () => {
      if (!user) return;
      try {
        // Query uploads to see if the user has uploaded documents
        const res = await apiFetch("/uploads/documents");
        if (res.ok) {
          const docs = await res.json();
          if (Array.isArray(docs) && docs.length > 0) {
            // Simulate active generated drafts linked to the dashboard pipelines
            setProposals([
              {
                id: "EIC-2024-ACCELERATOR-01",
                title: "Project GreenLithium",
                grantName: "EIC Accelerator 2026",
                requestedAmount: "€2,500,000",
                status: "GENERATING",
                progress: 65,
                subtext: "Context Assembling (RAG)",
                updatedAt: "Just now"
              },
              {
                id: "PROP-EAS-0082",
                title: "Circular Resource Allocation Software",
                grantName: "Estonian GreenTech Innovation Grant",
                requestedAmount: "€150,000",
                status: "DRAFT",
                progress: 100,
                subtext: "Ready for Human Polish",
                updatedAt: "2 hours ago"
              }
            ]);
          } else {
            setProposals([]);
          }
        }
      } catch (err) {
        console.error("Failed to load proposals:", err);
      } finally {
        setIsFetching(false);
      }
    };
    fetchProposals();
  }, [user]);

  if (loading || !user) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="flex flex-col items-center gap-6">
          <div className="w-16 h-16 border-4 border-emerald/10 border-t-emerald-light rounded-full animate-spin"></div>
          <p className="text-emerald-light/60 font-bold uppercase tracking-[0.2em] text-xs animate-pulse">Syncing Proposals Workspace...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-on-background selection:bg-emerald/10">
      <Sidebar 
        isMobile={isMobile}
        isSidebarOpen={isSidebarOpen}
        setIsSidebarOpen={setIsSidebarOpen}
        setIsUploadModalOpen={() => {}}
        logout={logout}
      />

      <Header 
        user={user}
        setIsSidebarOpen={setIsSidebarOpen}
      />

      <motion.main 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="relative z-10 md:ml-64 pt-12 px-12 pb-32 min-h-screen hero-gradient"
      >
        <div className="max-w-5xl mx-auto">
          {/* Header */}
          <div className="mb-12 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
            <div>
              <h1 className="text-4xl font-bold text-on-surface mb-3 flex items-center gap-4">
                <FileText className="text-emerald-light" size={32} />
                My Proposals
              </h1>
              <p className="text-on-surface-variant text-sm">
                Manage, edit, and track your AI-drafted European grant proposal applications.
              </p>
            </div>
            <button
              onClick={() => router.refresh()}
              className="px-4 py-2.5 rounded-lg bg-surface hover:bg-surface-variant border border-white/5 hover:border-white/10 text-on-surface-variant hover:text-on-surface text-xs font-semibold flex items-center gap-2 transition-all active:scale-95 shadow"
            >
              <RefreshCw size={14} /> Refresh Workspace
            </button>
          </div>

          {/* Active Proposals list */}
          {isFetching ? (
            <div className="flex flex-col items-center justify-center py-32">
              <Loader2 className="h-10 w-10 text-emerald animate-spin mb-4" />
              <p className="text-on-surface-variant text-sm tracking-wider animate-pulse">Loading active proposal drafts...</p>
            </div>
          ) : proposals.length === 0 ? (
            <div className="text-center py-24 premium-card bg-surface/20 backdrop-blur-md rounded-2xl border border-dashed border-white/10">
              <AlertCircle className="h-12 w-12 text-on-surface-variant/40 mx-auto mb-4" />
              <h3 className="text-xl font-bold text-on-surface mb-2">No active proposals found</h3>
              <p className="text-on-surface-variant max-w-sm mx-auto text-xs leading-relaxed mb-8">
                To begin generating a structured EIC or EuroGrant proposal, upload your company documents on the main Dashboard page.
              </p>
              <button
                onClick={() => router.push("/dashboard")}
                className="px-6 py-3 bg-emerald hover:bg-emerald-light text-surface font-semibold rounded-lg transition-all shadow-md active:scale-95 flex items-center gap-2 mx-auto"
              >
                Go to Dashboard
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              <h2 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/60 border-b border-white/5 pb-4">
                Active Drafts & Generations
              </h2>

              <div className="grid grid-cols-1 gap-6">
                {proposals.map((prop) => (
                  <motion.div 
                    key={prop.id}
                    variants={itemVariants}
                    className="premium-card p-8 bg-surface/30 rounded-2xl border border-white/5 shadow-lg group relative overflow-hidden"
                  >
                    <div className="flex flex-col md:flex-row justify-between items-start gap-4 mb-6">
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-[10px] font-bold text-emerald-light uppercase tracking-widest bg-emerald/10 border border-emerald/20 px-3 py-0.5 rounded-full">
                            {prop.id}
                          </span>
                          <span className="text-[10px] font-semibold text-on-surface-variant/60">
                            Updated {prop.updatedAt}
                          </span>
                        </div>
                        <h3 className="text-2xl font-bold text-on-surface leading-tight">
                          {prop.title}
                        </h3>
                        <p className="text-xs text-on-surface-variant font-medium mt-1">
                          Target Grant: <span className="text-on-surface font-semibold">{prop.grantName}</span>
                        </p>
                      </div>

                      <div className="flex flex-col items-end gap-2 text-right">
                        <div className="text-base font-bold text-emerald-light bg-emerald/10 border border-emerald/20 px-3 py-1 rounded-lg">
                          Funding Request: {prop.requestedAmount}
                        </div>
                        
                        {prop.status === "GENERATING" ? (
                          <span className="text-[10px] font-bold text-amber bg-amber/10 border border-amber/20 px-3 py-1 rounded-full uppercase tracking-wider flex items-center gap-1.5">
                            <Loader2 className="animate-spin h-3 w-3" />
                            {prop.subtext}
                          </span>
                        ) : (
                          <span className="text-[10px] font-bold text-emerald-light bg-emerald/10 border border-emerald/20 px-3 py-1 rounded-full uppercase tracking-wider flex items-center gap-1.5">
                            <CheckCircle2 size={12} />
                            {prop.subtext}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Progress slider */}
                    <div className="space-y-2 border-t border-white/5 pt-6">
                      <div className="flex justify-between text-xs font-semibold text-on-surface-variant">
                        <span>Generation & Structuring Progress</span>
                        <span className={prop.status === "GENERATING" ? "text-amber font-bold" : "text-emerald font-bold"}>{prop.progress}%</span>
                      </div>
                      <div className="w-full bg-background/60 h-2.5 rounded-full overflow-hidden border border-white/5">
                        <motion.div 
                          initial={{ width: 0 }}
                          animate={{ width: `${prop.progress}%` }}
                          transition={{ duration: 1.2, ease: "easeOut" }}
                          className={`h-full rounded-full ${
                            prop.status === "GENERATING" 
                              ? "bg-gradient-to-r from-amber to-amber-light shadow-[0_0_10px_rgba(245,158,11,0.2)] animate-pulse" 
                              : "bg-gradient-to-r from-emerald to-emerald-light shadow-[0_0_10px_rgba(16,185,129,0.2)]"
                          }`}
                        />
                      </div>
                    </div>

                    {/* Actions button */}
                    <div className="mt-8 flex justify-end gap-4">
                      {prop.status === "GENERATING" ? (
                        <button 
                          disabled
                          className="px-5 py-2.5 rounded-lg bg-surface/50 border border-white/5 text-on-surface-variant/40 text-xs font-semibold cursor-not-allowed flex items-center gap-2"
                        >
                          Assembling Sections...
                        </button>
                      ) : (
                        <>
                          <button 
                            className="px-5 py-2.5 rounded-lg bg-surface hover:bg-surface-variant border border-white/5 hover:border-white/10 text-on-surface-variant hover:text-on-surface text-xs font-semibold transition-all active:scale-95"
                          >
                            Edit Draft
                          </button>
                          <button 
                            className="px-5 py-2.5 rounded-lg bg-emerald hover:bg-emerald-light text-surface font-semibold text-xs transition-all active:scale-95 shadow flex items-center gap-1.5"
                          >
                            Export PDF <ArrowUpRight size={14} />
                          </button>
                        </>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          )}
        </div>
      </motion.main>
    </div>
  );
}

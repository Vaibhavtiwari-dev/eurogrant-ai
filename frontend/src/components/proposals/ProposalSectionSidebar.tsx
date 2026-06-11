"use client";

import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";

import type { ProposalSection } from "@/lib/proposalApi";

interface ProposalSectionSidebarProps {
  sections: ProposalSection[];
  selectedId: number | null;
  onSelect: (section: ProposalSection) => void;
}

export default function ProposalSectionSidebar({
  sections,
  selectedId,
  onSelect,
}: ProposalSectionSidebarProps) {
  return (
    <nav aria-label="Proposal sections" className="space-y-2">
      {sections.map((section) => (
        <button
          key={section.id}
          type="button"
          onClick={() => onSelect(section)}
          aria-current={selectedId === section.id ? "page" : undefined}
          className={`flex w-full items-center justify-between gap-3 rounded-lg border px-4 py-3 text-left transition ${
            selectedId === section.id
              ? "border-emerald/40 bg-emerald/10 text-white"
              : "border-white/5 bg-white/[0.03] text-slate-300 hover:border-white/15"
          }`}
        >
          <span className="text-sm font-semibold">{section.name}</span>
          {section.status === "generating" && (
            <Loader2 className="h-4 w-4 animate-spin text-amber" aria-label="Generating" />
          )}
          {section.status === "completed" && (
            <CheckCircle2 className="h-4 w-4 text-emerald-light" aria-label="Completed" />
          )}
          {section.status === "failed" && (
            <AlertCircle className="h-4 w-4 text-red-400" aria-label="Failed" />
          )}
        </button>
      ))}
    </nav>
  );
}

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ProposalSectionSidebar from "@/components/proposals/ProposalSectionSidebar";
import type { ProposalSection } from "@/lib/proposalApi";

const section: ProposalSection = {
  id: 5,
  proposal_id: 2,
  section_key: "summary",
  name: "Executive Summary",
  description: null,
  weight: null,
  content_json: { type: "doc", content: [] },
  order: 0,
  status: "completed",
  version: 1,
  edited_at: null,
  edited_by: null,
  created_at: "2026-06-11T00:00:00Z",
  updated_at: null,
};

describe("ProposalSectionSidebar", () => {
  it("renders status and selects a section", async () => {
    const onSelect = vi.fn();
    render(
      <ProposalSectionSidebar
        sections={[section]}
        selectedId={section.id}
        onSelect={onSelect}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /executive summary/i }));
    expect(onSelect).toHaveBeenCalledWith(section);
    expect(screen.getByLabelText("Completed")).toBeInTheDocument();
  });
});

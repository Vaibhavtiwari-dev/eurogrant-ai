import { describe, expect, it } from "vitest";

import {
  ProposalSchema,
  TipTapDocumentSchema,
} from "@/lib/proposalApi";

describe("proposal API schemas", () => {
  it("accepts completed-with-errors proposal status", () => {
    const proposal = ProposalSchema.parse({
      id: 1,
      organization_id: 1,
      grant_id: 2,
      status: "completed_with_errors",
      content: null,
      compatibility_score: 0.8,
      created_at: "2026-06-11T00:00:00Z",
      updated_at: null,
    });
    expect(proposal.status).toBe("completed_with_errors");
  });

  it("requires a TipTap doc root", () => {
    expect(TipTapDocumentSchema.safeParse({ type: "paragraph" }).success).toBe(false);
  });
});

import { z } from "zod";

import { apiFetch } from "@/lib/api";

export const ProposalStatusSchema = z.enum([
  "pending",
  "processing",
  "completed",
  "completed_with_errors",
  "failed",
]);

export const SectionStatusSchema = z.enum([
  "pending",
  "generating",
  "completed",
  "failed",
]);

export const TipTapDocumentSchema = z.object({
  type: z.literal("doc"),
  content: z.array(z.record(z.string(), z.unknown())).optional(),
});

export const ProposalSchema = z.object({
  id: z.number(),
  organization_id: z.number(),
  grant_id: z.number(),
  status: ProposalStatusSchema,
  content: z.string().nullable(),
  compatibility_score: z.number().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string().nullable().optional(),
});

export const ProposalSectionSchema = z.object({
  id: z.number(),
  proposal_id: z.number(),
  section_key: z.string(),
  name: z.string(),
  description: z.string().nullable().optional(),
  weight: z.number().nullable().optional(),
  content_json: TipTapDocumentSchema,
  order: z.number(),
  status: SectionStatusSchema,
  version: z.number(),
  edited_at: z.string().nullable().optional(),
  edited_by: z.number().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string().nullable().optional(),
});

export const ProposalListSchema = z.array(ProposalSchema);
export const ProposalSectionListSchema = z.array(ProposalSectionSchema);

export type Proposal = z.infer<typeof ProposalSchema>;
export type ProposalSection = z.infer<typeof ProposalSectionSchema>;
export type TipTapDocument = z.infer<typeof TipTapDocumentSchema>;

export class ProposalApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
    readonly details?: Record<string, unknown>,
  ) {
    super(message);
  }
}

async function parseResponse<T>(response: Response, schema: z.ZodSchema<T>): Promise<T> {
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const parsed = z
      .object({
        detail: z
          .object({
            error: z.object({
              code: z.string(),
              message: z.string(),
              details: z.record(z.string(), z.unknown()).optional(),
            }),
          })
          .optional(),
      })
      .safeParse(body);
    const error = parsed.success ? parsed.data.detail?.error : undefined;
    throw new ProposalApiError(
      error?.message || `Request failed with status ${response.status}`,
      response.status,
      error?.code,
      error?.details,
    );
  }
  return schema.parse(body);
}

export async function fetchProposals(): Promise<Proposal[]> {
  return parseResponse(await apiFetch("/proposals"), ProposalListSchema);
}

export async function fetchProposal(proposalId: number): Promise<Proposal> {
  return parseResponse(await apiFetch(`/proposals/${proposalId}`), ProposalSchema);
}

export async function fetchProposalSections(
  proposalId: number,
): Promise<ProposalSection[]> {
  return parseResponse(
    await apiFetch(`/proposals/${proposalId}/sections`),
    ProposalSectionListSchema,
  );
}

export async function createProposal(grantId: number): Promise<Proposal> {
  return parseResponse(
    await apiFetch("/proposals/", {
      method: "POST",
      body: JSON.stringify({ grant_id: grantId }),
    }),
    ProposalSchema,
  );
}

export async function updateProposalSection(
  proposalId: number,
  sectionId: number,
  contentJson: TipTapDocument,
  expectedVersion: number,
): Promise<ProposalSection> {
  return parseResponse(
    await apiFetch(`/proposals/${proposalId}/sections/${sectionId}`, {
      method: "PATCH",
      body: JSON.stringify({
        content_json: contentJson,
        expected_version: expectedVersion,
      }),
    }),
    ProposalSectionSchema,
  );
}

export async function regenerateProposalSection(
  proposalId: number,
  sectionId: number,
  expectedVersion: number,
): Promise<ProposalSection> {
  return parseResponse(
    await apiFetch(`/proposals/${proposalId}/sections/${sectionId}/regenerate`, {
      method: "POST",
      body: JSON.stringify({ expected_version: expectedVersion }),
    }),
    ProposalSectionSchema,
  );
}

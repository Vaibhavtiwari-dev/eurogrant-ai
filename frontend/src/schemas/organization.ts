import { z } from "zod";

/**
 * Shared Zod schema for the /organizations/me endpoint response.
 * Used by CompanyProfile and NotificationSettings (was duplicated with
 * divergent fields — M29 fix).
 */
export const OrganizationSchema = z.object({
  id: z.number(),
  name: z.string(),
  subscription_tier: z.string(),
  sector: z.string().nullable().optional(),
  headcount_range: z.string().nullable().optional(),
  revenue_tier: z.string().nullable().optional(),
  legal_entity_type: z.string().nullable().optional(),
  countries_of_operation: z.string().nullable().optional(),
  core_technologies: z.string().nullable().optional(),
  match_threshold: z.number(),
  alert_email_enabled: z.boolean(),
  created_at: z.string(),
});

export type Organization = z.infer<typeof OrganizationSchema>;

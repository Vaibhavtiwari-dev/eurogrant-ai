import ProposalWorkspace from "@/components/proposals/ProposalWorkspace";

export default async function ProposalDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const proposalId = Number(id);

  return <ProposalWorkspace proposalId={proposalId} />;
}

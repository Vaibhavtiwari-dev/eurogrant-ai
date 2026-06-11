import { Loader2 } from "lucide-react";

export default function ProposalDetailLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Loader2 className="h-10 w-10 animate-spin text-emerald-light" />
    </div>
  );
}

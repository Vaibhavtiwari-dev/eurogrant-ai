export default function Loading() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="flex flex-col items-center gap-6">
        <div className="w-16 h-16 border-4 border-emerald/10 border-t-emerald-light rounded-full animate-spin" />
        <p className="text-emerald-light/60 font-bold uppercase tracking-[0.2em] text-xs animate-pulse">Loading...</p>
      </div>
    </div>
  );
}

export default function ProposalsLoading() {
  return (
    <div className="min-h-screen bg-background text-on-background">
      {/* Sidebar skeleton */}
      <aside className="hidden md:flex fixed left-0 top-0 h-full w-56 bg-surface border-r border-white/5 flex-col gap-6 p-6">
        <div className="h-8 w-32 bg-white/5 rounded-lg animate-pulse" />
        <div className="flex flex-col gap-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-10 bg-white/5 rounded-lg animate-pulse" />
          ))}
        </div>
      </aside>

      {/* Header skeleton */}
      <header className="md:ml-56 h-20 border-b border-white/5 flex items-center justify-between px-8">
        <div className="h-6 w-48 bg-white/5 rounded animate-pulse" />
        <div className="h-10 w-10 bg-white/5 rounded-full animate-pulse" />
      </header>

      {/* Main content skeleton */}
      <main className="relative z-10 md:ml-56 pt-12 px-12 pb-32 min-h-screen">
        <div className="max-w-5xl mx-auto">
          {/* Page header skeleton */}
          <div className="mb-12 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
            <div>
              <div className="h-10 w-64 bg-white/5 rounded-lg animate-pulse mb-3" />
              <div className="h-4 w-80 bg-white/5 rounded animate-pulse" />
            </div>
            <div className="h-10 w-40 bg-white/5 rounded-lg animate-pulse" />
          </div>

          {/* Section title skeleton */}
          <div className="h-4 w-48 bg-white/5 rounded animate-pulse mb-8" />

          {/* Proposal cards skeleton */}
          <div className="space-y-6">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="h-64 bg-white/5 rounded-2xl animate-pulse" />
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}

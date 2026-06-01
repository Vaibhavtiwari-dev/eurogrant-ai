export default function DashboardLoading() {
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
        <div className="max-w-7xl mx-auto">
          {/* Tab bar skeleton */}
          <div className="flex gap-8 mb-10 border-b border-white/5 pb-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-4 w-32 bg-white/5 rounded animate-pulse" />
            ))}
          </div>

          {/* Content grid skeleton */}
          <div className="grid grid-cols-12 gap-10">
            <div className="col-span-12 lg:col-span-8 space-y-12">
              {/* Stats cards */}
              <div className="grid grid-cols-3 gap-6">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="h-28 bg-white/5 rounded-2xl animate-pulse" />
                ))}
              </div>
              {/* Company profile skeleton */}
              <div className="h-64 bg-white/5 rounded-2xl animate-pulse" />
              {/* Pipeline skeleton */}
              <div className="space-y-4">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="h-20 bg-white/5 rounded-xl animate-pulse" />
                ))}
              </div>
            </div>
            <div className="col-span-12 lg:col-span-4 space-y-12">
              {Array.from({ length: 2 }).map((_, i) => (
                <div key={i} className="h-80 bg-white/5 rounded-2xl animate-pulse" />
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

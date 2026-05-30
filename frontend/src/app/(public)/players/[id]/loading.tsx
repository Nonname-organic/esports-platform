export default function PlayerDetailLoading() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-8 animate-pulse space-y-5">
      <div className="h-4 w-40 rounded bg-white/5" />
      <div className="flex gap-5 rounded-2xl border border-white/10 bg-slate-900 p-6">
        <div className="h-24 w-24 rounded-2xl bg-white/5" />
        <div className="flex-1 space-y-3">
          <div className="h-7 w-48 rounded bg-white/5" />
          <div className="h-4 w-32 rounded bg-white/5" />
          <div className="flex gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-12 w-20 rounded-lg bg-white/5" />
            ))}
          </div>
        </div>
      </div>
      <div className="flex gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-10 w-24 rounded-full bg-white/5" />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 rounded-xl bg-white/5" />
        ))}
      </div>
    </div>
  );
}

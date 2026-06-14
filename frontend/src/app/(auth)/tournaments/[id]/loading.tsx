export default function TournamentDetailLoading() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 animate-pulse">
      <div className="mb-6 h-4 w-48 rounded bg-white/5" />
      <div className="mb-4 h-48 w-full rounded-2xl bg-white/5" />
      <div className="mb-2 h-8 w-2/3 rounded bg-white/5" />
      <div className="mb-8 h-4 w-full max-w-lg rounded bg-white/5" />
      <div className="mb-6 flex gap-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-10 w-24 rounded-full bg-white/5" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-32 rounded-xl bg-white/5" />
          ))}
        </div>
        <div className="space-y-4">
          <div className="h-40 rounded-xl bg-white/5" />
          <div className="h-40 rounded-xl bg-white/5" />
        </div>
      </div>
    </div>
  );
}

export default function MatchDetailLoading() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-8 animate-pulse space-y-5">
      <div className="h-4 w-48 rounded bg-white/5" />
      <div className="h-48 rounded-2xl bg-white/5" />
      <div className="flex gap-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-10 w-24 rounded-full bg-white/5" />
        ))}
      </div>
      <div className="h-64 rounded-xl bg-white/5" />
    </div>
  );
}

export default function AdminDashboardLoading() {
  return (
    <div className="animate-pulse px-4 py-6 sm:px-6 space-y-5">
      <div className="h-8 w-48 rounded-lg bg-white/5" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-24 rounded-xl bg-white/5" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2 h-80 rounded-xl bg-white/5" />
        <div className="h-80 rounded-xl bg-white/5" />
      </div>
    </div>
  );
}

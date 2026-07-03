import { Inbox } from "lucide-react";

/** タブ共通の空データ表示 */
export function EmptyState({
  icon: Icon = Inbox,
  title,
  desc,
  action,
}: {
  icon?: React.ElementType;
  title: string;
  desc?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 py-20 text-center">
      <Icon className="mb-4 h-12 w-12 text-slate-700" />
      <p className="font-semibold text-white">{title}</p>
      {desc && <p className="mt-1 max-w-sm text-sm text-slate-400">{desc}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

/** タブ共通のローディングスケルトン */
export function TabSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-4 pt-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-24 animate-pulse rounded-xl bg-white/5" />)}
      </div>
      {Array.from({ length: rows }).map((_, i) => <div key={i} className="h-40 animate-pulse rounded-xl bg-white/5" />)}
    </div>
  );
}

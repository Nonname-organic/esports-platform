import { cn } from "@/lib/utils";

export interface StatItem {
  label: string;
  value: string;
  hint?: string;
  highlight?: boolean;
}

interface StatsGridProps {
  items: StatItem[];
  cols?: 2 | 3 | 4;
  title?: string;
}

/** ラベル/値のグリッド。値が "—"（空データ）でも崩れないよう統一表示 */
export function StatsGrid({ items, cols = 3, title }: StatsGridProps) {
  return (
    <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
      {title && <h2 className="mb-4 text-sm font-bold text-white">{title}</h2>}
      <div
        className={cn(
          "grid gap-x-6 gap-y-3 text-sm",
          cols === 2 && "grid-cols-2",
          cols === 3 && "grid-cols-2 lg:grid-cols-3",
          cols === 4 && "grid-cols-2 lg:grid-cols-4",
        )}
      >
        {items.map(({ label, value, hint, highlight }) => (
          <div key={label} className="flex items-center justify-between border-b border-white/5 pb-2">
            <span className="flex items-center gap-1 text-slate-500">
              {label}
              {hint && <span className="text-[10px] text-slate-600">({hint})</span>}
            </span>
            <span className={cn("font-semibold tabular-nums", highlight ? "text-brand-400" : "text-white")}>
              {value}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

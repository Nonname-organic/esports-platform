import { cn } from "@/lib/utils";

interface SummaryCardProps {
  icon: React.ElementType;
  iconBg: string;
  iconColor: string;
  label: string;
  main: string;
  sub?: string;
}

/** アイコン付きの1指標サマリーカード（Overview / 各タブのKPI表示用） */
export function SummaryCard({ icon: Icon, iconBg, iconColor, label, main, sub }: SummaryCardProps) {
  return (
    <div className="rounded-xl border border-white/10 bg-slate-900 p-4">
      <div className={cn("mb-3 inline-flex rounded-lg p-2", iconBg)}>
        <Icon className={cn("h-4 w-4", iconColor)} />
      </div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-0.5 text-lg font-black text-white">{main}</p>
      {sub && <p className="mt-0.5 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

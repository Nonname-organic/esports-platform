import { cn } from "@/lib/utils";
import type { WsStatus } from "@/features/matches/hooks/use-match-admin";

const CONFIG: Record<WsStatus, { label: string; dot: string }> = {
  connected: { label: "接続中", dot: "bg-green-400 animate-pulse" },
  connecting: { label: "接続試行中", dot: "bg-yellow-400 animate-pulse" },
  disconnected: { label: "切断", dot: "bg-red-400" },
};

export function WsIndicator({ status }: { status: WsStatus }) {
  const { label, dot } = CONFIG[status];
  return (
    <div className="flex items-center gap-1.5 rounded-full border border-white/10 bg-slate-900 px-3 py-1.5">
      <span className={cn("h-2 w-2 rounded-full", dot)} />
      <span className="text-xs font-medium text-slate-400">WS {label}</span>
    </div>
  );
}

import Link from "next/link";
import { LayoutDashboard, TrendingUp, Swords, Target } from "lucide-react";
import { cn } from "@/lib/utils";

export type PlayerTabId = "overview" | "trend" | "matches" | "agents";

const TABS: Array<{ id: PlayerTabId; label: string; icon: React.ElementType }> = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "trend", label: "Trend", icon: TrendingUp },
  { id: "matches", label: "Matches", icon: Swords },
  { id: "agents", label: "Agents", icon: Target },
];

interface PlayerTabsProps {
  activeTab: string;
  id: string;
}

export function PlayerTabs({ activeTab, id }: PlayerTabsProps) {
  return (
    <nav
      className="flex overflow-x-auto border-b border-white/10 scrollbar-none"
      aria-label="プレイヤー詳細タブ"
    >
      {TABS.map(({ id: tabId, label, icon: Icon }) => {
        const isActive = activeTab === tabId;
        return (
          <Link
            key={tabId}
            href={`/players/${id}?tab=${tabId}`}
            className={cn(
              "flex flex-shrink-0 items-center gap-2 border-b-2 px-5 py-3 text-sm font-medium transition-colors",
              isActive
                ? "border-brand-500 text-brand-400"
                : "border-transparent text-slate-500 hover:text-slate-300",
            )}
            aria-current={isActive ? "page" : undefined}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

import Link from "next/link";
import { LayoutDashboard, Users, Swords, BarChart2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type TeamTabId = "overview" | "players" | "matches" | "analytics";

const TABS: Array<{ id: TeamTabId; label: string; icon: React.ElementType }> = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "players", label: "Players", icon: Users },
  { id: "matches", label: "Matches", icon: Swords },
  { id: "analytics", label: "Analytics", icon: BarChart2 },
];

interface TeamTabsProps {
  activeTab: string;
  id: string;
}

export function TeamTabs({ activeTab, id }: TeamTabsProps) {
  return (
    <nav
      className="flex overflow-x-auto border-b border-white/10 scrollbar-none"
      aria-label="チーム詳細タブ"
    >
      {TABS.map(({ id: tabId, label, icon: Icon }) => {
        const isActive = activeTab === tabId;
        return (
          <Link
            key={tabId}
            href={`/teams/${id}?tab=${tabId}`}
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

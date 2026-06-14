import Link from "next/link";
import { LayoutDashboard, Swords, Trophy, ListOrdered, BarChart2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type TabId = "overview" | "matches" | "bracket" | "standings" | "analytics";

const TABS: Array<{ id: TabId; label: string; icon: React.ElementType }> = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "matches", label: "Matches", icon: Swords },
  { id: "bracket", label: "Bracket", icon: Trophy },
  { id: "standings", label: "Standings", icon: ListOrdered },
  { id: "analytics", label: "Analytics", icon: BarChart2 },
];

interface TournamentTabsProps {
  activeTab: string;
  id: string;
}

export function TournamentTabs({ activeTab, id }: TournamentTabsProps) {
  return (
    <nav
      className="flex overflow-x-auto border-b border-white/10 scrollbar-none"
      aria-label="大会詳細タブ"
    >
      {TABS.map(({ id: tabId, label, icon: Icon }) => {
        const isActive = activeTab === tabId;
        return (
          <Link
            key={tabId}
            href={`/tournaments/${id}?tab=${tabId}`}
            className={cn(
              "flex flex-shrink-0 items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors",
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

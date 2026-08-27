import { MatchOverviewTab } from "@/features/matches/components/match-overview-tab";
import type { MatchDetail } from "@/types/match";

interface OverviewTabProps {
  match: MatchDetail;
}

/** ブラケットの詳細パネルと同じ内容を出すため、実体は features 側に共有している。 */
export function OverviewTab({ match }: OverviewTabProps) {
  return <MatchOverviewTab match={match} />;
}

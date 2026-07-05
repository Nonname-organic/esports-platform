import type { LucideIcon } from "lucide-react";
import { UserPlus, Radio, Trophy, Star, Swords, GitBranch, Megaphone, Activity } from "lucide-react";

/** Activity 種別のメタ（色分け + アイコン + ラベル）。ENTRY/LIVE/WINNER/MVP/MATCH/BRACKET。 */
export interface ActivityMeta {
  label: string;
  Icon: LucideIcon;
  color: string;
  bg: string;
  dot: string;
}

export function activityMeta(type: string): ActivityMeta {
  if (type.includes("mvp"))
    return { label: "MVP", Icon: Star, color: "text-pink-400", bg: "bg-pink-500/10", dot: "bg-pink-400" };
  if (type.includes("bracket"))
    return { label: "BRACKET", Icon: GitBranch, color: "text-purple-400", bg: "bg-purple-500/10", dot: "bg-purple-400" };
  if (type.includes("match"))
    return { label: "MATCH", Icon: Swords, color: "text-orange-400", bg: "bg-orange-500/10", dot: "bg-orange-400" };
  if (type === "tournament.completed")
    return { label: "WINNER", Icon: Trophy, color: "text-yellow-400", bg: "bg-yellow-500/10", dot: "bg-yellow-400" };
  if (type.startsWith("player.team") || type.includes("registration") || type.includes("entry"))
    return { label: "ENTRY", Icon: UserPlus, color: "text-green-400", bg: "bg-green-500/10", dot: "bg-green-400" };
  if (type.includes("ongoing") || type.includes("live"))
    return { label: "LIVE", Icon: Radio, color: "text-red-400", bg: "bg-red-500/10", dot: "bg-red-400" };
  if (type.startsWith("tournament"))
    return { label: "OPEN", Icon: Megaphone, color: "text-green-400", bg: "bg-green-500/10", dot: "bg-green-400" };
  return { label: "", Icon: Activity, color: "text-slate-400", bg: "bg-white/5", dot: "bg-slate-400" };
}

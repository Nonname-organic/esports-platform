"use client";

import { useState } from "react";
import Link from "next/link";
import { TrendingUp, Trophy, Shield, User, Tag as TagIcon } from "lucide-react";
import { cn, getGameColor } from "@/lib/utils";
import type { HomeTrending } from "@/features/home/api/home-api";
import { RankBadge } from "@/components/rank-badge";

type Cat = "tournaments" | "teams" | "players" | "tags";

/** Trending Now: 人気カテゴリ横スクロール（大会/チーム/選手/タグ）。 */
export function TrendingNow({ trending }: { trending: HomeTrending }) {
  const [cat, setCat] = useState<Cat>("tournaments");
  const tabs: [Cat, string, React.ElementType][] = [
    ["tournaments", "大会", Trophy], ["teams", "チーム", Shield], ["players", "選手", User], ["tags", "タグ", TagIcon],
  ];
  const empty = trending[cat].length === 0;

  return (
    <section>
      <div className="mb-3 flex items-center gap-3">
        <h2 className="flex items-center gap-2 text-lg font-bold text-white"><TrendingUp className="h-5 w-5 text-brand-400" /> Trending Now</h2>
        <div className="inline-flex rounded-full border border-white/10 bg-white/5 p-1">
          {tabs.map(([c, label, Icon]) => (
            <button key={c} onClick={() => setCat(c)}
              className={cn("inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-bold transition-colors", cat === c ? "bg-brand-500 text-white" : "text-slate-400 hover:text-white")}>
              <Icon className="h-3 w-3" />{label}
            </button>
          ))}
        </div>
      </div>

      {empty ? (
        <p className="rounded-xl border border-white/10 bg-slate-900 px-4 py-6 text-center text-sm text-slate-500">まだトレンドデータがありません。</p>
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin">
          {cat === "tournaments" && trending.tournaments.map((t) => (
            <Link key={t.id} href={`/tournaments/${t.id}`} className="w-56 flex-shrink-0 rounded-xl border border-white/10 bg-slate-900 p-4 transition-all hover:-translate-y-0.5 hover:border-white/20">
              <span className={cn("inline-block rounded-full border px-2 py-0.5 text-[10px] font-bold", getGameColor(t.game))}>{t.game}</span>
              <p className="mt-2 line-clamp-2 text-sm font-bold text-white">{t.name}</p>
              <p className="mt-1 text-xs text-slate-500">{t.registered}/{t.max_teams} Teams</p>
            </Link>
          ))}
          {cat === "teams" && trending.teams.map((t) => (
            <Link key={t.team_id} href={`/teams/${t.team_id}`} className="w-52 flex-shrink-0 rounded-xl border border-white/10 bg-slate-900 p-4 transition-all hover:-translate-y-0.5 hover:border-white/20">
              <p className="truncate font-bold text-white">{t.team_name}</p>
              <div className="mt-2 flex items-center justify-between">
                <RankBadge tierKey={t.tier_label.toLowerCase()} label={t.tier_label} color={t.tier_color} variant="compact" />
                <span className="text-xs font-black text-white">{t.rp.toLocaleString()} RP</span>
              </div>
            </Link>
          ))}
          {cat === "players" && trending.players.map((p) => (
            <Link key={p.player_id} href={`/players/${p.player_id}`} className="w-52 flex-shrink-0 rounded-xl border border-white/10 bg-slate-900 p-4 transition-all hover:-translate-y-0.5 hover:border-white/20">
              <p className="truncate font-bold text-white">{p.in_game_name}</p>
              <div className="mt-2 flex items-center justify-between">
                <RankBadge tierKey={p.tier_label.toLowerCase()} label={p.tier_label} color={p.tier_color} variant="compact" />
                <span className="text-xs font-black text-white">{p.rp.toLocaleString()} RP</span>
              </div>
            </Link>
          ))}
          {cat === "tags" && trending.tags.map((t) => (
            <span key={t.slug} className="flex-shrink-0 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-300">
              #{t.label} <span className="ml-1 text-xs text-slate-500">{t.count}</span>
            </span>
          ))}
        </div>
      )}
    </section>
  );
}

import { Shield, CheckCircle2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MatchDetail, BanPick } from "@/types/match";

interface BanPickTabProps {
  match: MatchDetail;
}

export function BanPickTab({ match }: BanPickTabProps) {
  if (match.ban_picks.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center pt-4">
        <p className="text-sm text-slate-500">Ban/Pickデータがありません</p>
      </div>
    );
  }

  const sorted = [...match.ban_picks].sort((a, b) => a.order - b.order);
  const bans = sorted.filter((bp) => bp.action === "ban");
  const picks = sorted.filter((bp) => bp.action === "pick");

  return (
    <div className="space-y-5 pt-4">
      {/* 視覚的シーケンス */}
      <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <h2 className="mb-4 text-sm font-bold text-white">Ban/Pickシーケンス</h2>
        <div className="space-y-2">
          {sorted.map((bp) => (
            <BanPickRow key={bp.order} bp={bp} match={match} />
          ))}
        </div>
      </section>

      {/* Ban一覧 */}
      {bans.length > 0 && (
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h2 className="mb-3 text-sm font-bold text-red-400 flex items-center gap-2">
            <XCircle className="h-4 w-4" />
            BANされたマップ
          </h2>
          <div className="flex flex-wrap gap-2">
            {bans.map((bp) => (
              <span key={bp.order} className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-1.5 text-sm text-red-400">
                {bp.map_name}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Pick一覧 */}
      {picks.length > 0 && (
        <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
          <h2 className="mb-3 text-sm font-bold text-green-400 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            PICKされたマップ
          </h2>
          <div className="flex flex-wrap gap-2">
            {picks.map((bp) => {
              const team = bp.team_id === match.team1?.id ? match.team1 : match.team2;
              return (
                <div key={bp.order} className="rounded-lg border border-green-500/20 bg-green-500/10 px-3 py-1.5">
                  <p className="text-sm font-semibold text-green-400">{bp.map_name}</p>
                  <p className="text-[10px] text-green-400/60">{team?.name ?? "?"} pick</p>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}

function BanPickRow({ bp, match }: { bp: BanPick; match: MatchDetail }) {
  const isBan = bp.action === "ban";
  const isPick = bp.action === "pick";
  const team = bp.team_id === match.team1?.id ? match.team1 : match.team2;

  return (
    <div className={cn(
      "flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors",
      isBan ? "border border-red-500/10 bg-red-500/5" : "border border-green-500/10 bg-green-500/5",
    )}>
      <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-white/5 text-xs font-bold text-slate-400">
        {bp.order}
      </span>
      <span className={cn(
        "rounded px-1.5 py-0.5 text-[10px] font-black uppercase",
        isBan ? "bg-red-500/10 text-red-400" : "bg-green-500/10 text-green-400",
      )}>
        {bp.action}
      </span>
      <div className="flex items-center gap-1.5">
        {team?.logo_url ? (
          <img src={team.logo_url} alt="" className="h-5 w-5 object-contain" />
        ) : (
          <Shield className="h-4 w-4 text-slate-600" />
        )}
        <span className="text-xs text-slate-400">{team?.name ?? "?"}</span>
      </div>
      <span className="flex-1 text-sm font-semibold text-white">{bp.map_name}</span>
      <span className="text-xs text-slate-600">{bp.map_id}</span>
    </div>
  );
}

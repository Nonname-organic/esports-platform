"use client";

import { Users, Star } from "lucide-react";
import { useTeamMembers } from "@/features/teams/hooks/use-teams";
import { cn, formatDate } from "@/lib/utils";
import type { TeamMember, TeamRole } from "@/types/team";

const ROLE_LABEL: Record<TeamRole, string> = {
  player: "選手",
  coach: "コーチ",
  analyst: "アナリスト",
  manager: "マネージャー",
  substitute: "補欠",
};

const ROLE_STYLE: Record<TeamRole, string> = {
  player: "bg-brand-500/10 text-brand-400",
  coach: "bg-yellow-500/10 text-yellow-400",
  analyst: "bg-purple-500/10 text-purple-400",
  manager: "bg-green-500/10 text-green-400",
  substitute: "bg-slate-500/10 text-slate-400",
};

interface PlayersTabProps {
  teamId: string;
}

export function PlayersTab({ teamId }: PlayersTabProps) {
  const { data: members, isLoading, isError } = useTeamMembers(teamId);

  if (isLoading) {
    return (
      <div className="space-y-3 pt-6">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded-xl bg-white/5" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="py-16 text-center text-slate-400 pt-6">
        メンバー情報の読み込みに失敗しました
      </div>
    );
  }

  if (!members || members.length === 0) {
    return (
      <div className="flex flex-col items-center py-24 text-center pt-6">
        <Users className="mb-4 h-12 w-12 text-slate-700" />
        <p className="font-semibold text-white">メンバーがいません</p>
      </div>
    );
  }

  const active = members.filter((m) => m.is_active);
  const inactive = members.filter((m) => !m.is_active);

  return (
    <div className="space-y-6 pt-6">
      {/* アクティブメンバー */}
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          アクティブ — {active.length}名
        </h2>
        <div className="space-y-2">
          {active.map((member) => (
            <MemberCard key={member.id} member={member} />
          ))}
        </div>
      </section>

      {/* 非アクティブメンバー */}
      {inactive.length > 0 && (
        <section>
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
            旧メンバー — {inactive.length}名
          </h2>
          <div className="space-y-2 opacity-60">
            {inactive.map((member) => (
              <MemberCard key={member.id} member={member} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function MemberCard({ member }: { member: TeamMember }) {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-white/8 bg-slate-900 px-4 py-3 transition-colors hover:border-white/15">
      {/* アバター */}
      <div className="h-10 w-10 flex-shrink-0 overflow-hidden rounded-full border border-white/10 bg-slate-800">
        {member.avatar_url ? (
          <img src={member.avatar_url} alt={member.display_name ?? member.username ?? ""} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <span className="text-sm font-bold text-slate-500">
              {(member.display_name ?? member.username ?? "?").charAt(0).toUpperCase()}
            </span>
          </div>
        )}
      </div>

      {/* 名前 + IGN */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="truncate font-semibold text-white">{member.display_name ?? member.username ?? "Unknown"}</p>
          {member.rating != null && member.rating >= 2000 && (
            <Star className="h-3.5 w-3.5 flex-shrink-0 text-yellow-400" fill="currentColor" />
          )}
        </div>
        {member.in_game_name && (
          <p className="truncate text-xs text-slate-500">
            IGN: <span className="text-slate-400">{member.in_game_name}</span>
          </p>
        )}
      </div>

      {/* エージェント */}
      {member.agent_specialty && member.agent_specialty.length > 0 && (
        <div className="hidden sm:flex items-center gap-1 flex-shrink-0">
          {member.agent_specialty.slice(0, 3).map((agent) => (
            <span key={agent} className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-slate-400">
              {agent}
            </span>
          ))}
        </div>
      )}

      {/* レーティング */}
      {member.rating != null && (
        <div className="hidden sm:block flex-shrink-0 text-right">
          <p className="text-xs text-slate-500">Rating</p>
          <p className="text-sm font-bold text-white">{member.rating.toLocaleString()}</p>
        </div>
      )}

      {/* ロール */}
      <span className={cn("flex-shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold", ROLE_STYLE[member.role])}>
        {ROLE_LABEL[member.role]}
      </span>
    </div>
  );
}

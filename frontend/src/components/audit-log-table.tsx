"use client";

import { History, User as UserIcon } from "lucide-react";
import type { AuditLogItem } from "@/features/audit/api/audit-api";

// action(type) → 日本語ラベル（未定義は type をそのまま表示）
const ACTION_LABEL: Record<string, string> = {
  "team.created": "チーム作成",
  "team.updated": "チーム編集",
  "team.member.added": "メンバー追加",
  "team.member.removed": "メンバー削除",
  "team.member.role_changed": "ロール変更",
  "team.owner.changed": "オーナー変更",
  "tournament.created": "大会作成",
  "tournament.updated": "大会編集",
  "tournament.published": "大会公開",
  "tournament.status.changed": "ステータス変更",
  "tournament.bracket.generated": "ブラケット生成",
  "tournament.registration.approved": "参加承認",
  "tournament.registration.rejected": "参加却下",
  "tournament.completed": "大会完了",
};

function diffText(before: Record<string, unknown> | null, after: Record<string, unknown> | null): string | null {
  if (!before && !after) return null;
  const keys = new Set([...Object.keys(before ?? {}), ...Object.keys(after ?? {})]);
  const parts: string[] = [];
  keys.forEach((k) => {
    const b = before?.[k];
    const a = after?.[k];
    if (JSON.stringify(b) !== JSON.stringify(a)) {
      parts.push(`${k}: ${b ?? "—"} → ${a ?? "—"}`);
    }
  });
  return parts.length ? parts.join(" / ") : null;
}

export function AuditLogTable({ items, isLoading }: { items?: AuditLogItem[]; isLoading?: boolean }) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-12 animate-pulse rounded-lg bg-white/5" />)}
      </div>
    );
  }
  if (!items || items.length === 0) {
    return (
      <div className="flex flex-col items-center rounded-xl border border-dashed border-white/10 py-12 text-center">
        <History className="mb-2 h-8 w-8 text-slate-700" />
        <p className="text-sm text-slate-500">監査ログはまだありません</p>
      </div>
    );
  }
  return (
    <div className="overflow-hidden rounded-xl border border-white/10 bg-slate-900">
      <ul className="divide-y divide-white/5">
        {items.map((it) => {
          const diff = diffText(it.before, it.after);
          return (
            <li key={it.id} className="flex items-start gap-3 px-4 py-3">
              <div className="mt-0.5 rounded-lg bg-white/5 p-1.5">
                <UserIcon className="h-3.5 w-3.5 text-slate-400" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-md bg-brand-500/10 px-2 py-0.5 text-xs font-semibold text-brand-400">
                    {ACTION_LABEL[it.action] ?? it.action}
                  </span>
                  <span className="text-xs text-slate-400">
                    {it.actor_name ?? (it.actor_type === "system" ? "システム" : it.actor_type === "bot" ? "Bot" : "—")}
                  </span>
                  {it.actor_ip && <span className="text-[10px] text-slate-600">{it.actor_ip}</span>}
                </div>
                {diff && <p className="mt-0.5 truncate text-xs text-slate-500">{diff}</p>}
              </div>
              <span className="flex-shrink-0 text-xs text-slate-600">
                {new Date(it.created_at).toLocaleString("ja-JP", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

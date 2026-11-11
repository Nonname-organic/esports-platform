"use client";

import { useState } from "react";
import { Users } from "lucide-react";
import { useAdminUsers, useUpdateAdminUser } from "@/features/admin/hooks/use-admin";
import type { AdminUserItem } from "@/features/admin/api/admin-api";
import { useAuthStore } from "@/store/auth-store";

const ROLE_LABELS: Record<AdminUserItem["role"], string> = {
  admin: "管理者",
  organizer: "主催者",
  team_manager: "チーム管理者",
  player: "選手",
  viewer: "閲覧者",
};

/** 利用停止・再開とロール変更。操作はサーバー側で監査ログに残る。 */
export function UserManagementSection() {
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const me = useAuthStore((s) => s.user);
  const { data: users, isLoading, isError } = useAdminUsers(query);
  const update = useUpdateAdminUser();

  return (
    <section className="rounded-2xl border border-white/10 bg-slate-900 p-5">
      <h2 className="mb-4 flex items-center gap-2 text-sm font-bold text-white">
        <Users className="h-4 w-4 text-brand-400" /> ユーザー管理
      </h2>
      <form
        className="mb-4 flex gap-2"
        onSubmit={(e) => { e.preventDefault(); setQuery(q.trim()); }}
      >
        <label htmlFor="admin-user-search" className="sr-only">ユーザー名またはメールで検索</label>
        <input
          id="admin-user-search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="ユーザー名またはメールで検索"
          className="flex-1 rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-sm text-white placeholder:text-slate-600"
        />
        <button type="submit" className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-bold text-white hover:bg-brand-600">
          検索
        </button>
      </form>

      {update.isError && (
        <p role="alert" className="mb-3 text-sm text-red-400">
          {update.error instanceof Error ? update.error.message : "更新に失敗しました"}
        </p>
      )}
      {isLoading && <p className="text-sm text-slate-500">読み込み中…</p>}
      {isError && <p className="text-sm text-red-400">ユーザー一覧の読み込みに失敗しました</p>}
      {users && users.length === 0 && <p className="text-sm text-slate-500">該当するユーザーはいません</p>}

      {users && users.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-slate-500">
              <tr>
                <th className="py-2 pr-3">ユーザー</th>
                <th className="py-2 pr-3">ロール</th>
                <th className="py-2 pr-3">状態</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isSelf = me?.id === u.id;
                return (
                  <tr key={u.id} className="border-t border-white/5">
                    <td className="py-2 pr-3">
                      <p className="font-semibold text-white">{u.username}</p>
                      <p className="text-xs text-slate-500">{u.email}</p>
                    </td>
                    <td className="py-2 pr-3">
                      <select
                        aria-label={`${u.username} のロール`}
                        value={u.role}
                        disabled={isSelf || update.isPending}
                        onChange={(e) => update.mutate({ id: u.id, role: e.target.value as AdminUserItem["role"] })}
                        className="rounded-lg border border-white/10 bg-slate-950 px-2 py-1 text-xs text-white disabled:opacity-50"
                      >
                        {(Object.keys(ROLE_LABELS) as AdminUserItem["role"][]).map((r) => (
                          <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                        ))}
                      </select>
                    </td>
                    <td className="py-2 pr-3">
                      <span className={u.is_active ? "text-emerald-400" : "text-red-400"}>
                        {u.is_active ? "利用中" : "停止中"}
                      </span>
                    </td>
                    <td className="py-2 text-right">
                      {!isSelf && (
                        <button
                          type="button"
                          disabled={update.isPending}
                          onClick={() => {
                            if (u.is_active && !window.confirm(`${u.username} を利用停止にしますか？`)) return;
                            update.mutate({ id: u.id, is_active: !u.is_active });
                          }}
                          className="rounded-lg border border-white/10 px-3 py-1 text-xs text-slate-300 hover:text-white disabled:opacity-50"
                        >
                          {u.is_active ? "利用停止" : "再開"}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

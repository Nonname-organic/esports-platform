"use client";

import { Bell, Loader2, Check } from "lucide-react";
import { useRequireAuth } from "@/hooks/use-require-auth";
import { useNotificationPrefs, useUpdateNotificationPrefs } from "@/features/notifications/hooks/use-notifications";
import { cn } from "@/lib/utils";

const CHANNELS: { key: string; label: string; desc: string }[] = [
  { key: "browser", label: "ブラウザ通知", desc: "アプリ内通知とリアルタイム表示" },
  { key: "discord", label: "Discord通知", desc: "連携済みアカウントへDM" },
  { key: "email", label: "メール通知", desc: "（準備中）" },
];

const CATEGORIES: { key: string; label: string; desc: string }[] = [
  { key: "tournament", label: "大会", desc: "参加承認・却下・大会の進行" },
  { key: "team", label: "チーム", desc: "メンバー追加・変更など" },
  { key: "scout", label: "スカウト", desc: "募集・応募関連" },
  { key: "match", label: "試合", desc: "試合結果・スケジュール" },
];

function Toggle({ on, onClick, disabled }: { on: boolean; onClick: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "relative h-6 w-11 flex-shrink-0 rounded-full transition-colors disabled:opacity-40",
        on ? "bg-brand-500" : "bg-white/10",
      )}
      aria-pressed={on}
    >
      <span className={cn("absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform",
        on ? "translate-x-5" : "translate-x-0.5")} />
    </button>
  );
}

export default function NotificationSettingsPage() {
  const { ready, authed } = useRequireAuth();
  const { data: prefs, isLoading } = useNotificationPrefs();
  const update = useUpdateNotificationPrefs();

  if (!ready || !authed) return null;

  const toggleChannel = (key: string, cur: boolean) =>
    update.mutate({ channels: { [key]: !cur } });
  const toggleCategory = (key: string, cur: boolean) =>
    update.mutate({ categories: { [key]: !cur } });

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6 flex items-center gap-3">
        <div className="rounded-xl bg-brand-500/10 p-2.5">
          <Bell className="h-6 w-6 text-brand-400" />
        </div>
        <div>
          <h1 className="text-xl font-black text-white">通知設定</h1>
          <p className="text-sm text-slate-500">受け取る通知をチャネル・種別ごとに設定</p>
        </div>
        {update.isPending && <Loader2 className="ml-auto h-4 w-4 animate-spin text-slate-500" />}
        {update.isSuccess && !update.isPending && <Check className="ml-auto h-4 w-4 text-green-400" />}
      </div>

      {isLoading || !prefs ? (
        <div className="space-y-3">
          {Array.from({ length: 2 }).map((_, i) => <div key={i} className="h-40 animate-pulse rounded-2xl bg-white/5" />)}
        </div>
      ) : (
        <div className="space-y-5">
          {/* チャネル */}
          <section className="rounded-2xl border border-white/10 bg-slate-900 p-5">
            <h2 className="mb-4 text-sm font-bold text-white">チャネル</h2>
            <div className="space-y-3">
              {CHANNELS.map((c) => {
                const on = prefs.channels?.[c.key] ?? true;
                return (
                  <div key={c.key} className="flex items-center gap-3">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-white">{c.label}</p>
                      <p className="text-xs text-slate-500">{c.desc}</p>
                    </div>
                    <Toggle on={on} onClick={() => toggleChannel(c.key, on)} disabled={update.isPending} />
                  </div>
                );
              })}
            </div>
            <p className="mt-3 text-xs text-slate-600">※ チャネルをOFFにすると、その手段では全種別の通知が届きません。</p>
          </section>

          {/* 種別 */}
          <section className="rounded-2xl border border-white/10 bg-slate-900 p-5">
            <h2 className="mb-4 text-sm font-bold text-white">通知の種別</h2>
            <div className="space-y-3">
              {CATEGORIES.map((c) => {
                const on = prefs.categories?.[c.key] ?? true;
                return (
                  <div key={c.key} className="flex items-center gap-3">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-white">{c.label}</p>
                      <p className="text-xs text-slate-500">{c.desc}</p>
                    </div>
                    <Toggle on={on} onClick={() => toggleCategory(c.key, on)} disabled={update.isPending} />
                  </div>
                );
              })}
            </div>
          </section>

          {update.isError && (
            <p className="text-sm text-red-400">
              {update.error instanceof Error ? update.error.message : "更新に失敗しました"}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

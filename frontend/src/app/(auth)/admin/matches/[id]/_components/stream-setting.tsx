"use client";

import { useState } from "react";
import { Radio, Loader2, Check } from "lucide-react";
import { matchApi } from "@/features/matches/api/match-api";
import { ApiError } from "@/lib/api-client";
import type { MatchDetail } from "@/types/match";

/**
 * この試合を配信対象にする設定。
 *
 * 設定するのは最初の1回だけで、配信の開始・終了にあわせてこの画面を
 * 操作する必要はない。運営の手間を増やさないため、状態の管理はせず
 * 「この試合はここで配信する」という事実だけを持たせている。
 *
 * 設定するとブラケットに「配信」の印が出て、そこから配信へ直接飛べる。
 */
export function StreamSetting({ match }: { match: MatchDetail }) {
  const [url, setUrl] = useState(match.stream_url ?? "");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setSaving(true);
    setError(null);
    setDone(false);
    try {
      await matchApi.setStreamUrl(String(match.id), url.trim());
      setDone(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "保存に失敗しました");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="rounded-xl border border-white/10 bg-slate-900">
      <div className="flex items-center gap-2 border-b border-white/10 px-5 py-3">
        <Radio className="h-4 w-4 text-red-400" />
        <h2 className="text-sm font-bold text-white">配信設定</h2>
        <span className="ml-auto text-xs text-slate-500">
          ブラケットに印が出て、そこから配信へ飛べます
        </span>
      </div>

      <div className="space-y-3 p-5">
        <label className="block text-xs font-medium text-slate-400">
          配信URL（Twitch / YouTube など）
        </label>
        <div className="flex gap-2">
          <input
            type="url"
            value={url}
            onChange={(e) => { setUrl(e.target.value); setDone(false); }}
            placeholder="https://twitch.tv/your-channel"
            className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-slate-600 outline-none transition-colors focus:border-brand-500"
          />
          <button
            onClick={save}
            disabled={saving}
            className="flex items-center gap-1.5 rounded-lg bg-brand-500 px-4 py-2 text-sm font-bold text-white transition-colors hover:bg-brand-600 disabled:opacity-50"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            保存
          </button>
        </div>
        <p className="text-xs text-slate-500">
          最初に1回設定するだけで、配信の開始・終了にあわせた操作は要りません。
          空のまま保存すると配信対象から外れます。
        </p>
        {done && (
          <p className="flex items-center gap-1 text-xs text-green-400">
            <Check className="h-3.5 w-3.5" />
            {url.trim() ? "配信試合に設定しました" : "配信設定を解除しました"}
          </p>
        )}
        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>
    </section>
  );
}

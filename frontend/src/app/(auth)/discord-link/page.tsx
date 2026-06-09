"use client";

import { useState } from "react";
import { Check, Copy, Link2, Loader2, RefreshCw } from "lucide-react";
import { discordApi } from "@/features/discord/api/discord-api";
import { useDiscordLink, useIssueLinkCode } from "@/features/discord/hooks/use-discord";

export default function DiscordLinkPage() {
  const { data: link, isLoading, refetch } = useDiscordLink();
  const issue = useIssueLinkCode();
  const [code, setCode] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [oauthLoading, setOauthLoading] = useState(false);
  const [oauthError, setOauthError] = useState<string | null>(null);

  const handleIssue = async () => {
    const res = await issue.mutateAsync();
    setCode(res.data.code);
    setCopied(false);
  };

  const handleCopy = async () => {
    if (!code) return;
    await navigator.clipboard.writeText(`/link code:${code}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleOAuth = async () => {
    setOauthError(null);
    setOauthLoading(true);
    try {
      const res = await discordApi.oauthUrl();
      if (res.data.url) {
        window.location.href = res.data.url;
      } else {
        setOauthError("OAuthが未設定です（管理者がDISCORD_CLIENT_ID等を設定してください）。コード連携をご利用ください。");
      }
    } catch {
      setOauthError("OAuth URLの取得に失敗しました。コード連携をご利用ください。");
    } finally {
      setOauthLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6 flex items-center gap-3">
        <div className="rounded-lg bg-[#5865F2]/15 p-2.5">
          <Link2 className="h-6 w-6 text-[#5865F2]" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">Discord 連携</h1>
          <p className="text-sm text-slate-400">Discordから大会操作（チェックイン・結果報告など）を行うために連携します</p>
        </div>
      </div>

      {/* 連携状態 */}
      <section className="mb-6 rounded-xl border border-white/10 bg-slate-900 p-5">
        {isLoading ? (
          <div className="flex items-center gap-2 text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin" /> 読み込み中...
          </div>
        ) : link ? (
          <div className="flex items-center gap-3">
            <Check className="h-5 w-5 text-green-400" />
            <div className="flex-1">
              <p className="font-semibold text-white">連携済み</p>
              <p className="text-xs text-slate-500">
                {link.discord_username ?? link.discord_user_id} ・ {new Date(link.linked_at).toLocaleString("ja-JP")}
              </p>
            </div>
            <button
              onClick={() => refetch()}
              className="flex items-center gap-1.5 rounded-lg bg-white/5 px-3 py-2 text-xs text-slate-300 hover:bg-white/10"
            >
              <RefreshCw className="h-3.5 w-3.5" /> 更新
            </button>
          </div>
        ) : (
          <p className="text-sm text-slate-400">まだ連携されていません。下の方法で連携してください。</p>
        )}
      </section>

      {/* 方法A: コード連携（推奨） */}
      <section className="mb-5 rounded-xl border border-brand-500/30 bg-slate-900 p-5">
        <div className="mb-3 flex items-center gap-2">
          <span className="rounded-md bg-brand-500/20 px-2 py-0.5 text-xs font-bold text-brand-300">推奨</span>
          <h2 className="font-bold text-white">コードで連携</h2>
        </div>
        <ol className="mb-4 space-y-1 text-sm text-slate-400">
          <li>1. 下のボタンで連携コードを発行</li>
          <li>2. Discordで <code className="rounded bg-white/10 px-1.5 py-0.5 text-brand-300">/link code:コード</code> を実行</li>
        </ol>
        {code ? (
          <div className="flex items-center gap-3">
            <div className="flex-1 rounded-lg border border-white/10 bg-black/30 px-4 py-3 text-center text-2xl font-mono font-bold tracking-[0.3em] text-white">
              {code}
            </div>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 rounded-lg bg-brand-500 px-4 py-3 text-sm font-bold text-white hover:bg-brand-600"
            >
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copied ? "コピー済" : "コマンドをコピー"}
            </button>
          </div>
        ) : (
          <button
            onClick={handleIssue}
            disabled={issue.isPending}
            className="flex items-center gap-2 rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
          >
            {issue.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            連携コードを発行
          </button>
        )}
        {code && <p className="mt-2 text-xs text-slate-500">※ コードの有効期限は5分です。Discordで実行すると連携が完了します。</p>}
      </section>

      {/* 方法B: OAuth */}
      <section className="rounded-xl border border-white/10 bg-slate-900 p-5">
        <h2 className="mb-2 font-bold text-white">Discord OAuthで連携</h2>
        <p className="mb-3 text-sm text-slate-400">Discordの認可画面で連携します（管理者がOAuth設定済みの場合）。</p>
        <button
          onClick={handleOAuth}
          disabled={oauthLoading}
          className="flex items-center gap-2 rounded-lg bg-[#5865F2] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#4752c4] disabled:opacity-50"
        >
          {oauthLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Link2 className="h-4 w-4" />}
          Discordで認可
        </button>
        {oauthError && <p className="mt-2 text-xs text-amber-400">{oauthError}</p>}
      </section>
    </div>
  );
}

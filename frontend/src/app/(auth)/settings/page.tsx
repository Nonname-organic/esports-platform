"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useRequireAuth } from "@/hooks/use-require-auth";
import { AlertTriangle, Check, Link2, Loader2, Lock, Mail, RefreshCw, Settings as SettingsIcon, Unlink } from "lucide-react";
import { apiClient, ApiError } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";
import { discordApi } from "@/features/discord/api/discord-api";
import { useDiscordLink, useIssueLinkCode } from "@/features/discord/hooks/use-discord";

const inputCls =
  "w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder-slate-600 outline-none focus:border-brand-500 transition-colors";

function Notice({ type, msg }: { type: "ok" | "err"; msg: string }) {
  return (
    <p className={`mt-2 flex items-center gap-1.5 text-xs ${type === "ok" ? "text-green-400" : "text-red-400"}`}>
      {type === "ok" ? <Check className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
      {msg}
    </p>
  );
}

function DiscordSection() {
  const { data: link, isLoading, refetch } = useDiscordLink();
  const issue = useIssueLinkCode();
  const [code, setCode] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [unlinking, setUnlinking] = useState(false);
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
        setOauthError("OAuthが未設定です。コード連携をご利用ください。");
      }
    } catch {
      setOauthError("OAuth URLの取得に失敗しました。コード連携をご利用ください。");
    } finally {
      setOauthLoading(false);
    }
  };

  return (
    <section className="mb-5 rounded-2xl border border-white/10 bg-slate-900 p-5">
      <h2 className="mb-4 flex items-center gap-2 text-sm font-bold text-white">
        <Link2 className="h-4 w-4 text-[#5865F2]" /> Discord 連携
      </h2>

      {/* 連携状態 */}
      <div className="mb-4 rounded-xl border border-white/8 bg-white/3 p-3">
        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin" /> 読み込み中...
          </div>
        ) : link ? (
          <div className="flex items-center gap-3">
            <Check className="h-4 w-4 text-green-400 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white">連携済み</p>
              <p className="text-xs text-slate-500 truncate">
                {link.discord_username ?? link.discord_user_id} ・ {new Date(link.linked_at).toLocaleDateString("ja-JP")}
              </p>
            </div>
            <button onClick={() => refetch()} className="rounded-lg bg-white/5 p-1.5 text-slate-400 hover:text-white">
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={async () => {
                if (!confirm("Discord連携を解除しますか？")) return;
                setUnlinking(true);
                try { await discordApi.unlink(); await refetch(); } finally { setUnlinking(false); }
              }}
              disabled={unlinking}
              className="flex items-center gap-1 rounded-lg bg-red-500/10 px-2.5 py-1.5 text-xs text-red-400 hover:bg-red-500/20 disabled:opacity-50"
            >
              {unlinking ? <Loader2 className="h-3 w-3 animate-spin" /> : <Unlink className="h-3 w-3" />} 解除
            </button>
          </div>
        ) : (
          <p className="text-sm text-slate-400">未連携</p>
        )}
      </div>

      {/* コード連携 */}
      <div className="mb-3 rounded-xl border border-brand-500/20 bg-brand-500/5 p-4">
        <p className="mb-2 text-xs font-semibold text-brand-300">コードで連携（推奨）</p>
        <ol className="mb-3 space-y-0.5 text-xs text-slate-400">
          <li>1. 下のボタンで連携コードを発行</li>
          <li>2. Discordで <code className="rounded bg-white/10 px-1 text-brand-300">/link code:コード</code> を実行</li>
        </ol>
        {code ? (
          <div className="flex items-center gap-2">
            <div className="flex-1 rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-center text-xl font-mono font-bold tracking-[0.25em] text-white">
              {code}
            </div>
            <button onClick={handleCopy} className="flex items-center gap-1.5 rounded-lg bg-brand-500 px-3 py-2 text-xs font-bold text-white hover:bg-brand-600">
              {copied ? <Check className="h-3.5 w-3.5" /> : null}{copied ? "コピー済" : "コピー"}
            </button>
          </div>
        ) : (
          <button onClick={handleIssue} disabled={issue.isPending}
            className="flex items-center gap-2 rounded-lg bg-brand-500 px-3 py-2 text-xs font-bold text-white hover:bg-brand-600 disabled:opacity-50">
            {issue.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            コードを発行
          </button>
        )}
      </div>

      {/* OAuth */}
      <div>
        <button onClick={handleOAuth} disabled={oauthLoading}
          className="flex items-center gap-2 rounded-lg bg-[#5865F2]/20 px-3 py-2 text-xs font-bold text-[#7289da] hover:bg-[#5865F2]/30 disabled:opacity-50">
          {oauthLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Link2 className="h-3.5 w-3.5" />}
          Discord OAuthで連携
        </button>
        {oauthError && <p className="mt-1.5 text-xs text-amber-400">{oauthError}</p>}
      </div>
    </section>
  );
}

export default function SettingsPage() {
  const { ready, authed } = useRequireAuth();
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const logout = useAuthStore((s) => s.logout);

  const [newEmail, setNewEmail] = useState("");
  const [emailPw, setEmailPw] = useState("");
  const [emailState, setEmailState] = useState<{ loading: boolean; ok?: string; err?: string }>({ loading: false });

  const [curPw, setCurPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [pwState, setPwState] = useState<{ loading: boolean; ok?: string; err?: string }>({ loading: false });

  const [delPw, setDelPw] = useState("");
  const [delConfirm, setDelConfirm] = useState(false);
  const [delState, setDelState] = useState<{ loading: boolean; err?: string }>({ loading: false });

  if (!ready || !authed) return null;

  const changeEmail = async () => {
    setEmailState({ loading: true });
    try {
      await apiClient.patch("/api/v1/auth/email", { password: emailPw, new_email: newEmail });
      if (user) setUser({ ...user, email: newEmail });
      setEmailState({ loading: false, ok: "メールアドレスを変更しました" });
      setEmailPw("");
    } catch (e) {
      setEmailState({ loading: false, err: e instanceof ApiError ? e.message : "変更に失敗しました" });
    }
  };

  const changePassword = async () => {
    setPwState({ loading: true });
    try {
      await apiClient.patch("/api/v1/auth/password", { current_password: curPw, new_password: newPw });
      setPwState({ loading: false, ok: "パスワードを変更しました" });
      setCurPw(""); setNewPw("");
    } catch (e) {
      setPwState({ loading: false, err: e instanceof ApiError ? e.message : "変更に失敗しました" });
    }
  };

  const deleteAccount = async () => {
    setDelState({ loading: true });
    try {
      await apiClient.delete("/api/v1/auth/account", { body: JSON.stringify({ password: delPw }) });
      logout();
      router.push("/");
    } catch (e) {
      setDelState({ loading: false, err: e instanceof ApiError ? e.message : "退会に失敗しました" });
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6 flex items-center gap-3">
        <div className="rounded-xl bg-brand-500/10 p-2.5">
          <SettingsIcon className="h-6 w-6 text-brand-400" />
        </div>
        <div>
          <h1 className="text-xl font-black text-white">ユーザー設定</h1>
          <p className="text-sm text-slate-500">{user?.username} ({user?.email ?? "—"})</p>
        </div>
      </div>

      {/* Discord 連携 */}
      <DiscordSection />

      {/* メールアドレス変更 */}
      <section className="mb-5 rounded-2xl border border-white/10 bg-slate-900 p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-bold text-white">
          <Mail className="h-4 w-4 text-brand-400" /> メールアドレス変更
        </h2>
        <div className="space-y-3">
          <input type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} className={inputCls} placeholder="新しいメールアドレス" />
          <input type="password" value={emailPw} onChange={(e) => setEmailPw(e.target.value)} className={inputCls} placeholder="現在のパスワード（確認）" />
          <button onClick={changeEmail} disabled={emailState.loading || !newEmail || !emailPw}
            className="flex items-center gap-2 rounded-lg bg-brand-500 px-4 py-2 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-40 transition-colors">
            {emailState.loading && <Loader2 className="h-4 w-4 animate-spin" />} メールを変更
          </button>
          {emailState.ok && <Notice type="ok" msg={emailState.ok} />}
          {emailState.err && <Notice type="err" msg={emailState.err} />}
        </div>
      </section>

      {/* パスワード変更 */}
      <section className="mb-5 rounded-2xl border border-white/10 bg-slate-900 p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-bold text-white">
          <Lock className="h-4 w-4 text-brand-400" /> パスワード変更
        </h2>
        <div className="space-y-3">
          <input type="password" value={curPw} onChange={(e) => setCurPw(e.target.value)} className={inputCls} placeholder="現在のパスワード" />
          <input type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} className={inputCls} placeholder="新しいパスワード（8文字以上）" />
          <button onClick={changePassword} disabled={pwState.loading || !curPw || newPw.length < 8}
            className="flex items-center gap-2 rounded-lg bg-brand-500 px-4 py-2 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-40 transition-colors">
            {pwState.loading && <Loader2 className="h-4 w-4 animate-spin" />} パスワードを変更
          </button>
          {pwState.ok && <Notice type="ok" msg={pwState.ok} />}
          {pwState.err && <Notice type="err" msg={pwState.err} />}
        </div>
      </section>

      {/* 退会 */}
      <section className="rounded-2xl border border-red-500/20 bg-red-500/5 p-5">
        <h2 className="mb-2 flex items-center gap-2 text-sm font-bold text-red-400">
          <AlertTriangle className="h-4 w-4" /> 退会
        </h2>
        <p className="mb-4 text-xs text-slate-500">退会するとアカウントは無効化され、ログインできなくなります。</p>
        {!delConfirm ? (
          <button onClick={() => setDelConfirm(true)}
            className="rounded-lg border border-red-500/30 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors">
            退会手続きへ
          </button>
        ) : (
          <div className="space-y-3">
            <input type="password" value={delPw} onChange={(e) => setDelPw(e.target.value)} className={inputCls} placeholder="パスワードを入力して確認" />
            <div className="flex gap-2">
              <button onClick={deleteAccount} disabled={delState.loading || !delPw}
                className="flex items-center gap-2 rounded-lg bg-red-500 px-4 py-2 text-sm font-bold text-white hover:bg-red-600 disabled:opacity-40 transition-colors">
                {delState.loading && <Loader2 className="h-4 w-4 animate-spin" />} 退会する
              </button>
              <button onClick={() => { setDelConfirm(false); setDelPw(""); setDelState({ loading: false }); }}
                className="rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors">
                キャンセル
              </button>
            </div>
            {delState.err && <Notice type="err" msg={delState.err} />}
          </div>
        )}
      </section>
    </div>
  );
}

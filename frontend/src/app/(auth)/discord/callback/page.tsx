"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Check, Loader2, XCircle } from "lucide-react";
import { discordApi } from "@/features/discord/api/discord-api";

export default function DiscordCallbackPage() {
  const [state, setState] = useState<"loading" | "ok" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    if (!code) {
      setState("error");
      setMessage("認可コードが見つかりません。");
      return;
    }
    discordApi
      .oauthCallback(code)
      .then((res) => {
        setState("ok");
        setMessage(`@${res.data.discord_username ?? res.data.discord_user_id} と連携しました。`);
      })
      .catch((e) => {
        setState("error");
        setMessage(e instanceof Error ? e.message : "連携に失敗しました。");
      });
  }, []);

  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-4 py-20 text-center">
      {state === "loading" && (
        <>
          <Loader2 className="h-10 w-10 animate-spin text-brand-500" />
          <p className="mt-4 text-slate-300">Discord連携を処理中...</p>
        </>
      )}
      {state === "ok" && (
        <>
          <Check className="h-12 w-12 text-green-400" />
          <h1 className="mt-4 text-lg font-bold text-white">連携完了</h1>
          <p className="mt-1 text-sm text-slate-400">{message}</p>
          <Link href="/discord-link" className="mt-6 rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-bold text-white hover:bg-brand-600">
            連携ページへ戻る
          </Link>
        </>
      )}
      {state === "error" && (
        <>
          <XCircle className="h-12 w-12 text-red-400" />
          <h1 className="mt-4 text-lg font-bold text-white">連携に失敗しました</h1>
          <p className="mt-1 text-sm text-slate-400">{message}</p>
          <Link href="/discord-link" className="mt-6 rounded-lg bg-white/10 px-5 py-2.5 text-sm font-bold text-white hover:bg-white/20">
            コード連携を試す
          </Link>
        </>
      )}
    </div>
  );
}

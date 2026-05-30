"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";
import { useMatchAdmin } from "@/features/matches/hooks/use-match-admin";
import type { MatchDetail } from "@/types/match";
import { MatchHeader } from "./match-header";
import { StatusControls } from "./status-controls";
import { GameManager } from "./game-manager";
import { BanPickPanel } from "./banpick-panel";
import { WsIndicator } from "./ws-indicator";

interface MatchAdminClientProps {
  matchId: string;
  initialMatch: MatchDetail;
  game: string;
}

export function MatchAdminClient({ matchId, initialMatch, game }: MatchAdminClientProps) {
  const router = useRouter();
  const hasRole = useAuthStore((s) => s.hasRole);

  // 権限チェック（クライアント側）
  useEffect(() => {
    if (!hasRole("admin", "organizer")) {
      router.replace("/dashboard");
    }
  }, [hasRole, router]);

  const {
    match,
    isLoading,
    wsStatus,
    startMatch,
    updateScore,
    registerResult,
    registerBanPick,
  } = useMatchAdmin(matchId, initialMatch);

  if (isLoading && !match) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  if (!match) return null;

  return (
    <div className="space-y-5">
      {/* WS状態 + ヘッダー */}
      <div className="flex items-center justify-end">
        <WsIndicator status={wsStatus} />
      </div>

      <MatchHeader match={match} />

      {/* ステータスコントロール */}
      <StatusControls
        match={match}
        startMatch={startMatch}
        registerResult={registerResult}
      />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* ゲーム管理 */}
        <GameManager match={match} game={game} updateScore={updateScore} />

        {/* Ban/Pick */}
        <BanPickPanel match={match} game={game} registerBanPick={registerBanPick} />
      </div>
    </div>
  );
}

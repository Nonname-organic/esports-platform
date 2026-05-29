"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { BracketView } from "@/features/tournaments/components/bracket/bracket-view";
import { useBracket, tournamentKeys } from "@/features/tournaments/hooks/use-tournaments";
import type { BracketResponse } from "@/types/tournament";

interface Props {
  tournamentId: string;
  initialBracket: BracketResponse | null;
}

export function BracketPageClient({ tournamentId, initialBracket }: Props) {
  const qc = useQueryClient();

  // SSR で取得した初期データをキャッシュに注入（ハイドレーション）
  useEffect(() => {
    if (initialBracket) {
      qc.setQueryData(tournamentKeys.bracket(tournamentId), { data: initialBracket, meta: null });
    }
  }, [initialBracket, tournamentId, qc]);

  // 30秒ポーリングで最新ブラケットを取得
  const { data: bracket, isLoading } = useBracket(tournamentId);

  if (isLoading && !initialBracket) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  const displayBracket = bracket ?? initialBracket;

  if (!displayBracket) {
    return (
      <div className="rounded-xl border border-white/10 bg-slate-900 py-16 text-center">
        <p className="text-slate-400">ブラケットはまだ生成されていません</p>
      </div>
    );
  }

  return <BracketView bracket={displayBracket} />;
}

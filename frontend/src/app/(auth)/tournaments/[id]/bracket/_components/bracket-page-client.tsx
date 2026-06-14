"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Trophy } from "lucide-react";
import { BracketView } from "@/features/tournaments/components/bracket/bracket-view";
import { useBracket, tournamentKeys } from "@/features/tournaments/hooks/use-tournaments";
import type { BracketResponse } from "@/types/tournament";

interface Props {
  tournamentId: string;
  initialBracket: BracketResponse | null;
}

export function BracketPageClient({ tournamentId, initialBracket }: Props) {
  const qc = useQueryClient();

  useEffect(() => {
    if (initialBracket) {
      qc.setQueryData(tournamentKeys.bracket(tournamentId), {
        data: initialBracket,
        meta: null,
      });
    }
  }, [initialBracket, tournamentId, qc]);

  const { data: bracket, isLoading, isFetching, refetch } = useBracket(tournamentId);
  const display = bracket ?? initialBracket;

  if (isLoading && !initialBracket) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  if (!display) {
    return (
      <div className="flex flex-col items-center rounded-xl border border-white/10 bg-slate-900 py-24 text-center">
        <Trophy className="mb-4 h-16 w-16 text-slate-700" />
        <p className="font-semibold text-white">ブラケットはまだ生成されていません</p>
        <p className="mt-1 text-sm text-slate-400">大会開始後に主催者がブラケットを生成します</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs text-slate-500">
          {isFetching ? "更新中..." : "30秒ごとに自動更新"}
        </p>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:text-white transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
          手動更新
        </button>
      </div>
      <BracketView bracket={display} />
    </div>
  );
}

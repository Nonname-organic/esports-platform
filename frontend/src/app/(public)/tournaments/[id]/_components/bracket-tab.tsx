"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Trophy, RefreshCw } from "lucide-react";
import { useBracket, tournamentKeys } from "@/features/tournaments/hooks/use-tournaments";
import { BracketView } from "@/features/tournaments/components/bracket/bracket-view";
import type { BracketResponse } from "@/types/tournament";

interface BracketTabProps {
  tournamentId: string;
  initialBracket?: BracketResponse;
}

export function BracketTab({ tournamentId, initialBracket }: BracketTabProps) {
  const qc = useQueryClient();

  useEffect(() => {
    if (initialBracket) {
      qc.setQueryData(tournamentKeys.bracket(tournamentId), { data: initialBracket, meta: null });
    }
  }, [initialBracket, tournamentId, qc]);

  const { data: bracket, isLoading, isError, refetch, isFetching } = useBracket(tournamentId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 pt-6">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  if (isError || !bracket) {
    return (
      <div className="flex flex-col items-center py-24 text-center pt-6">
        <Trophy className="mb-4 h-12 w-12 text-slate-700" />
        <p className="font-semibold text-white">ブラケットがまだありません</p>
        <p className="mt-1 text-sm text-slate-400">
          大会が開始されるとブラケットが表示されます
        </p>
      </div>
    );
  }

  return (
    <div className="pt-6">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-slate-500">30秒ごとに自動更新</p>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:text-white transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
          更新
        </button>
      </div>
      <div className="overflow-x-auto rounded-xl border border-white/10 bg-slate-900 p-4">
        <BracketView bracket={bracket} />
      </div>
    </div>
  );
}

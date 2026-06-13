"use client";

import { useState, useEffect, useCallback } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { Search, SlidersHorizontal, Trophy, X, ChevronLeft, ChevronRight, AlertCircle } from "lucide-react";
import { TournamentCard } from "@/features/tournaments/components/tournament-card";
import { TournamentGridSkeleton } from "@/features/tournaments/components/tournament-skeleton";
import { useTournamentList } from "@/features/tournaments/hooks/use-tournaments";
import { cn } from "@/lib/utils";
import type { GameType, TournamentStatus } from "@/types/tournament";
import type { TournamentSortOrder } from "@/features/tournaments/api/tournament-api";

const GAMES: Array<{ value: GameType | "ALL"; label: string }> = [
  { value: "ALL", label: "すべて" },
  { value: "VALORANT", label: "VALORANT" },
  { value: "LOL", label: "LoL" },
  { value: "APEX", label: "APEX" },
  { value: "CS2", label: "CS2" },
  { value: "OVERWATCH", label: "OW2" },
];

const STATUSES: Array<{ value: TournamentStatus | "ALL"; label: string }> = [
  { value: "ALL", label: "すべてのステータス" },
  { value: "registration_open", label: "参加受付中" },
  { value: "ongoing", label: "開催中" },
  { value: "completed", label: "終了済み" },
  { value: "cancelled", label: "中止" },
];

const SORTS: Array<{ value: TournamentSortOrder; label: string }> = [
  { value: "start_at_asc", label: "開催日が近い順" },
  { value: "start_at_desc", label: "開催日が遠い順" },
  { value: "created_at_desc", label: "作成日が新しい順" },
];

function ymNow(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}
function shiftMonth(ym: string, delta: number): string {
  const [y, m] = ym.split("-").map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}
function ymLabel(ym: string): string {
  const [y, m] = ym.split("-");
  return `${y}年${Number(m)}月`;
}

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export function TournamentsClient() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [searchInput, setSearchInput] = useState(searchParams.get("q") ?? "");
  const [game, setGame] = useState<GameType | "ALL">((searchParams.get("game") as GameType) ?? "ALL");
  const [status, setStatus] = useState<TournamentStatus | "ALL">((searchParams.get("status") as TournamentStatus) ?? "ALL");
  const [sort, setSort] = useState<TournamentSortOrder>((searchParams.get("sort") as TournamentSortOrder) ?? "start_at_asc");
  // デフォルトは「当月」。"ALL" で全期間。
  const [month, setMonth] = useState<string>(() => {
    const mp = searchParams.get("month");
    return mp === "all" ? "ALL" : (mp ?? ymNow());
  });

  const [cursors, setCursors] = useState<(string | undefined)[]>([undefined]);
  const [pageIdx, setPageIdx] = useState(0);

  const debouncedSearch = useDebounce(searchInput, 400);

  // フィルター変更時はページを先頭に戻す
  const resetPage = useCallback(() => {
    setCursors([undefined]);
    setPageIdx(0);
  }, []);

  useEffect(() => { resetPage(); }, [debouncedSearch, game, status, sort, month, resetPage]);

  // URL同期
  useEffect(() => {
    const params = new URLSearchParams();
    if (debouncedSearch) params.set("q", debouncedSearch);
    if (game !== "ALL") params.set("game", game);
    if (status !== "ALL") params.set("status", status);
    if (sort !== "start_at_asc") params.set("sort", sort);
    if (month === "ALL") params.set("month", "all");
    else if (month !== ymNow()) params.set("month", month);
    const qs = params.toString();
    router.replace(`${pathname}${qs ? `?${qs}` : ""}`, { scroll: false });
  }, [debouncedSearch, game, status, sort, month, pathname, router]);

  const params = {
    q: debouncedSearch || undefined,
    game: game !== "ALL" ? game : undefined,
    status: status !== "ALL" ? status : undefined,
    sort,
    month: month !== "ALL" ? month : undefined,
    cursor: cursors[pageIdx],
  };

  const { data, isLoading, isFetching, isError } = useTournamentList(params);

  const handleNext = () => {
    if (data?.meta.has_next && data.meta.cursor) {
      const next = [...cursors.slice(0, pageIdx + 1), data.meta.cursor];
      setCursors(next);
      setPageIdx(pageIdx + 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handlePrev = () => {
    if (pageIdx > 0) {
      setPageIdx(pageIdx - 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handleReset = () => {
    setSearchInput("");
    setGame("ALL");
    setStatus("ALL");
    setSort("start_at_asc");
    setMonth(ymNow());
  };

  const hasFilters = searchInput || game !== "ALL" || status !== "ALL";
  const tournaments = data?.data ?? [];
  const isFirstPage = pageIdx === 0;
  const hasNext = data?.meta.has_next ?? false;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* ページヘッダー */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-white">大会一覧</h1>
          <p className="mt-1 text-slate-400">
            {month === "ALL" ? "すべての期間の大会" : `${ymLabel(month)}に受付・開催する大会`}
          </p>
        </div>

        {/* 月ナビゲーション（デフォルト＝当月） */}
        <div className="flex items-center gap-1.5">
          {month === "ALL" ? (
            <button
              onClick={() => setMonth(ymNow())}
              className="rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-300 hover:bg-white/5 hover:text-white transition-colors"
            >
              今月を表示
            </button>
          ) : (
            <>
              <button
                onClick={() => setMonth(shiftMonth(month, -1))}
                className="rounded-lg border border-white/10 p-2 text-slate-400 hover:bg-white/5 hover:text-white transition-colors"
                aria-label="前の月"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="min-w-[6.5rem] text-center text-sm font-bold text-white">{ymLabel(month)}</span>
              <button
                onClick={() => setMonth(shiftMonth(month, 1))}
                className="rounded-lg border border-white/10 p-2 text-slate-400 hover:bg-white/5 hover:text-white transition-colors"
                aria-label="次の月"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
              <button
                onClick={() => setMonth("ALL")}
                className="ml-1 rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-400 hover:bg-white/5 hover:text-white transition-colors"
              >
                すべて
              </button>
            </>
          )}
        </div>
      </div>

      {/* フィルターバー */}
      <div className="mb-6 space-y-3">
        {/* 検索 + ソート */}
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              type="search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="大会名で検索..."
              className="w-full rounded-lg border border-white/10 bg-white/5 py-2.5 pl-9 pr-4 text-sm text-white placeholder-slate-600 outline-none transition-colors focus:border-brand-500"
            />
            {searchInput && (
              <button
                onClick={() => setSearchInput("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
                aria-label="検索をクリア"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <SlidersHorizontal className="h-4 w-4 flex-shrink-0 text-slate-500" />
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as TournamentSortOrder)}
              className="rounded-lg border border-white/10 bg-slate-800 py-2.5 pl-3 pr-8 text-sm text-white outline-none focus:border-brand-500"
            >
              {SORTS.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* ゲームタブ */}
        <div className="flex flex-wrap items-center gap-1 rounded-xl border border-white/10 bg-white/5 p-1">
          {GAMES.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setGame(value)}
              className={cn(
                "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                game === value
                  ? "bg-brand-500 text-white shadow-sm"
                  : "text-slate-400 hover:text-white",
              )}
            >
              {label}
            </button>
          ))}

          <div className="mx-1 h-4 w-px bg-white/10" />

          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as TournamentStatus | "ALL")}
            className="rounded-lg border border-transparent bg-transparent py-1.5 pl-2 pr-6 text-sm text-slate-400 outline-none hover:text-white focus:text-white"
          >
            {STATUSES.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>

          {hasFilters && (
            <button
              onClick={handleReset}
              className="ml-auto flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs text-slate-500 hover:text-white transition-colors"
            >
              <X className="h-3.5 w-3.5" />
              リセット
            </button>
          )}
        </div>
      </div>

      {/* 結果件数 */}
      {!isLoading && data && (
        <p className="mb-4 text-sm text-slate-500">
          {data.meta.total != null ? `${data.meta.total}件` : `${tournaments.length}件`}
          {isFetching && <span className="ml-2 text-brand-400">更新中...</span>}
        </p>
      )}

      {/* コンテンツ */}
      {isLoading ? (
        <TournamentGridSkeleton count={12} />
      ) : isError ? (
        <ErrorState onRetry={resetPage} />
      ) : tournaments.length === 0 ? (
        <EmptyState hasFilters={!!hasFilters} onReset={handleReset} />
      ) : (
        <div
          className={cn(
            "grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3",
            isFetching && "opacity-60 transition-opacity",
          )}
        >
          {tournaments.map((t) => (
            <TournamentCard key={t.id} tournament={t} />
          ))}
        </div>
      )}

      {/* ページネーション */}
      {(hasNext || !isFirstPage) && !isLoading && !isError && (
        <div className="mt-8 flex items-center justify-center gap-4">
          <button
            onClick={handlePrev}
            disabled={isFirstPage || isFetching}
            className={cn(
              "flex items-center gap-2 rounded-lg border border-white/10 px-4 py-2 text-sm font-medium transition-colors",
              isFirstPage || isFetching
                ? "cursor-not-allowed text-slate-600"
                : "text-slate-300 hover:border-white/20 hover:text-white",
            )}
          >
            <ChevronLeft className="h-4 w-4" />
            前のページ
          </button>

          <span className="text-sm text-slate-500">
            {pageIdx + 1} ページ目
          </span>

          <button
            onClick={handleNext}
            disabled={!hasNext || isFetching}
            className={cn(
              "flex items-center gap-2 rounded-lg border border-white/10 px-4 py-2 text-sm font-medium transition-colors",
              !hasNext || isFetching
                ? "cursor-not-allowed text-slate-600"
                : "text-slate-300 hover:border-white/20 hover:text-white",
            )}
          >
            次のページ
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}

function EmptyState({ hasFilters, onReset }: { hasFilters: boolean; onReset: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-white/5">
        <Trophy className="h-10 w-10 text-slate-600" />
      </div>
      <h3 className="text-lg font-semibold text-white">
        {hasFilters ? "条件に合う大会がありません" : "大会がまだありません"}
      </h3>
      <p className="mt-2 max-w-sm text-sm text-slate-400">
        {hasFilters
          ? "フィルターを変えて再度お試しください。"
          : "最初の大会が開催されるまでお待ちください。"}
      </p>
      {hasFilters && (
        <button
          onClick={onReset}
          className="mt-4 rounded-lg bg-brand-500/10 px-4 py-2 text-sm font-medium text-brand-400 hover:bg-brand-500/20 transition-colors"
        >
          フィルターをリセット
        </button>
      )}
    </div>
  );
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-red-500/10">
        <AlertCircle className="h-10 w-10 text-red-400" />
      </div>
      <h3 className="text-lg font-semibold text-white">読み込みに失敗しました</h3>
      <p className="mt-2 text-sm text-slate-400">ネットワークエラーが発生しました。</p>
      <button
        onClick={onRetry}
        className="mt-4 rounded-lg bg-red-500/10 px-4 py-2 text-sm font-medium text-red-400 hover:bg-red-500/20 transition-colors"
      >
        再試行
      </button>
    </div>
  );
}

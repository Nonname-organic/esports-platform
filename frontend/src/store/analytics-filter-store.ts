"use client";

import { create } from "zustand";
import type { GameType } from "@/types/tournament";
import type { AnalyticsPeriod } from "@/types/analytics";

const today = new Date().toISOString().slice(0, 10);
const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
  .toISOString()
  .slice(0, 10);

interface AnalyticsFilterState {
  game: GameType;
  tournamentId: string;
  teamId: string;
  dateFrom: string;
  dateTo: string;
  period: AnalyticsPeriod;

  setGame: (game: GameType) => void;
  setTournamentId: (id: string) => void;
  setTeamId: (id: string) => void;
  setDateFrom: (date: string) => void;
  setDateTo: (date: string) => void;
  setPeriod: (period: AnalyticsPeriod) => void;
  reset: () => void;
}

const DEFAULT: Pick<
  AnalyticsFilterState,
  "game" | "tournamentId" | "teamId" | "dateFrom" | "dateTo" | "period"
> = {
  game: "VALORANT",
  tournamentId: "",
  teamId: "",
  dateFrom: thirtyDaysAgo,
  dateTo: today,
  period: "30d",
};

export const useAnalyticsFilterStore = create<AnalyticsFilterState>((set) => ({
  ...DEFAULT,
  setGame: (game) => set({ game }),
  setTournamentId: (tournamentId) => set({ tournamentId }),
  setTeamId: (teamId) => set({ teamId }),
  setDateFrom: (dateFrom) => set({ dateFrom }),
  setDateTo: (dateTo) => set({ dateTo }),
  setPeriod: (period) => set({ period }),
  reset: () => set(DEFAULT),
}));

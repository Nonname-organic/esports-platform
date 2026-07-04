"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export interface ViewedItem {
  type: string;
  id: string;
  label: string;
  url: string;
}

interface SearchState {
  recentQueries: string[];        // 最大8件
  recentlyViewed: ViewedItem[];   // 最大8件
  addQuery: (q: string) => void;
  addViewed: (item: ViewedItem) => void;
  clearQueries: () => void;
}

const MAX = 8;

export const useSearchStore = create<SearchState>()(
  persist(
    (set) => ({
      recentQueries: [],
      recentlyViewed: [],
      addQuery: (q) =>
        set((s) => {
          const query = q.trim();
          if (query.length < 2) return s;
          const next = [query, ...s.recentQueries.filter((x) => x !== query)].slice(0, MAX);
          return { recentQueries: next };
        }),
      addViewed: (item) =>
        set((s) => {
          const next = [item, ...s.recentlyViewed.filter((x) => !(x.type === item.type && x.id === item.id))].slice(0, MAX);
          return { recentlyViewed: next };
        }),
      clearQueries: () => set({ recentQueries: [] }),
    }),
    {
      name: "esports-search",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ recentQueries: s.recentQueries, recentlyViewed: s.recentlyViewed }),
    },
  ),
);

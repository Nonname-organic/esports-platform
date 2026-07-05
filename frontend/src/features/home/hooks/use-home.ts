"use client";

import { useQuery } from "@tanstack/react-query";
import { homeApi } from "../api/home-api";

/** ホーム全体を1リクエストで取得（60秒更新・非表示時停止）。Widgetはこのsliceを参照。 */
export function useHome(game?: string) {
  return useQuery({
    queryKey: ["home", game ?? "all"],
    queryFn: () => homeApi.home(game),
    select: (res) => res.data,
    refetchInterval: 60000,
    refetchIntervalInBackground: false,
    staleTime: 30000,
  });
}

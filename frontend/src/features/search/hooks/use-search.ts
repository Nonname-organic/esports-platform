"use client";

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { searchApi } from "../api/search-api";

export function useGlobalSearch(q: string) {
  const query = q.trim();
  return useQuery({
    queryKey: ["search", query],
    queryFn: () => searchApi.search(query),
    select: (res) => res.data,
    enabled: query.length >= 2,
    staleTime: 30 * 1000,
    placeholderData: keepPreviousData,
  });
}

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { discordApi } from "../api/discord-api";

export const discordKeys = {
  all: ["discord"] as const,
  link: () => [...discordKeys.all, "link"] as const,
};

export function useDiscordLink() {
  return useQuery({
    queryKey: discordKeys.link(),
    queryFn: () => discordApi.getLink(),
    select: (res) => res.data,
    staleTime: 30 * 1000,
  });
}

export function useIssueLinkCode() {
  return useMutation({
    mutationFn: () => discordApi.issueCode(),
  });
}

export function useUnlinkRefresh() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: discordKeys.all });
}

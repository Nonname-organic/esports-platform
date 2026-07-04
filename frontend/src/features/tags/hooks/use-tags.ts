"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tagApi, type TagEntityType } from "../api/tag-api";

export function useTagCatalog(q?: string) {
  return useQuery({
    queryKey: ["tags", "catalog", q ?? ""],
    queryFn: () => tagApi.catalog({ q }),
    select: (res) => res.data,
    staleTime: 10 * 60 * 1000,
  });
}

export function useEntityTags(entityType: TagEntityType, entityId: string) {
  return useQuery({
    queryKey: ["tags", entityType, entityId],
    queryFn: () => tagApi.forEntity(entityType, entityId),
    select: (res) => res.data,
    enabled: !!entityId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useSetEntityTags(entityType: TagEntityType, entityId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (tags: string[]) => tagApi.setForEntity(entityType, entityId, tags),
    onSuccess: (res) => {
      qc.setQueryData(["tags", entityType, entityId], res);
    },
  });
}

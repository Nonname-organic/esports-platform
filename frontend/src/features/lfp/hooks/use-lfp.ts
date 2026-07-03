"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { lfpApi, type LFPSearchParams, type LFPCreateInput } from "../api/lfp-api";

export const lfpKeys = {
  all: ["lfp"] as const,
  list: (params?: object) => [...lfpKeys.all, "list", params] as const,
  mine: () => [...lfpKeys.all, "mine"] as const,
  detail: (id: string) => [...lfpKeys.all, "detail", id] as const,
};

export function useLFPList(params?: LFPSearchParams) {
  return useQuery({
    queryKey: lfpKeys.list(params),
    queryFn: () => lfpApi.list(params),
    select: (res) => res.data,
    staleTime: 60 * 1000,
  });
}

export function useMyLFP() {
  return useQuery({
    queryKey: lfpKeys.mine(),
    queryFn: () => lfpApi.mine(),
    select: (res) => res.data,
    staleTime: 60 * 1000,
  });
}

export function useLFP(id: string) {
  return useQuery({
    queryKey: lfpKeys.detail(id),
    queryFn: () => lfpApi.get(id),
    select: (res) => res.data,
    enabled: !!id,
    staleTime: 60 * 1000,
  });
}

export function useCreateLFP() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: LFPCreateInput) => lfpApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: lfpKeys.all }),
  });
}

export function useUpdateLFP(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<LFPCreateInput>) => lfpApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: lfpKeys.all }),
  });
}

export function useDeleteLFP() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => lfpApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: lfpKeys.all }),
  });
}

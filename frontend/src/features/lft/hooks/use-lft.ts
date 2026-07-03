"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { lftApi, type LFTSearchParams, type LFTCreateInput } from "../api/lft-api";

export const lftKeys = {
  all: ["lft"] as const,
  list: (params?: object) => [...lftKeys.all, "list", params] as const,
  me: () => [...lftKeys.all, "me"] as const,
  detail: (id: string) => [...lftKeys.all, "detail", id] as const,
};

export function useLFTList(params?: LFTSearchParams) {
  return useQuery({
    queryKey: lftKeys.list(params),
    queryFn: () => lftApi.list(params),
    select: (res) => res.data,
    staleTime: 60 * 1000,
  });
}

export function useMyLFT() {
  return useQuery({
    queryKey: lftKeys.me(),
    queryFn: () => lftApi.getMe(),
    select: (res) => res.data,
    staleTime: 60 * 1000,
  });
}

export function useLFT(id: string) {
  return useQuery({
    queryKey: lftKeys.detail(id),
    queryFn: () => lftApi.get(id),
    select: (res) => res.data,
    enabled: !!id,
    staleTime: 60 * 1000,
  });
}

export function useCreateLFT() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: LFTCreateInput) => lftApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: lftKeys.all }),
  });
}

export function useUpdateMyLFT() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<LFTCreateInput>) => lftApi.updateMe(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: lftKeys.all }),
  });
}

export function useDeleteMyLFT() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => lftApi.deleteMe(),
    onSuccess: () => qc.invalidateQueries({ queryKey: lftKeys.all }),
  });
}

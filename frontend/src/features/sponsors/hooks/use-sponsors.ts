"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { sponsorApi, type SponsorInput } from "../api/sponsor-api";

export function useSponsors(teamId: string) {
  return useQuery({
    queryKey: ["sponsors", teamId],
    queryFn: () => sponsorApi.list(teamId),
    select: (res) => res.data,
    enabled: !!teamId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateSponsor(teamId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SponsorInput) => sponsorApi.create(teamId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sponsors", teamId] }),
  });
}

export function useUpdateSponsor(teamId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<SponsorInput> }) => sponsorApi.update(teamId, id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sponsors", teamId] }),
  });
}

export function useDeleteSponsor(teamId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => sponsorApi.remove(teamId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sponsors", teamId] }),
  });
}

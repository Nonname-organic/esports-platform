"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { rulesApi, type RulesDoc } from "../api/rules-api";

export function useRules(tournamentId: string) {
  return useQuery({
    queryKey: ["tournament-rules", tournamentId],
    queryFn: () => rulesApi.get(tournamentId),
    select: (res) => res.data,
    enabled: !!tournamentId,
    staleTime: 60 * 1000,
  });
}

export function useRulesTemplates(enabled = true) {
  return useQuery({
    queryKey: ["tournament-rules-templates"],
    queryFn: () => rulesApi.templates(),
    select: (res) => res.data,
    enabled,
    staleTime: 30 * 60 * 1000,
  });
}

export function useUpdateRules(tournamentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (doc: RulesDoc) => rulesApi.update(tournamentId, doc),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tournament-rules", tournamentId] }),
  });
}

export function useApplyRulesTemplate(tournamentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (templateId: string) => rulesApi.applyTemplate(tournamentId, templateId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tournament-rules", tournamentId] }),
  });
}

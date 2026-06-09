"use client";

import { useQuery } from "@tanstack/react-query";
import { careerApi } from "../api/career-api";

export const careerKeys = {
  playerCareer: (id: string) => ["career", "player", id] as const,
  playerAchievements: (id: string) => ["career", "player-achievements", id] as const,
  playerRatingHistory: (id: string, game: string) => ["career", "player-ratings", id, game] as const,
  teamCareer: (id: string) => ["career", "team", id] as const,
  teamAchievements: (id: string) => ["career", "team-achievements", id] as const,
  teamRivals: (id: string) => ["career", "team-rivals", id] as const,
};

export function usePlayerCareer(id: string) {
  return useQuery({
    queryKey: careerKeys.playerCareer(id),
    queryFn: () => careerApi.playerCareer(id),
    select: (res) => res.data,
    staleTime: 5 * 60 * 1000,
    enabled: !!id,
  });
}

export function usePlayerAchievements(id: string) {
  return useQuery({
    queryKey: careerKeys.playerAchievements(id),
    queryFn: () => careerApi.playerAchievements(id),
    select: (res) => res.data,
    staleTime: 5 * 60 * 1000,
    enabled: !!id,
  });
}

export function usePlayerRatingHistory(id: string, game: string) {
  return useQuery({
    queryKey: careerKeys.playerRatingHistory(id, game),
    queryFn: () => careerApi.playerRatingHistory(id, game),
    select: (res) => res.data,
    staleTime: 5 * 60 * 1000,
    enabled: !!id,
  });
}

export function useTeamCareer(id: string) {
  return useQuery({
    queryKey: careerKeys.teamCareer(id),
    queryFn: () => careerApi.teamCareer(id),
    select: (res) => res.data,
    staleTime: 5 * 60 * 1000,
    enabled: !!id,
  });
}

export function useTeamAchievements(id: string) {
  return useQuery({
    queryKey: careerKeys.teamAchievements(id),
    queryFn: () => careerApi.teamAchievements(id),
    select: (res) => res.data,
    staleTime: 5 * 60 * 1000,
    enabled: !!id,
  });
}

export function useTeamRivals(id: string) {
  return useQuery({
    queryKey: careerKeys.teamRivals(id),
    queryFn: () => careerApi.teamRivals(id),
    select: (res) => res.data,
    staleTime: 5 * 60 * 1000,
    enabled: !!id,
  });
}

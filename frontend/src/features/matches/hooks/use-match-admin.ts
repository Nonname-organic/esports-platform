"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { matchApi } from "../api/match-api";
import { matchKeys } from "./use-matches";
import type { MatchDetail, WSMessage } from "@/types/match";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

export type WsStatus = "connecting" | "connected" | "disconnected";

// ── マッチデータ + リアルタイム更新 ──────────────────────────────────────────
export function useMatchAdmin(matchId: string, initialData?: MatchDetail) {
  const qc = useQueryClient();

  const { data: match, isLoading } = useQuery({
    queryKey: matchKeys.detail(matchId),
    queryFn: () => matchApi.get(matchId),
    select: (res) => res.data,
    staleTime: 30 * 1000,
    initialData: initialData
      ? { data: initialData, meta: null }
      : undefined,
  });

  // ── WebSocket (接続状態を useState で追跡) ──────────────────────────────
  const [wsStatus, setWsStatus] = useState<WsStatus>("connecting");
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    setWsStatus("connecting");

    const ws = new WebSocket(`${WS_BASE}/ws/matches/${matchId}`);
    wsRef.current = ws;

    ws.onopen = () => setWsStatus("connected");

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string) as WSMessage;

        switch (msg.type) {
          case "score_update":
            qc.setQueryData(
              matchKeys.detail(matchId),
              (old: { data: MatchDetail } | undefined) => {
                if (!old) return old;
                return {
                  ...old,
                  data: {
                    ...old.data,
                    games: old.data.games.map((g) =>
                      g.game_number === msg.game_number
                        ? { ...g, team1_score: msg.team1_score, team2_score: msg.team2_score }
                        : g,
                    ),
                  },
                };
              },
            );
            break;
          case "match_complete":
            qc.invalidateQueries({ queryKey: matchKeys.detail(matchId) });
            break;
          case "ping":
            ws.send(JSON.stringify({ type: "pong" }));
            break;
        }
      } catch {
        // JSON解析エラーは無視
      }
    };

    ws.onerror = () => setWsStatus("disconnected");

    ws.onclose = () => {
      setWsStatus("disconnected");
      retryRef.current = setTimeout(connect, 3000);
    };
  }, [matchId, qc]);

  useEffect(() => {
    connect();
    return () => {
      retryRef.current && clearTimeout(retryRef.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  // ── ミューテーション ──────────────────────────────────────────────────────
  const startMatch = useMutation({
    mutationFn: () => matchApi.start(matchId),
    onSuccess: () => qc.invalidateQueries({ queryKey: matchKeys.detail(matchId) }),
  });

  const updateScore = useMutation({
    mutationFn: (data: {
      gameNumber: number;
      team1_score: number;
      team2_score: number;
      duration_seconds?: number;
    }) =>
      matchApi.updateScore(matchId, data.gameNumber, {
        team1_score: data.team1_score,
        team2_score: data.team2_score,
        duration_seconds: data.duration_seconds,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: matchKeys.detail(matchId) }),
  });

  const registerResult = useMutation({
    mutationFn: (data: { winner_id: string; was_forfeit?: boolean }) =>
      matchApi.registerResult(matchId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: matchKeys.detail(matchId) }),
  });

  const registerBanPick = useMutation({
    mutationFn: (data: {
      team_id: string;
      action: "ban" | "pick";
      map_id: string;
      order: number;
    }) => matchApi.registerBanPick(matchId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: matchKeys.detail(matchId) }),
  });

  return {
    match,
    isLoading,
    wsStatus,
    startMatch,
    updateScore,
    registerResult,
    registerBanPick,
  };
}

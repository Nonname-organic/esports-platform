"use client";

import { useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { WSMessage } from "@/types/match";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

interface UseMatchWebSocketOptions {
  matchId: string;
  onScoreUpdate?: (data: Extract<WSMessage, { type: "score_update" }>) => void;
  onMatchComplete?: (data: Extract<WSMessage, { type: "match_complete" }>) => void;
}

export function useMatchWebSocket({
  matchId,
  onScoreUpdate,
  onMatchComplete,
}: UseMatchWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const qc = useQueryClient();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_BASE}/ws/matches/${matchId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.info(`[WS] Connected to match ${matchId}`);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string) as WSMessage;
        switch (msg.type) {
          case "score_update":
            onScoreUpdate?.(msg);
            // TanStack Query のキャッシュを楽観的更新
            qc.setQueryData(["matches", "detail", matchId], (old: { data: { games: { game_number: number; team1_score: number; team2_score: number }[] } } | undefined) => {
              if (!old) return old;
              return {
                ...old,
                data: {
                  ...old.data,
                  games: old.data.games.map((g: { game_number: number; team1_score: number; team2_score: number }) =>
                    g.game_number === msg.game_number
                      ? { ...g, team1_score: msg.team1_score, team2_score: msg.team2_score }
                      : g,
                  ),
                },
              };
            });
            break;
          case "match_complete":
            onMatchComplete?.(msg);
            qc.invalidateQueries({ queryKey: ["matches", "detail", matchId] });
            break;
          case "ping":
            ws.send(JSON.stringify({ type: "pong" }));
            break;
        }
      } catch {
        // JSON解析エラーは無視
      }
    };

    ws.onerror = () => {
      console.warn(`[WS] Error on match ${matchId}`);
    };

    ws.onclose = () => {
      console.info(`[WS] Disconnected from match ${matchId}, reconnecting...`);
      // 3秒後に再接続
      reconnectTimerRef.current = setTimeout(connect, 3000);
    };
  }, [matchId, onScoreUpdate, onMatchComplete, qc]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  return {
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
  };
}

/** ブラケット更新用WebSocket */
export function useBracketWebSocket(tournamentId: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const qc = useQueryClient();

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/brackets/${tournamentId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string) as WSMessage;
        if (msg.type === "bracket_update") {
          qc.invalidateQueries({ queryKey: ["tournaments", "bracket", tournamentId] });
        }
      } catch {}
    };

    ws.onclose = () => {
      setTimeout(() => {
        // 5秒後に再接続（ブラケットは試合ほど緊急でない）
      }, 5000);
    };

    return () => ws.close();
  }, [tournamentId, qc]);
}

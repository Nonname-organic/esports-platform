"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { liveApi, type LiveStats, type PlatformTotals, type StatsOverview } from "../api/live-api";

/**
 * Live 更新のデータ源を抽象化する Transport。
 * 現在は Polling 実装。将来 `/ws` 基盤に載せた WebSocket 実装へ差し替え可能
 * （consumer 側= Provider/コンポーネントは変更不要）。
 */
export interface LiveTransport {
  /** onData を購読開始し、購読解除関数を返す。 */
  start(onData: (data: StatsOverview | null) => void): () => void;
}

type LiveSource = "idle" | "live" | "mock";

interface LiveContextValue {
  live: LiveStats | null;
  totals: PlatformTotals | null;
  lastUpdated: number | null; // epoch ms（最終更新表示用）
  source: LiveSource;
}

const LiveContext = createContext<LiveContextValue | null>(null);

// ── Mock フォールバック（Backendが空/不通のとき賑わいを補完） ──────────────
function jitter(v: number, amp: number): number {
  return Math.max(0, Math.round(v + (Math.random() - 0.5) * amp));
}
function mockLive(prev: LiveStats | null): LiveStats {
  const base = prev ?? { ongoing_tournaments: 44, registration_open_tournaments: 63, ongoing_matches: 118, online_participants: 3800, updated_at: "" };
  return {
    ongoing_tournaments: jitter(base.ongoing_tournaments || 44, 4),
    registration_open_tournaments: jitter(base.registration_open_tournaments || 63, 5),
    ongoing_matches: jitter(base.ongoing_matches || 118, 12),
    online_participants: jitter(base.online_participants || 3800, 140),
    updated_at: new Date().toISOString(),
  };
}
function mockTotals(): PlatformTotals {
  return { tournaments: 1248, teams: 512, players: 3200, matches: 8900 };
}
function isDead(o: StatsOverview): boolean {
  const l = o.live;
  return (l.ongoing_tournaments + l.ongoing_matches + l.online_participants) <= 0;
}

// ── Polling Transport（Visibility API 対応: 非表示中は停止） ─────────────────
export function createPollingTransport(intervalMs = 60000): LiveTransport {
  return {
    start(onData) {
      if (typeof window === "undefined") return () => {};
      let timer: ReturnType<typeof setInterval> | null = null;

      const tick = async () => {
        try {
          const res = await liveApi.overview();
          onData(res.data);
        } catch {
          onData(null); // 不通 → Provider が mock で補完
        }
      };
      const startTimer = () => { if (!timer) timer = setInterval(tick, intervalMs); };
      const stopTimer = () => { if (timer) { clearInterval(timer); timer = null; } };

      const onVisibility = () => {
        if (document.visibilityState === "visible") {
          tick();          // 復帰時は即時更新
          startTimer();
        } else {
          stopTimer();     // バックグラウンドでは完全停止（ネットワーク負荷ゼロ）
        }
      };

      if (document.visibilityState === "visible") {
        tick();
        startTimer();
      }
      document.addEventListener("visibilitychange", onVisibility);

      return () => {
        stopTimer();
        document.removeEventListener("visibilitychange", onVisibility);
      };
    },
  };
}

export function LiveProvider({
  children,
  transport,
  intervalMs = 60000,
}: {
  children: React.ReactNode;
  transport?: LiveTransport;
  intervalMs?: number;
}) {
  const [live, setLive] = useState<LiveStats | null>(null);
  const [totals, setTotals] = useState<PlatformTotals | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  const [source, setSource] = useState<LiveSource>("idle");
  const liveRef = useRef<LiveStats | null>(null);

  const handle = useCallback((data: StatsOverview | null) => {
    if (data && !isDead(data)) {
      liveRef.current = data.live;
      setLive(data.live);
      setTotals(data.totals);
      setSource("live");
    } else {
      // 空 or 不通 → mock で賑わいを維持（数値の出所は問わない設計）
      const m = mockLive(liveRef.current);
      liveRef.current = m;
      setLive(m);
      setTotals((prev) => data?.totals ?? prev ?? mockTotals());
      setSource("mock");
    }
    setLastUpdated(Date.now());
  }, []);

  useEffect(() => {
    const t = transport ?? createPollingTransport(intervalMs);
    const stop = t.start(handle);
    return stop;
  }, [transport, intervalMs, handle]);

  return (
    <LiveContext.Provider value={{ live, totals, lastUpdated, source }}>
      {children}
    </LiveContext.Provider>
  );
}

export function useLive(): LiveContextValue {
  const ctx = useContext(LiveContext);
  if (!ctx) throw new Error("useLive は <LiveProvider> の内側で使用してください");
  return ctx;
}

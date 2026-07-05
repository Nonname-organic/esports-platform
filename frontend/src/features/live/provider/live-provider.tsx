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
// ── モック方針（仕様: 「以下のみモック許可 = 閲覧人数 / 参加人数」） ──────────
// 大会・試合・優勝・MVP・賞金などの実体数は絶対にモックしない（実データ or 0）。
// online_participants（閲覧人数）と entries_today/recent（参加人数）だけ、
// 値が 0/未取得のとき賑わい下限をモックで補完する。
function mockViewer(prev: number | undefined): number {
  return jitter(prev && prev > 0 ? prev : 3200, 140);
}
function mockToday(prev: number | undefined): number {
  return jitter(prev && prev > 0 ? prev : 90, 6);
}
function mockRecent(prev: number | undefined): number {
  return jitter(prev && prev > 0 ? prev : 5, 3);
}

/** 実 live に対して、閲覧/参加のみ（0/未取得時に）モック下限を重ねる。他は実値のまま。 */
function withLivelyViewers(realLive: LiveStats, prev: LiveStats | null): LiveStats {
  return {
    ...realLive,
    online_participants: realLive.online_participants || mockViewer(prev?.online_participants),
    entries_today: (realLive.entries_today ?? 0) || mockToday(prev?.entries_today),
    entries_recent: (realLive.entries_recent ?? 0) || mockRecent(prev?.entries_recent),
  };
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
    if (data) {
      // 実データ: 大会/試合/累計は実値のまま。閲覧/参加のみ賑わい下限を補完。
      const live = withLivelyViewers(data.live, liveRef.current);
      liveRef.current = live;
      setLive(live);
      setTotals(data.totals);        // 累計は常に実データ（モックしない）
      setSource("live");
    } else {
      // 不通: 累計/大会/試合は前回実値を保持（捏造しない）。閲覧/参加のみ動かす。
      const base = liveRef.current;
      const live: LiveStats = base
        ? {
            ...base,
            online_participants: mockViewer(base.online_participants),
            entries_today: mockToday(base.entries_today),
            entries_recent: mockRecent(base.entries_recent),
          }
        : {
            ongoing_tournaments: 0, registration_open_tournaments: 0, ongoing_matches: 0,
            online_participants: mockViewer(undefined),
            entries_today: mockToday(undefined), entries_recent: mockRecent(undefined),
            updated_at: new Date().toISOString(),
          };
      liveRef.current = live;
      setLive(live);
      // totals は前回の実値を維持（無ければ null のまま → UI は 0 表示）
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

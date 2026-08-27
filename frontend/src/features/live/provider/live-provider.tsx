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

type LiveSource = "idle" | "live";

interface LiveContextValue {
  live: LiveStats | null;
  totals: PlatformTotals | null;
  lastUpdated: number | null; // epoch ms（最終更新表示用）
  source: LiveSource;
}

const LiveContext = createContext<LiveContextValue | null>(null);

// 表示する数値はすべてAPIの実測値。閲覧者数などを「賑わい演出」で
// 生成していた実装があったが、公開サイトで実績を偽ることになるため撤去した。
// 値が取れない場合は前回値を保持し、無ければ 0 を表示する。

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
          onData(null); // 不通 → Provider が前回値を保持
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
      liveRef.current = data.live;
      setLive(data.live);
      setTotals(data.totals);
      setSource("live");
    } else {
      // 不通時は前回取得した実値を保持するだけ。値は作らない
      setSource("idle");
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

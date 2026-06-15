// k6 共有設定 — プロファイル / SLO閾値 / Golden ID / 認証ヘルパー。
//
// 実行例:
//   k6 run -e BASE_URL=https://your-host -e PROFILE=load   k6/tournament.js
//   k6 run -e BASE_URL=https://your-host -e PROFILE=stress  k6/match.js
//   k6 run -e BASE_URL=https://your-host -e PROFILE=spike   k6/notification.js
//
// PROFILE: smoke(1VU) / load(→100) / stress(100→500→1000) / spike(→5000)
import http from "k6/http";
import { check } from "k6";

export const BASE_URL = (__ENV.BASE_URL || "http://localhost:8000").replace(/\/$/, "");
export const API = `${BASE_URL}/api/v1`;

// Golden Dataset 決定論UUID（golden_seed.py の gid と一致）
const gid = (s) => `00000000-0000-0000-0000-${s.padStart(12, "0")}`;
export const IDS = {
  tournamentOngoing: gid("e3"),
  tournamentRegOpen: gid("e2"),
  tournamentDone: gid("e4"),
  player: gid("b1"),
  team: gid("c1"),
  matchScheduled: gid("90"),
  matchOngoing: gid("91"),
  matchCompleted: gid("92"),
};

// Golden 認証情報（負荷時の認証フロー検証用）
export const CREDENTIALS = {
  email: __ENV.GOLDEN_EMAIL || "player@golden.test",
  password: __ENV.GOLDEN_PASSWORD || "Passw0rd!",
};

// ── 段階的負荷プロファイル ──────────────────────────────────────────────────────
const PROFILES = {
  smoke: [{ duration: "30s", target: 1 }],
  load: [
    { duration: "1m", target: 100 },
    { duration: "3m", target: 100 },
    { duration: "1m", target: 0 },
  ],
  stress: [
    { duration: "2m", target: 100 },
    { duration: "3m", target: 500 },
    { duration: "3m", target: 1000 },
    { duration: "2m", target: 0 },
  ],
  spike: [
    { duration: "1m", target: 100 },
    { duration: "30s", target: 5000 },
    { duration: "2m", target: 5000 },
    { duration: "1m", target: 0 },
  ],
};

export function stages() {
  const p = __ENV.PROFILE || "load";
  return PROFILES[p] || PROFILES.load;
}

// ── SLO 閾値（超過=失敗） ───────────────────────────────────────────────────────
// 読み取り p95<500ms / 集計(analytics) p95<800ms / error率<1%
export function thresholds(extra = {}) {
  return Object.assign(
    {
      http_req_failed: ["rate<0.01"],
      http_req_duration: ["p(95)<500", "p(99)<1000"],
    },
    extra,
  );
}

// ── 認証: トークン取得（setup() から呼ぶ） ──────────────────────────────────────
export function login() {
  const res = http.post(
    `${API}/auth/login`,
    JSON.stringify(CREDENTIALS),
    { headers: { "Content-Type": "application/json" }, tags: { name: "auth/login" } },
  );
  check(res, { "login 200": (r) => r.status === 200 });
  try {
    return res.json("access_token");
  } catch (_e) {
    return null;
  }
}

export function authHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

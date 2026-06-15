// 負荷試験: 試合取得 + 集計(Analytics) 経路。
// SLO: 読み取り p95 < 500ms / 集計 p95 < 800ms, error < 1%。
import http from "k6/http";
import { check, group, sleep } from "k6";
import { Trend } from "k6/metrics";
import { API, IDS, stages, thresholds } from "./lib/config.js";

const tMatch = new Trend("d_match_detail", true);
const tMapStats = new Trend("d_analytics_maps", true);
const tPlayerStats = new Trend("d_analytics_player", true);

export const options = {
  scenarios: {
    matches: { executor: "ramping-vus", startVUs: 0, stages: stages() },
  },
  thresholds: thresholds({
    "d_match_detail": ["p(95)<500"],
    "d_analytics_maps": ["p(95)<800"], // 集計は緩めのSLO
    "d_analytics_player": ["p(95)<800"],
  }),
};

export default function () {
  group("match + analytics", () => {
    const m = http.get(`${API}/matches/${IDS.matchCompleted}`, { tags: { name: "matches/detail" } });
    tMatch.add(m.timings.duration);
    check(m, { "match ok": (r) => r.status === 200 || r.status === 404 });

    const maps = http.get(`${API}/analytics/maps/stats?game=VALORANT`, {
      tags: { name: "analytics/maps" },
    });
    tMapStats.add(maps.timings.duration);
    check(maps, { "maps 200": (r) => r.status === 200 });

    const ps = http.get(`${API}/analytics/players/${IDS.player}/stats`, {
      tags: { name: "analytics/player" },
    });
    tPlayerStats.add(ps.timings.duration);
    check(ps, { "player stats ok": (r) => r.status === 200 || r.status === 404 });
  });
  sleep(1);
}

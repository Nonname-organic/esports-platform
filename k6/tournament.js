// 負荷試験: 大会の読み取り経路（一覧 / 詳細 / ブラケット / ランキング）。
// SLO: p95 < 500ms（読み取り）, error < 1%。
import http from "k6/http";
import { check, group, sleep } from "k6";
import { Trend } from "k6/metrics";
import { API, IDS, stages, thresholds } from "./lib/config.js";

const tList = new Trend("d_tournament_list", true);
const tDetail = new Trend("d_tournament_detail", true);
const tBracket = new Trend("d_tournament_bracket", true);
const tRanking = new Trend("d_tournament_ranking", true);

export const options = {
  scenarios: {
    tournaments: { executor: "ramping-vus", startVUs: 0, stages: stages() },
  },
  thresholds: thresholds({
    "d_tournament_list": ["p(95)<500"],
    "d_tournament_detail": ["p(95)<500"],
    "d_tournament_bracket": ["p(95)<500"],
    "d_tournament_ranking": ["p(95)<500"],
    "http_reqs": ["rate>300"], // ≥300 req/s スループット目標
  }),
};

export default function () {
  group("tournament reads", () => {
    const list = http.get(`${API}/tournaments?limit=20`, { tags: { name: "tournaments/list" } });
    tList.add(list.timings.duration);
    check(list, { "list 200": (r) => r.status === 200 });

    const detail = http.get(`${API}/tournaments/${IDS.tournamentOngoing}`, {
      tags: { name: "tournaments/detail" },
    });
    tDetail.add(detail.timings.duration);
    check(detail, { "detail 200": (r) => r.status === 200 });

    const bracket = http.get(`${API}/tournaments/${IDS.tournamentOngoing}/bracket`, {
      tags: { name: "tournaments/bracket" },
    });
    tBracket.add(bracket.timings.duration);
    check(bracket, { "bracket ok": (r) => r.status === 200 || r.status === 404 });

    const rank = http.get(`${API}/rankings/tournaments/${IDS.tournamentDone}?limit=50`, {
      tags: { name: "rankings/tournament" },
    });
    tRanking.add(rank.timings.duration);
    check(rank, { "ranking ok": (r) => r.status === 200 || r.status === 404 });
  });
  sleep(1);
}

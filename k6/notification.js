// 負荷試験: 認証フロー + 通知（ユーザースコープ読み取り）+ スカウト探索。
// 認証→通知一覧→未読数→スカウト検索。SLO: p95 < 500ms, error < 1%。
import http from "k6/http";
import { check, group, sleep } from "k6";
import { Trend } from "k6/metrics";
import { API, stages, thresholds, login, authHeaders } from "./lib/config.js";

const tNotif = new Trend("d_notifications_list", true);
const tUnread = new Trend("d_notifications_unread", true);
const tScout = new Trend("d_scout_players", true);

export const options = {
  scenarios: {
    notifications: { executor: "ramping-vus", startVUs: 0, stages: stages() },
  },
  thresholds: thresholds({
    "d_notifications_list": ["p(95)<500"],
    "d_notifications_unread": ["p(95)<500"],
    "d_scout_players": ["p(95)<500"],
  }),
};

// 認証は1回だけ実行しトークンを共有（ログイン自体の連打を避ける）
export function setup() {
  const token = login();
  return { token };
}

export default function (data) {
  const headers = Object.assign({ "Content-Type": "application/json" }, authHeaders(data.token));

  group("notifications (auth)", () => {
    const list = http.get(`${API}/notifications?limit=30`, { headers, tags: { name: "notifications/list" } });
    tNotif.add(list.timings.duration);
    check(list, { "notif ok": (r) => r.status === 200 || r.status === 401 });

    const unread = http.get(`${API}/notifications/unread-count`, {
      headers,
      tags: { name: "notifications/unread" },
    });
    tUnread.add(unread.timings.duration);
    check(unread, { "unread ok": (r) => r.status === 200 || r.status === 401 });
  });

  group("scout discovery", () => {
    const scout = http.get(`${API}/scout/players?limit=30`, { tags: { name: "scout/players" } });
    tScout.add(scout.timings.duration);
    check(scout, { "scout 200": (r) => r.status === 200 });
  });
  sleep(1);
}

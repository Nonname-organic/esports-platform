/**
 * 公開画面（ログイン不要）のスクリーンショットを本番から撮る。
 *
 *   node docs/manual/capture_public.mjs
 *
 * 操作マニュアルの図として docs/manual/figures/ に保存する。
 * ログインが必要な画面は capture_figures.py（ローカルスタック向け）側で撮る。
 */
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";

const BASE = process.env.AXELIA_BASE ?? "https://app.axelia-esports.jp";
const OUT = "C:/dev/esports-platform/docs/manual/figures";
const CUP = "b56e17ca-c487-4d5f-a4cd-0916d08253e2";
const T2 = "4b60d28b-7ef4-406c-a2b9-d96249315afe";
const MATCH = "f031e879-e144-4fbb-847a-261a20322547";

mkdirSync(OUT, { recursive: true });

// 画面ごとに「この文字が出たら描画完了」を指定する。データ取得が
// 非同期なので networkidle だけでは空の状態を撮ってしまう。
const SHOTS = [
  ["p01_home",               "/",                                  "大会"],
  ["p02_tournaments",        "/tournaments",                       "件"],
  ["p03_tournament_overview","/tournaments/" + CUP,                "大会概要"],
  ["p04_tournament_bracket", "/tournaments/" + CUP + "?tab=bracket", "Round 1"],
  ["p05_tournament_standings","/tournaments/" + CUP + "?tab=standings", "勝率"],
  ["p06_tournament_matches", "/tournaments/" + CUP + "?tab=matches", "準決勝"],
  ["p07_tournament_rules",   "/tournaments/" + CUP + "?tab=rules",  null],
  ["p08_tournament_ongoing", "/tournaments/" + T2 + "?tab=bracket", "Round 1"],
  ["p09_match_overview",     "/matches/" + MATCH,                   "試合情報"],
  ["p10_teams",              "/teams",                              null],
  ["p11_rankings",           "/rankings",                           null],
  ["p12_scout_players",      "/scout/players",                      null],
  ["p13_login",              "/login",                              null],
  ["p14_register",           "/register",                           null],
];

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1280, height: 900 },
  deviceScaleFactor: 2,          // 印刷に載せるので2倍で撮る
  locale: "ja-JP",
  timezoneId: "Asia/Tokyo",
});
const page = await ctx.newPage();
const results = [];

for (const [name, path, waitText] of SHOTS) {
  const url = BASE + path;
  try {
    const res = await page.goto(url, { waitUntil: "networkidle", timeout: 45000 });
    if (waitText) {
      await page.getByText(waitText, { exact: false }).first()
        .waitFor({ timeout: 20000 }).catch(() => {});
    }
    await page.waitForTimeout(1500);
    const file = join(OUT, name + ".png");
    await page.screenshot({ path: file, fullPage: true });
    results.push(`  OK   ${name}  HTTP ${res?.status()}  ${path}`);
  } catch (e) {
    results.push(`  NG   ${name}  ${path}  — ${String(e).split("\n")[0].slice(0, 90)}`);
  }
}

await browser.close();
console.log(results.join("\n"));

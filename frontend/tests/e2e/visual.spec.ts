import { test, expect } from "@playwright/test";

/**
 * Visual Regression — 24画面 × 3端末。
 * 端末(Desktop1440 / Tablet / Mobile)は playwright.config の projects が掛け算する。
 * 認証画面は setup プロジェクトの storageState(captain) を利用。
 *
 * 前提: Golden Dataset 投入済み（決定論UUIDで詳細画面に到達）。
 * ベースライン生成: npx playwright test visual --update-snapshots
 * 差分閾値: maxDiffPixelRatio 0.02（config）。
 */

// Golden 決定論UUID（golden_seed.py の gid と一致）
const gid = (suffix: string) => `00000000-0000-0000-0000-${suffix.padStart(12, "0")}`;
const T_ONGOING = gid("e3");
const T_REGOPEN = gid("e2");
const T_DONE = gid("e4");
const PLAYER = gid("b1");
const TEAM = gid("c1");
const MATCH = gid("92");

interface Screen {
  name: string;
  path: string;
  /** 未ログイン状態で撮影する画面 */
  anon?: boolean;
}

const SCREENS: Screen[] = [
  // ── Public ──
  { name: "landing", path: "/", anon: true },
  { name: "login", path: "/login", anon: true },
  { name: "register", path: "/register", anon: true },
  { name: "public-team", path: `/teams/${TEAM}`, anon: true },
  { name: "public-match", path: `/matches/${MATCH}`, anon: true },
  // ── Auth (captain) ──
  { name: "dashboard", path: "/dashboard" },
  { name: "tournaments-list", path: "/tournaments" },
  { name: "tournament-ongoing", path: `/tournaments/${T_ONGOING}` },
  { name: "tournament-bracket", path: `/tournaments/${T_ONGOING}/bracket` },
  { name: "tournament-regopen", path: `/tournaments/${T_REGOPEN}` },
  { name: "tournament-completed", path: `/tournaments/${T_DONE}` },
  { name: "scout", path: "/scout" },
  { name: "scout-players", path: "/scout/players" },
  { name: "scout-teams", path: "/scout/teams" },
  { name: "scout-recruitment", path: "/scout/recruitment" },
  { name: "analytics", path: "/analytics" },
  { name: "notifications", path: "/notifications" },
  { name: "settings", path: "/settings" },
  { name: "player-profile", path: `/players/${PLAYER}` },
  { name: "team-create", path: "/teams/create" },
  { name: "team-members", path: `/teams/${TEAM}/members` },
  { name: "team-edit", path: `/teams/${TEAM}/edit` },
  { name: "organizer-create", path: "/organizer/tournaments/create" },
  { name: "discord-link", path: "/discord-link" },
];

// アニメーション/キャレットを無効化して安定撮影
const FREEZE_CSS = `
  *, *::before, *::after { animation: none !important; transition: none !important; caret-color: transparent !important; }
  .animate-spin, .animate-pulse { animation: none !important; }
  html { scroll-behavior: auto !important; }
`;

for (const screen of SCREENS) {
  test(`visual ${screen.name}`, async ({ page, browser }, testInfo) => {
    // anon画面は storageState を捨てた新規コンテキストで
    const ctx = screen.anon
      ? await browser.newContext({ storageState: { cookies: [], origins: [] } })
      : null;
    const p = ctx ? await ctx.newPage() : page;

    const resp = await p.goto(screen.path, { waitUntil: "networkidle" });
    // 認可リダイレクト等で到達不能なら記録してスキップ（撮影しない）
    if (resp && resp.status() >= 400) {
      testInfo.annotations.push({ type: "warn", value: `${screen.path} -> HTTP ${resp.status()}` });
      if (ctx) await ctx.close();
      test.skip(true, `unreachable ${screen.path}`);
      return;
    }

    await p.addStyleTag({ content: FREEZE_CSS });
    await p.waitForTimeout(300); // レイアウト確定待ち
    await expect(p).toHaveScreenshot(`${screen.name}.png`, {
      fullPage: true,
      maxDiffPixelRatio: 0.02,
      animations: "disabled",
    });

    if (ctx) await ctx.close();
  });
}

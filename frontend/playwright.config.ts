import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config — E2E + Visual Regression。
 * baseURL は PLAYWRIGHT_BASE_URL（CI=ローカルNext / 既定=本番CloudFront）。
 * 認証はsetupプロジェクトでGoldenユーザーのstorageStateを生成し各projectで再利用。
 * Golden Dataset 投入済みのDBに対して実行すること（tests/seed/golden_seed.py）。
 */
const baseURL = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000";
const AUTH_STATE = "playwright/.auth/user.json";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 45_000,
  expect: { toHaveScreenshot: { maxDiffPixelRatio: 0.02 } },
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  // ローカルではアプリ（Next / API / DB）と同じマシンでブラウザを動かす。既定（論理コア数の半分、
  // 16スレッド機で8）だと動画録画込みのブラウザ8つで全コアが埋まり、起動直後の Next が
  // 応答できず時間切れになった（8並列: 初回の各テスト12〜19秒 / 4並列: 0.1〜5秒）。
  workers: process.env.CI ? 2 : 4,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "setup", testMatch: /.*\.setup\.ts/ },
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 }, storageState: AUTH_STATE },
      dependencies: ["setup"],
    },
    {
      name: "tablet",
      use: { ...devices["iPad (gen 7)"], storageState: AUTH_STATE },
      dependencies: ["setup"],
    },
    {
      name: "mobile",
      use: { ...devices["Pixel 5"], storageState: AUTH_STATE },
      dependencies: ["setup"],
    },
  ],
});

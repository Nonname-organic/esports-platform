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
  workers: process.env.CI ? 2 : undefined,
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

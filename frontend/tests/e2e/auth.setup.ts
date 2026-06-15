import { test as setup, expect } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";

/**
 * 認証セットアップ — Goldenユーザーでログインし storageState を保存。
 * 各viewport projectがこのstateを使い回す（毎回ログインしない）。
 * 前提: Golden Dataset 投入済み（captain@golden.test / Passw0rd!）。
 *
 * GOLDEN_EMAIL / GOLDEN_PASSWORD で上書き可能。
 */
const AUTH_FILE = path.join(__dirname, "..", "..", "playwright", ".auth", "user.json");
const EMAIL = process.env.GOLDEN_EMAIL || "captain@golden.test";
const PASSWORD = process.env.GOLDEN_PASSWORD || "Passw0rd!";

setup("authenticate", async ({ page }) => {
  fs.mkdirSync(path.dirname(AUTH_FILE), { recursive: true });

  await page.goto("/login");
  await page.getByLabel("メールアドレス").fill(EMAIL);
  await page.getByLabel("パスワード").fill(PASSWORD);
  await page.getByRole("button", { name: "ログイン" }).click();

  // ログイン成功で /dashboard へ遷移し、トークンが永続化される
  await page.waitForURL("**/dashboard", { timeout: 15_000 });
  await expect
    .poll(async () => page.evaluate(() => localStorage.getItem("access_token")), { timeout: 10_000 })
    .not.toBeNull();

  await page.context().storageState({ path: AUTH_FILE });
});

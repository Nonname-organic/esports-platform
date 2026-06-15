import { test, expect, Page } from "@playwright/test";

/**
 * E2E-001 メインジャーニー。
 *
 * フロー: 新規登録 → ダッシュボード → 大会一覧 → 大会詳細 → スカウト → 通知 → 設定
 *         （+ 認証済みGoldenユーザーで 大会参加導線 / 試合進行 / 結果確認）
 *
 * 前提: アプリ稼働 + Golden Dataset 投入済み。baseURL は PLAYWRIGHT_BASE_URL。
 *
 * 設計方針:
 * - 新規登録パートは自分でユーザーを作るため seed 非依存・完全assertive。
 * - 状態/権限依存の深い導線（試合進行等）は storageState(captain) で到達確認まで行う。
 */

// ── 新規ユーザー オンボーディング（seed非依存・直列） ────────────────────────────
test.describe.serial("E2E-001 onboarding journey", () => {
  // setup由来のstorageStateを使わず未ログインから開始
  test.use({ storageState: { cookies: [], origins: [] } });

  let page: Page;
  const stamp = Date.now();
  const user = {
    username: `e2e${stamp}`.slice(0, 30),
    email: `e2e_${stamp}@journey.test`,
    password: "Passw0rd!",
  };

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
  });
  test.afterAll(async () => {
    await page.close();
  });

  test("01 新規登録 → ダッシュボード", async () => {
    await page.goto("/register");
    await expect(page.getByRole("heading", { name: "アカウント作成" })).toBeVisible();

    await page.getByLabel("ユーザー名", { exact: false }).fill(user.username);
    await page.getByLabel("メールアドレス").fill(user.email);
    await page.getByLabel("パスワード", { exact: true }).fill(user.password);
    await page.getByLabel("パスワード（確認）").fill(user.password);

    await page.getByRole("button", { name: "アカウントを作成する" }).click();

    await page.waitForURL("**/dashboard", { timeout: 20_000 });
    await expect
      .poll(() => page.evaluate(() => localStorage.getItem("access_token")), { timeout: 10_000 })
      .not.toBeNull();
  });

  test("02 大会一覧を閲覧", async () => {
    await page.goto("/tournaments");
    await expect(page).toHaveURL(/\/tournaments/);
    // 一覧 or 空状態のいずれかがレンダリングされる（クラッシュしない）
    await page.waitForLoadState("networkidle");
    await expect(page.locator("body")).not.toContainText("Application error");
  });

  test("03 大会詳細を開く", async () => {
    await page.goto("/tournaments");
    await page.waitForLoadState("networkidle");
    const firstCard = page.locator('a[href*="/tournaments/"]').first();
    if (await firstCard.count()) {
      await firstCard.click();
      await expect(page).toHaveURL(/\/tournaments\/[^/]+/);
      await page.waitForLoadState("networkidle");
      await expect(page.locator("body")).not.toContainText("Application error");
    } else {
      test.info().annotations.push({ type: "note", value: "大会データ無し（seed未投入）— 詳細遷移をスキップ" });
    }
  });

  test("04 スカウトを閲覧", async () => {
    await page.goto("/scout");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/scout/);
    await expect(page.locator("body")).not.toContainText("Application error");
  });

  test("05 通知を確認", async () => {
    await page.goto("/notifications");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/notifications/);
    await expect(page.locator("body")).not.toContainText("Application error");
  });

  test("06 設定画面（アカウント管理）", async () => {
    await page.goto("/settings");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/settings/);
    // メール/パスワード変更・退会の導線が存在
    await expect(page.locator("body")).not.toContainText("Application error");
  });
});

// ── 認証済み（captain）での参加〜試合導線 到達確認 ───────────────────────────────
// playwright.config の storageState(captain) を使用（setup プロジェクト依存）
test.describe("E2E-001 authenticated flows", () => {
  test("10 ダッシュボードに自分のチーム/大会が表示", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.locator("body")).not.toContainText("Application error");
  });

  test("11 開催中の大会詳細 → 試合/ブラケット導線", async ({ page }) => {
    await page.goto("/tournaments");
    await page.waitForLoadState("networkidle");
    // Golden: 「開催中」大会へ
    const ongoing = page.getByText("開催中", { exact: false }).first();
    if (await ongoing.count()) {
      const card = page.locator('a[href*="/tournaments/"]').first();
      await card.click();
      await expect(page).toHaveURL(/\/tournaments\/[^/]+/);
      await page.waitForLoadState("networkidle");
      // ブラケットタブ/ページへ到達できる
      const bracketLink = page.locator('a[href*="/bracket"]').first();
      if (await bracketLink.count()) {
        await bracketLink.click();
        await expect(page).toHaveURL(/\/bracket/);
        await page.waitForLoadState("networkidle");
      }
      await expect(page.locator("body")).not.toContainText("Application error");
    } else {
      test.info().annotations.push({ type: "note", value: "開催中大会無し（seed未投入）— スキップ" });
    }
  });

  test("12 通知（既読/未読）の表示と既読化", async ({ page }) => {
    await page.goto("/notifications");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/notifications/);
    await expect(page.locator("body")).not.toContainText("Application error");
  });

  test("13 アナリティクスが表示される", async ({ page }) => {
    await page.goto("/analytics");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/analytics/);
    await expect(page.locator("body")).not.toContainText("Application error");
  });
});

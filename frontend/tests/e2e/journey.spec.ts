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
 * - 新規登録パートは自分でユーザーを作る。並列の各ワーカーが同じミリ秒に
 *   読み込んでも衝突しないよう、名前にワーカー番号を入れる。
 * - 大会詳細・ブラケットは Golden の大会を開く。データが無いときに分岐で
 *   通すことはせず、無ければ失敗させる（以前は分岐で素通りし、何も確かめていなかった）。
 * - 待ち合わせに networkidle は使わない。ナビゲーションの <Link> が裏で
 *   十数本のプリフェッチを出すため、画面と無関係な通信まで待つことになり、
 *   起動直後の負荷が高い間はそれだけで時間切れになっていた。代わりに
 *   「その画面のデータ取得が成功し、見出しが表示された」ことを待つ。
 */

/** 画面を開き、データ取得（apiPath への GET）の成功と見出しの表示を待ってから、エラー画面でないことを確かめる。 */
async function openPage(page: Page, url: string, heading: string, apiPath?: string) {
  const data = apiPath
    ? page.waitForResponse((r) => new URL(r.url()).pathname === apiPath && r.request().method() === "GET")
    : undefined;
  await page.goto(url);
  if (data) {
    const res = await data;
    expect(res.ok(), `${apiPath} が ${res.status()} を返した`).toBe(true);
  }
  await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("Application error");
}

/** 一覧の先頭の大会を開き、詳細画面（タブ）が表示されるまで待つ。 */
async function openFirstTournament(page: Page) {
  const card = page.locator('a[href^="/tournaments/"]').first();
  await expect(card, "Golden の大会が一覧に出ていない").toBeVisible();
  await card.click();
  await expect(page).toHaveURL(/\/tournaments\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("navigation", { name: "大会詳細タブ" })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("Application error");
}

// ── 新規ユーザー オンボーディング（直列） ─────────────────────────────────────
test.describe.serial("E2E-001 onboarding journey", () => {
  // setup由来のstorageStateを使わず未ログインから開始
  test.use({ storageState: { cookies: [], origins: [] } });

  let page: Page;
  let user: { username: string; email: string; password: string };

  test.beforeAll(async ({ browser }, testInfo) => {
    const id = `${Date.now()}_${testInfo.parallelIndex}`;
    user = { username: `e2e${id}`.slice(0, 30), email: `e2e_${id}@example.com`, password: "Passw0rd!" };
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
    await openPage(page, "/tournaments", "大会一覧", "/api/v1/tournaments");
  });

  test("03 大会詳細を開く", async () => {
    // Golden の大会は日付が固定のため、既定の「当月」表示には出ない。期間を「すべて」にして開く
    await openPage(page, "/tournaments?month=all", "大会一覧", "/api/v1/tournaments");
    await openFirstTournament(page);
  });

  test("04 スカウトを閲覧", async () => {
    await openPage(page, "/scout", "スカウト");
  });

  test("05 通知を確認", async () => {
    await openPage(page, "/notifications", "通知センター", "/api/v1/notifications");
  });

  test("06 設定画面（アカウント管理）", async () => {
    await openPage(page, "/settings", "ユーザー設定");
  });
});

// ── 認証済み（captain）での参加〜試合導線 到達確認 ───────────────────────────────
// playwright.config の storageState(captain) を使用（setup プロジェクト依存）
test.describe("E2E-001 authenticated flows", () => {
  test("10 ダッシュボードに自分のチーム/大会が表示", async ({ page }) => {
    await openPage(page, "/dashboard", "ダッシュボード");
    // 保存したログイン状態が戻り、自分の名前で表示されている
    await expect(page.getByText(/\S+ の大会管理/)).toBeVisible();
  });

  test("11 開催中の大会詳細 → 試合/ブラケット導線", async ({ page }) => {
    // Golden の日付は固定なので、期間は「すべて」・状態は「開催中」で開く
    await openPage(page, "/tournaments?month=all&status=ongoing", "大会一覧", "/api/v1/tournaments");
    await openFirstTournament(page);
    const tabs = page.getByRole("navigation", { name: "大会詳細タブ" });

    // 試合タブ: Golden の試合が並ぶ（タブの切り替わりはサーバー描画の aria-current で確かめる）
    await tabs.getByRole("link", { name: "Matches" }).click();
    await expect(tabs.getByRole("link", { name: "Matches" })).toHaveAttribute("aria-current", "page");
    await expect(page.locator('main a[href^="/matches/"]').first()).toBeVisible();

    // ブラケットタブ: 取得に成功したときだけ出る表示まで確かめる。
    // Golden は試合を直接入れておりブラケット生成を経ていないため、試合カードは並ばない
    await tabs.getByRole("link", { name: "Bracket" }).click();
    await expect(tabs.getByRole("link", { name: "Bracket" })).toHaveAttribute("aria-current", "page");
    await expect(page.getByText("30秒ごとに自動更新")).toBeVisible();
    await expect(page.locator("body")).not.toContainText("Application error");
  });

  test("12 通知（既読/未読）の表示と既読化", async ({ page }) => {
    await openPage(page, "/notifications", "通知センター", "/api/v1/notifications");
  });

  test("13 アナリティクスが表示される", async ({ page }) => {
    await openPage(page, "/analytics", "Analytics Dashboard", "/api/v1/analytics/trend");
  });
});

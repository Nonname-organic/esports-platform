import { test, expect } from "@playwright/test";

/**
 * ログイン後の転送先（?next=）。実際のブラウザで、同じサイトの相対パスにだけ戻り、
 * 外部サイトや javascript: の URL には進まないことを、最終的な遷移先で確かめる（RC2 の S2）。
 *
 * ログインは IP ごとに 10 回/分までなので、desktop だけで 6 件にしている（setup の 1 回と合わせて 7 回）。
 */
const EMAIL = process.env.GOLDEN_EMAIL || "captain@golden.test";
const PASSWORD = process.env.GOLDEN_PASSWORD || "Passw0rd!";

const CASES: Array<[string, string]> = [
  ["/tournaments", "/tournaments"],
  ["//example.com", "/dashboard"],
  ["/\\example.com", "/dashboard"],
  ["javascript:alert(document.domain)", "/dashboard"],
  ["/\t/example.com", "/dashboard"],
  ["/.//example.com", "/dashboard"],
];

test.describe("ログイン後の転送先", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  for (const [next, expected] of CASES) {
    test(`next=${JSON.stringify(next)} → ${expected}`, async ({ page, baseURL }, testInfo) => {
      test.skip(testInfo.project.name !== "desktop", "ログインの回数制限に収めるため desktop だけで確かめる");
      const dialogs: string[] = [];
      page.on("dialog", (d) => {
        dialogs.push(d.message());
        void d.dismiss();
      });

      await page.goto(`/login?next=${encodeURIComponent(next)}`);
      await page.getByLabel("メールアドレス").fill(EMAIL);
      await page.getByLabel("パスワード").fill(PASSWORD);
      await page.getByRole("button", { name: "ログイン" }).click();

      await page.waitForURL((url) => url.pathname === expected, { timeout: 20_000 });
      expect(new URL(page.url()).origin).toBe(new URL(baseURL!).origin);
      expect(dialogs, "スクリプトが実行された").toEqual([]);
    });
  }
});

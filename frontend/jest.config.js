/**
 * Jest はユニットテスト専用。
 *
 * tests/e2e は Playwright のスペックで、playwright.config.ts が testDir として
 * 持っている。設定が無いと Jest の既定の testMatch がそこまで拾ってしまい、
 * Playwright の構文を解釈できずに「Test suite failed to run」で落ちる。
 *
 * 現時点でユニットテストは1件も無いため、npm test は --passWithNoTests で通る。
 * ユニットテストを足すときは TypeScript のトランスフォーム（next/jest など）の
 * 設定もここに追加する。
 */
module.exports = {
  testPathIgnorePatterns: ["<rootDir>/node_modules/", "<rootDir>/tests/e2e/"],
};

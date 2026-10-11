/**
 * Jest はユニットテスト専用。
 *
 * tests/e2e は Playwright のスペックで、playwright.config.ts が testDir として
 * 持っている。設定が無いと Jest の既定の testMatch がそこまで拾ってしまい、
 * Playwright の構文を解釈できずに「Test suite failed to run」で落ちる。
 *
 * TypeScript の変換と @/ エイリアスの解決は next/jest に任せる（next 本体に
 * 同梱されているので追加の依存は不要）。testEnvironment は既定の node のまま。
 * DOM を触るテストを足すときは jest-environment-jsdom を入れたうえで
 * testEnvironment: "jsdom" を指定する。
 */
const nextJest = require("next/jest");

const createJestConfig = nextJest({ dir: "./" });

module.exports = createJestConfig({
  testPathIgnorePatterns: ["<rootDir>/node_modules/", "<rootDir>/tests/e2e/"],
  // .next はビルド成果物。standalone 出力に package.json が入るため、
  // 走査させると haste module の名前衝突で警告が出る。
  modulePathIgnorePatterns: ["<rootDir>/.next/"],
});

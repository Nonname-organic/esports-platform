// ESLint 設定。これまで設定ファイルが無く、`npm run lint` は対話プロンプトで止まっていた。
import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: dirname(fileURLToPath(import.meta.url)) });

export default [
  { ignores: [".next/**", "node_modules/**", "playwright-report/**", "test-results/**"] },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    // shortcut: 既存コードに未使用変数 70件・any 37件が残っているため警告に留める。
    // 解消したら error に戻す。フックの誤用など実害のある規則は error のまま。
    rules: {
      "@typescript-eslint/no-unused-vars": "warn",
      "@typescript-eslint/no-explicit-any": "warn",
    },
  },
];

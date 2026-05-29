# Phase 4: Frontend設計（Next.js App Router）

---

## 1. SSR / ISR / CSR 使い分け方針

| ページ | 戦略 | 理由 |
|-------|------|------|
| トップページ | **SSG** | 静的コンテンツ、ビルド時生成で最速 |
| 大会一覧 | **ISR (5分)** | SEO必要・更新頻度低め・キャッシュ有効 |
| 大会詳細 | **SSR** | SEO必要・最新データ必須（参加締切など） |
| ブラケット | **SSR + CSR** | 初期表示はSSR、試合中はWSでCSR更新 |
| 試合詳細 | **CSR** | リアルタイムスコア・WebSocket必須 |
| ダッシュボード | **CSR** | 認証済み画面・SEO不要 |
| 分析ページ | **CSR + SWR** | ユーザー操作でフィルタ変更 |
| ランキング | **ISR (15分)** | SEO有効・頻繁な更新不要 |

---

## 2. ディレクトリ構成

```
frontend/
├── src/
│   ├── app/                          # App Router
│   │   ├── layout.tsx                # Root Layout（Header/Footer）
│   │   ├── page.tsx                  # Home (SSG)
│   │   ├── (public)/                 # 認証不要グループ
│   │   │   ├── tournaments/
│   │   │   │   ├── page.tsx          # 大会一覧 (ISR)
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx      # 大会詳細 (SSR)
│   │   │   │       └── bracket/
│   │   │   │           └── page.tsx  # ブラケット (SSR+CSR)
│   │   │   └── matches/
│   │   │       └── [id]/
│   │   │           └── page.tsx      # 試合詳細 (CSR)
│   │   ├── (auth)/                   # 認証済みグループ
│   │   │   ├── layout.tsx            # 認証チェックLayout
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx
│   │   │   └── analytics/
│   │   │       └── page.tsx          # 分析ダッシュ (CSR)
│   │   └── (admin)/                  # 管理者グループ
│   │       └── admin/
│   │           └── page.tsx
│   ├── components/
│   │   ├── ui/                       # shadcn/ui (自動生成)
│   │   └── layout/
│   │       └── header.tsx
│   ├── features/                     # 機能別モジュール
│   │   ├── tournaments/
│   │   │   ├── components/           # UIコンポーネント
│   │   │   ├── hooks/                # カスタムフック
│   │   │   └── api/                  # API関数
│   │   ├── matches/
│   │   └── analytics/
│   ├── lib/
│   │   ├── api-client.ts             # fetch wrapper
│   │   └── query-client.ts           # TanStack Query設定
│   ├── store/
│   │   └── auth-store.ts             # Zustand
│   └── types/                        # 型定義
├── Dockerfile
├── next.config.ts
└── package.json
```

---

## 3. 技術選定理由

| 技術 | 理由 |
|------|------|
| **App Router** | Server Components でSEO最適化・初期表示高速化 |
| **TanStack Query** | サーバー状態管理・キャッシュ・楽観的更新 |
| **Zustand** | 認証状態などクライアント状態。Redux より軽量 |
| **Tailwind CSS** | ユーティリティファーストで開発速度最大化 |
| **shadcn/ui** | コピペで使えるRadix UI + Tailwind製コンポーネント |
| **Recharts** | React製・SSR対応・TypeScript型付き |
| **SWR** | WebSocket連携・リアルタイム更新 |

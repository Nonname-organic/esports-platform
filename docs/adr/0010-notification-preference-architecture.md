# ADR-0010: Notification Preference Architecture

- **Status**: Accepted
- **Date**: 2026-07-04
- **Deciders**: Solo developer

## Context
機能③（ユーザーごとの通知 ON/OFF）を実装する。P1-2 で `PreferenceResolver.is_enabled(user, category, channel)` のスタブ（常に True）と Notification Event Matrix（SSOT）を用意済み。
懸念は、通知設定の保存形（JSONB）が **Dispatcher / Channel Provider / API / UI に漏れ出す**こと。JSONB 構造が各所に散ると、設定項目の追加・デフォルト変更・precedence 変更のたびに複数箇所を直す必要が生じ、5年運用で破綻する。

本ADRは、Preference の**責務境界**を確定する（ADR-0005, 0008, Notification Event Matrix を前提）。

## Decision

### 1. 責務の分離（3者）
- **Notification Matrix（SSOT: 何を誰にどのチャネルで）**
  イベント → `category` / `channels` / `recipients` の写像。「どの通知がどのカテゴリか」の唯一の定義。
- **PreferenceService（SSOT: 誰がどの通知を受けるか）**
  ユーザーごとの ON/OFF を管理する**唯一の窓口**。判定 API は `is_enabled(user_id, category, channel) -> bool` のみ公開。
  取得/更新（`get_preferences` / `update_preferences`）もここに集約。
- **Provider（どう送るか）**
  Browser / Email / Discord の送信手段。Preference も Matrix も知らない（受け取った Message を送るだけ）。

### 2. PreferenceService を唯一の SSOT とする（JSONB 隠蔽）
- `notification_preferences.prefs`（JSONB）の**構造・キー名・デフォルト値・precedence を知るのは PreferenceService だけ**。
- **Dispatcher / Provider / Consumer / Router は JSONB を直接参照しない**。必ず PreferenceService 経由:
  - 配信判定: `NotificationDispatcher` は `PreferenceService.is_enabled(...)` を呼ぶ（現在の `PreferenceResolver` を PreferenceService 実装に差し替え）。
  - 設定画面 API: `PreferenceService.get_preferences / update_preferences` を呼ぶ（DTOで受け渡し）。
- API/UI に渡すのは**正規化済み DTO**（`{channels: {...}, categories: {...}}`）であり、DBの生 JSONB ではない。内部表現が変わっても DTO 契約を保てば UI 無変更。

### 3. precedence（判定順）を PreferenceService に閉じ込める
```
global channel OFF  >  per-entity mute(将来)  >  category OFF  >  default ON
```
- 未設定キーは **default ON**（後方互換: 既存ユーザーは全通知が届く）。
- この順序ロジックは PreferenceService の内部実装。呼び出し側は `is_enabled` の真偽だけを見る。

### 4. カテゴリ/チャネルの定義
- カテゴリ（`tournament` / `team` / `scout` / `match`）は **Notification Matrix 由来**（Matrix が category の源）。PreferenceService はそのキーを ON/OFF 管理するだけで、カテゴリ自体を再定義しない。
- チャネル（`browser` / `email` / `discord`）は ChannelRegistry と一致させる。email は将来だが設定キーとしては先に持てる（default ON でも Provider が no-op なら無害）。
- **新カテゴリ/新チャネル追加 = Matrix/Registry に足すだけ**でマイグレーション不要（JSONB のため）。

## Consequences
- (+) JSONB 構造の変更が **PreferenceService 内に限定**される。Dispatcher/Provider/UI は不変。
- (+) 「何を通知するか（Matrix）」と「誰が受けるか（Preference）」が独立して進化できる。
- (+) precedence やデフォルトの方針変更が1箇所（PreferenceService）で完結。
- (−) 直接 JSONB を触れば数行で済む処理に薄い層が挟まる。SSOT 化の対価として許容。
- 既存 P1-2 の `PreferenceResolver`（スタブ）は **PreferenceService へ置き換え**（インターフェース `is_enabled` は不変なので Dispatcher は無変更）。

## Alternatives considered
- Dispatcher/Provider が JSONB を直接参照: 設定構造が各所に漏れ、変更が多点に波及。→ 却下。
- 正規化テーブル（user×category×channel 行）: 現フェーズには過剰。JSONB + Service 隠蔽で十分（将来スケール時に PreferenceService 内実装だけ差し替え可能）。→ 却下（将来トリガーで再検討）。

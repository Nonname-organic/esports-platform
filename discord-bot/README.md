# Esports Platform Discord Bot

大会運営を自動化する Discord Bot（discord.py）。

## アーキテクチャ

```
プラットフォーム ──[SQS/Redis discord-queue]──▶ Bot (event_consumer)
                                                     │
                                                     ▼
                                              Discord API (guild操作)

Discord(/コマンド) ──▶ Bot (cogs) ──HTTP──▶ プラットフォームAPI
```

## イベント処理

| イベント | 動作 |
|---|---|
| `setup_tournament` | カテゴリ・チャンネル・ロール一括生成 |
| `create_match_channel` | `match-001` を🏆MATCHESに生成 |
| `archive_match_channel` | 試合終了で📦ARCHIVEへ移動・読取専用化 |

## スラッシュコマンド

`/create-tournament` `/bracket` `/check-in` `/report-result` `/match` `/team` `/player` `/help`

## セットアップ手順

### 1. Discord Developer Portal でBot作成
1. https://discord.com/developers/applications → New Application
2. Bot → Add Bot → Token を取得
3. OAuth2 → URL Generator → scopes: `bot` `applications.commands`
   - 権限: Manage Channels, Manage Roles, Send Messages
4. 生成URLでBotをサーバーに招待

### 2. 環境変数設定
```env
DISCORD_BOT_TOKEN=<bot token>
DISCORD_GUILD_ID=<開発用ギルドID（任意）>
API_BASE_URL=http://api:8000
BOT_API_TOKEN=<プラットフォームのBot用トークン>
USE_REDIS_QUEUE=true
REDIS_URL=redis://redis:6379/0
```

### 3. 起動
```bash
docker compose --profile discord up -d discord-bot
```

## 必要なDiscord権限（Intents）
- Server Members Intent（メンバー管理）
- ※ Privileged Gateway Intents を Developer Portal で有効化

# ADR-0003: Docker PostgreSQL を維持し pg_dump→S3 バックアップを追加（RDS/HA は延期）

- **Status**: Accepted
- **Date**: 2026-07-04
- **Deciders**: Solo developer (Principal review 反映)

## Context
コスト削減のため RDS から EC2 上の Docker PostgreSQL へ移行済み（月約$19削減）。しかしこれで自動バックアップ・PITR・Multi-AZ を失った。Principalレビューは「単一EC2 + コンテナPostgres（backup/HA無し）」を最大の運用リスクと指摘。一方、現フェーズはコスト優先・数百人規模で HA は過剰。**「データを全損させない」ことが最優先要件**であり、それは可用性(HA)ではなく耐久性(backup)で満たせる。

## Decision
- **Docker PostgreSQL を維持**（RDS へ戻さない）。
- **pg_dump → S3 の夜次自動バックアップ**を追加（世代保持・復元手順を文書化）。
- **HA / Multi-AZ / PITR / Read Replica は実装しない**（接続をRepositoryに集約し、将来の差し替え余地のみ確保）。

## Consequences
- (+) コスト維持しつつデータ全損リスクを解消（RPO = 最大1日）。
- (+) 復元は S3 の dump を restore するだけ（シンプル）。
- (−) RPO 最大24h・単一AZ・フェイルオーバー無し。EC2/EBS障害時はダウンタイム発生。現フェーズでは許容。
- **Scale Trigger**: データ耐久/HA要件の発生、または DBサイズ/EBS IOPS 逼迫で RDS/Aurora（Multi-AZ + PITR + Read Replica）へ移行を検討。頻度を上げたい場合は WAL アーカイブ（WAL-G）で PITR 化。

## Alternatives considered
- RDS へ即戻す: コスト増。現フェーズの要件(全損回避)は backup で足りる。→ 却下。
- バックアップ無しで継続: データ全損リスク放置。→ 却下（P0で必須）。

# Domain Design - World-Class Esports SaaS

## Bounded Contexts

### 1. Tournament Context
- Tournament, Registration, Bracket, Match, Round, CheckIn

### 2. Player Context  
- Player, PlayerStats, PlayerRating, Career, Achievement

### 3. Team Context
- Team, TeamMember, TeamStats, Roster, Recruitment

### 4. Analytics Context
- MapStats, AgentStats, CompositionStats, MetaTrend

### 5. Scout Context
- ScoutProfile, Recruitment, Rating (ELO/Glicko2)

### 6. Event Context
- TournamentEvent, MatchEvent, PlayerEvent

### 7. Discord Context
- Server, Channel, BotCommand, Sync

## Domain Events

TournamentCreated → [Bracket生成, Discord通知, SEO page生成]
MatchStarted → [WebSocket配信, Discord通知, Stream開始]
MatchFinished → [Stats計算, Rating更新, 次試合生成, Discord結果投稿]
CheckInCompleted → [シード確定, Auto forfeit開始]
PlayerRegistered → [Rating初期化, Career作成]
ResultSubmitted → [Ranking更新, Analytics集計]

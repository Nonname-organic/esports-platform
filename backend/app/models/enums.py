import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ORGANIZER = "organizer"
    TEAM_MANAGER = "team_manager"
    PLAYER = "player"


class GameType(str, enum.Enum):
    VALORANT = "VALORANT"
    LOL = "LOL"
    APEX = "APEX"
    CS2 = "CS2"
    OVERWATCH = "OVERWATCH"


class TournamentFormat(str, enum.Enum):
    SINGLE_ELIMINATION = "single_elimination"
    DOUBLE_ELIMINATION = "double_elimination"
    ROUND_ROBIN = "round_robin"
    SWISS = "swiss"


class TournamentStatus(str, enum.Enum):
    DRAFT = "draft"
    REGISTRATION_OPEN = "registration_open"
    REGISTRATION_CLOSED = "registration_closed"
    CHECK_IN = "check_in"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RegistrationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    WAITLISTED = "waitlisted"


class MemberRole(str, enum.Enum):
    CAPTAIN = "captain"
    PLAYER = "player"
    SUBSTITUTE = "substitute"
    COACH = "coach"
    ANALYST = "analyst"


class BOFormat(str, enum.Enum):
    BO1 = "BO1"
    BO3 = "BO3"
    BO5 = "BO5"


class MatchStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FORFEIT = "forfeit"
    NO_SHOW = "no_show"


class BanPickAction(str, enum.Enum):
    BAN = "ban"
    PICK = "pick"


class SideType(str, enum.Enum):
    ATTACK = "attack"
    DEFENSE = "defense"


class NotificationType(str, enum.Enum):
    MATCH_START = "match_start"
    MATCH_RESULT = "match_result"
    MATCH_SCHEDULED = "match_scheduled"
    REGISTRATION_APPROVED = "registration_approved"
    REGISTRATION_REJECTED = "registration_rejected"
    CHECK_IN_REMINDER = "check_in_reminder"
    TOURNAMENT_START = "tournament_start"
    TOURNAMENT_CANCELLED = "tournament_cancelled"
    BRACKET_UPDATED = "bracket_updated"
    GENERAL = "general"


class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    DISCORD = "discord"
    EMAIL = "email"


class CheckInMethod(str, enum.Enum):
    QR = "qr"
    MANUAL = "manual"


class PeriodType(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    TOURNAMENT = "tournament"
    ALL_TIME = "all_time"


class AnalyticsEventSource(str, enum.Enum):
    APPLICATION = "application"
    RIOT_API = "riot_api"
    MANUAL = "manual"
    WEBHOOK = "webhook"

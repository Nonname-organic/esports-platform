import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.player import Player
    from app.models.team import Team
    from app.models.tournament import Tournament
    from app.models.notification import Notification
    from app.models.audit_log import AuditLog


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.VIEWER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    discord_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    player: Mapped[Optional["Player"]] = relationship(
        "Player", back_populates="user", uselist=False
    )
    owned_teams: Mapped[list["Team"]] = relationship(
        "Team", back_populates="owner", foreign_keys="Team.owner_id"
    )
    organized_tournaments: Mapped[list["Tournament"]] = relationship(
        "Tournament", back_populates="organizer"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user", order_by="Notification.created_at.desc()"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"

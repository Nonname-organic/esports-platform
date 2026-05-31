import enum as _enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as _SAEnum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def pg_enum(enum_cls: type[_enum.Enum], *, name: str, **kwargs) -> _SAEnum:
    """PostgreSQL ENUM column using the .value of each member (lowercase)."""
    return _SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda x: [e.value for e in x],
        **kwargs,
    )


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

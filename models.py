from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    # Mapped[] for Python type hints, mapped_column() for DB types
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )  # PKs actually get indexed automatically
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    image_file: Mapped[str | None] = (
        mapped_column(  # Stores file name (not entire path), None matches nullable=True
            String(200),
            nullable=True,
            default=None,
        )
    )

    posts: Mapped[list[Post]] = relationship(
        back_populates="author"
    )  # One to many via user.posts

    @property  # This is Python property, not DB
    def image_path(self) -> str:
        if self.image_file:
            return f"/media/profile_pics/{self.image_file}"  # Path if a user has an uploaded image
        return "/static/profile_pics/default.jpg"  # Else, uses default image path


class Post(Base):
    __tablename__ = "posts"

    # Mapped[] for Python type hints, mapped_column() for DB types
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )  # PKs actually get indexed automatically
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,  # FKs don't get indexed automatically
    )
    date_posted: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # Renders as timestamptz in PG
        default=lambda: datetime.now(UTC),
    )

    author: Mapped[User] = relationship(
        back_populates="posts"
    )  # Many to one via post.author

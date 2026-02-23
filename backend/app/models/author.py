from __future__ import annotations

from sqlalchemy import Column, String, Boolean, TIMESTAMP, text

from app.db.base import Base


class Author(Base):
    __tablename__ = "authors"

    # Reddit author fullname (t2_*) or username as fallback
    author_id = Column(String(100), primary_key=True)
    author_name = Column(String(100), nullable=True)
    created_utc = Column(TIMESTAMP(timezone=True), nullable=True)
    is_bot = Column(Boolean, nullable=False, server_default=text("false"))
    first_seen_at_global = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class SubredditSnapshot(Base):
    __tablename__ = "subreddit_snapshots"

    from sqlalchemy import BigInteger, Sequence
    id = Column(BigInteger, Sequence("subreddit_snapshots_id_seq"), primary_key=True)
    subreddit = Column(String(100), nullable=False)
    captured_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    subscribers = Column(String(32), nullable=True)  # use string to avoid overflow surprises
    active_user_count = Column(String(32), nullable=True)
    rules_text = Column(String, nullable=True)
    over18 = Column(Boolean, nullable=True)

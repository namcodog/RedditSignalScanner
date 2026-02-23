from __future__ import annotations

from datetime import datetime, timezone
import enum

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Float,
    Index,
    Integer,
    Sequence,
    String,
    Text,
    UniqueConstraint,
    func,
    Enum as SQLEnum,
)

from app.db.base import Base


class ContentType(enum.Enum):
    POST = "post"
    COMMENT = "comment"


class Category(enum.Enum):
    PAIN = "pain"
    SOLUTION = "solution"
    OTHER = "other"


class Aspect(enum.Enum):
    PRICE = "price"
    SUBSCRIPTION = "subscription"
    SUB_CANCEL = "sub_cancel"
    SUB_HIDDEN_FEE = "sub_hidden_fee"
    SUB_AUTO_RENEW = "sub_auto_renew"
    SUB_PRICE = "sub_price"
    SCAM = "scam"
    CONTENT = "content"
    INSTALL = "install"
    ECOSYSTEM = "ecosystem"
    STRENGTH = "strength"
    QUALITY = "quality"
    SHIPPING = "shipping"
    SERVICE = "service"
    FUNCTION = "function"
    UX = "ux"
    RETURN = "return"
    OTHER = "other"


class EntityType(enum.Enum):
    BRAND = "brand"
    FEATURE = "feature"
    PLATFORM = "platform"
    OTHER = "other"


class Comment(Base):
    """Reddit comment with full conversation context for analysis.

    Note: We link comments to posts via (source, source_post_id) pair to
    remain compatible with hot/cold storage (no single posts table).
    """

    __tablename__ = "comments"
    __table_args__ = (
        UniqueConstraint("reddit_comment_id", name="uq_comments_reddit_comment_id"),
        CheckConstraint("depth >= 0", name="ck_comments_depth_non_negative"),
        Index("idx_comments_post_time", "source", "source_post_id", "created_utc"),
        Index("idx_comments_subreddit_time", "subreddit", "created_utc"),
    )

    id = Column(BigInteger, Sequence("comments_id_seq"), primary_key=True)
    reddit_comment_id = Column(String(32), nullable=False)

    # post linkage (no FK to specific posts table by design)
    source = Column(String(50), nullable=False, default="reddit")
    source_post_id = Column(String(100), nullable=False)
    subreddit = Column(String(100), nullable=False)
    source_track = Column(String(32), nullable=True, default="incremental")

    parent_id = Column(String(32))  # fullname id from Reddit API (e.g., t1_*, t3_*)
    depth = Column(Integer, nullable=False, default=0)
    body = Column(Text, nullable=False)

    author_id = Column(String(100))
    author_name = Column(String(100))
    author_created_utc = Column(TIMESTAMP(timezone=True))

    created_utc = Column(TIMESTAMP(timezone=True), nullable=False)
    first_seen_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )
    fetched_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )
    score = Column(Integer, nullable=False, default=0)
    is_submitter = Column(Boolean, nullable=False, default=False)
    distinguished = Column(String(32))
    edited = Column(Boolean, nullable=False, default=False)
    permalink = Column(Text)
    removed_by_category = Column(String(64))
    awards_count = Column(Integer, nullable=False, default=0)
    lang = Column(String(10))
    business_pool = Column(String(10), default="lab")  # legacy compatibility
    captured_at = Column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class ContentLabel(Base):
    """Semantic label for either a post or a comment."""

    __tablename__ = "content_labels"
    __table_args__ = (
        Index("idx_content_labels_target", "content_type", "content_id"),
        Index("idx_content_labels_cat_aspect", "category", "aspect"),
    )

    id = Column(BigInteger, Sequence("content_labels_id_seq"), primary_key=True)
    content_type = Column(
        SQLEnum(
            ContentType,
            name="content_type",
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    content_id = Column(BigInteger, nullable=False)
    # NOTE: category/aspect 需要允许历史/回填写入的自由文本（例如 pain_tag/aspect_tag），
    # 不能再用 Enum 强校验，否则会在读写时抛 Enum 映射错误并刷屏 worker 日志。
    category = Column(String(255), nullable=False)
    aspect = Column(String(255), nullable=False, default=Aspect.OTHER.value)
    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String(20), nullable=True)  # positive, negative, neutral
    confidence = Column(Integer, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )


class ContentEntity(Base):
    """Entities extracted from content (brand/feature/platform)."""

    __tablename__ = "content_entities"
    __table_args__ = (
        Index("idx_content_entities_target", "content_type", "content_id"),
        Index("idx_content_entities_entity", "entity", "entity_type"),
    )

    id = Column(BigInteger, Sequence("content_entities_id_seq"), primary_key=True)
    content_type = Column(
        SQLEnum(
            ContentType,
            name="content_type",
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    content_id = Column(BigInteger, nullable=False)
    entity = Column(String(128), nullable=False)
    entity_type = Column(String(32), nullable=False, default=EntityType.OTHER.value)
    count = Column(Integer, nullable=False, default=1)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

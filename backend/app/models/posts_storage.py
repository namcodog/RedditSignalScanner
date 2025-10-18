"""
冷热分层存储模型
- PostRaw: 冷库，增量累积，90天滚动窗口
- PostHot: 热缓存，覆盖式刷新，24-72小时TTL
"""
from datetime import datetime, timezone

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    Sequence,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all models in posts_storage"""



class PostRaw(Base):
    """
    冷库：增量累积，保留90天滚动窗口
    用于算法训练、趋势分析、回测
    """

    __tablename__ = "posts_raw"

    # 主键（复合主键在 __table_args__ 中定义）
    id = Column(
        BigInteger,
        Sequence("posts_raw_id_seq"),
        nullable=True,
    )  # 自增 ID，但不是主键，可为空
    source = Column(String(50), nullable=False, default="reddit")
    source_post_id = Column(String(100), nullable=False)
    version = Column(Integer, nullable=False, default=1)

    # 时间戳
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    fetched_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    valid_from = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    valid_to = Column(TIMESTAMP(timezone=True), default=datetime(9999, 12, 31))
    is_current = Column(Boolean, nullable=False, default=True)

    # 作者信息
    author_id = Column(String(100))
    author_name = Column(String(100))

    # 内容
    title = Column(Text, nullable=False)
    body = Column(Text)
    body_norm = Column(Text)  # 由触发器自动填充
    text_norm_hash = Column(UUID(as_uuid=True))  # 由触发器自动填充

    # 元数据
    url = Column(Text)
    subreddit = Column(String(100), nullable=False)
    score = Column(Integer, default=0)
    num_comments = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)
    edit_count = Column(Integer, default=0)
    lang = Column(String(10))

    # JSONB 元数据（注意：metadata 是 SQLAlchemy 保留字，使用 name="metadata"）
    extra_data = Column("metadata", JSONB)

    # 约束
    __table_args__ = (
        PrimaryKeyConstraint(
            "source", "source_post_id", "version", name="pk_posts_raw"
        ),
        CheckConstraint("version > 0", name="ck_posts_raw_version_positive"),
        CheckConstraint(
            "valid_from < valid_to OR valid_to = '9999-12-31'::TIMESTAMP",
            name="ck_posts_raw_valid_period",
        ),
        Index("idx_posts_raw_created_at", "created_at"),
        Index("idx_posts_raw_fetched_at", "fetched_at"),
        Index("idx_posts_raw_subreddit", "subreddit", "created_at"),
        Index("idx_posts_raw_text_hash", "text_norm_hash"),
        Index("idx_posts_raw_source_post_id", "source", "source_post_id"),
        Index(
            "idx_posts_raw_current",
            "source",
            "source_post_id",
            "is_current",
            postgresql_where=(is_current == True),
        ),
        Index("idx_posts_raw_metadata_gin", "metadata", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<PostRaw(source={self.source}, post_id={self.source_post_id}, version={self.version}, subreddit={self.subreddit})>"


class PostHot(Base):
    """
    热缓存：覆盖式刷新，保留24-72小时
    用于实时分析、快报、看板
    """

    __tablename__ = "posts_hot"

    # 主键
    source = Column(String(50), nullable=False, default="reddit")
    source_post_id = Column(String(100), nullable=False)

    # 时间戳
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    cached_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)

    # 内容（简化版）
    title = Column(Text, nullable=False)
    body = Column(Text)
    subreddit = Column(String(100), nullable=False)
    score = Column(Integer, default=0)
    num_comments = Column(Integer, default=0)

    # 元数据
    extra_data = Column("metadata", JSONB)

    # 约束
    __table_args__ = (
        PrimaryKeyConstraint("source", "source_post_id", name="pk_posts_hot"),
        Index("idx_posts_hot_expires_at", "expires_at"),
        Index("idx_posts_hot_subreddit", "subreddit", "created_at"),
        Index("idx_posts_hot_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<PostHot(source={self.source}, post_id={self.source_post_id}, subreddit={self.subreddit})>"


class Watermark(Base):
    """
    水位线：记录每个社区的最后抓取位置
    用于增量抓取
    """

    __tablename__ = "community_watermarks"

    # 主键
    community_name = Column(String(100), primary_key=True)

    # 水位线
    last_seen_post_id = Column(String(100))
    last_seen_created_at = Column(TIMESTAMP(timezone=True))

    # 统计
    total_posts_fetched = Column(Integer, default=0)
    dedup_rate = Column(Numeric(5, 2))  # 去重率（%）
    last_crawled_at = Column(TIMESTAMP(timezone=True))

    # 元数据
    extra_data = Column("metadata", JSONB)

    def __repr__(self) -> str:
        return f"<Watermark(community={self.community_name}, last_seen={self.last_seen_created_at})>"


# 导出
__all__ = ["PostRaw", "PostHot", "Watermark"]

from __future__ import annotations

from typing import Optional, Literal

from pydantic import Field

from app.schemas.base import ORMModel
from app.schemas.hotpost_signal import SourceScopeId


SearchMode = Literal["listing", "search"]
ListingSort = Literal["hot", "new", "rising", "top"]
TimeFilter = Literal["day", "week", "month"]


class SourceScope(ORMModel):
    source_scope_id: SourceScopeId
    title: str
    description: str
    subreddits: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    topic_packs: list["TopicPack"] = Field(default_factory=list)


class TopicPack(ORMModel):
    topic_pack_id: str
    title: str
    description: str
    target_share: int
    subreddits: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)


class RedditSearchSpec(ORMModel):
    source_scope_id: SourceScopeId
    topic_pack_id: str
    topic_cluster_id:Optional[ str] = None
    topic_cluster_ids: list[str] = Field(default_factory=list)
    named_topic_ids: list[str] = Field(default_factory=list)
    subreddit: str
    mode: SearchMode
    sort: str
    time_filter: TimeFilter
    query:Optional[ str] = None
    listing_source: str
    primary_reason: str
    matched_keywords: list[str] = Field(default_factory=list)
    is_experimental_probe: bool = False


class SourceScopeListResponse(ORMModel):
    items: list[SourceScope] = Field(default_factory=list)


class RedditSearchSpecListResponse(ORMModel):
    items: list[RedditSearchSpec] = Field(default_factory=list)


__all__ = [
    "RedditSearchSpec",
    "RedditSearchSpecListResponse",
    "SourceScope",
    "SourceScopeListResponse",
    "TopicPack",
]

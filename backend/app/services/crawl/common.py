"""
共享的数据类和工具类，避免循环导入
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


@dataclass
class Submission:
    """Reddit 帖子数据类"""
    id: str
    title: str
    selftext: str
    score: int
    num_comments: int
    created_utc: float
    subreddit: str
    author: str
    url: str
    permalink: str

    @staticmethod
    def from_praw_post(post_dict: Dict[str, Any]) -> "Submission":
        """从 PRAW 返回的字典创建 Submission"""
        created_utc_raw = post_dict.get("created_utc")
        if isinstance(created_utc_raw, datetime):
            created_utc = created_utc_raw.timestamp()
        else:
            created_utc = float(created_utc_raw or 0.0)

        return Submission(
            id=str(post_dict.get("id", "")),
            title=str(post_dict.get("title", "")),
            selftext=str(post_dict.get("selftext", "")),
            score=int(post_dict.get("score", 0)),
            num_comments=int(post_dict.get("num_comments", 0)),
            created_utc=created_utc,
            subreddit=str(post_dict.get("subreddit", "")),
            author=str(post_dict.get("author", "unknown")),
            url=str(post_dict.get("url", "")),
            permalink=str(post_dict.get("permalink", "")),
        )

    @staticmethod
    def from_reddit_post(post: Any) -> "Submission":
        """从 RedditPost 对象创建 Submission"""
        return Submission(
            id=post.id,
            title=post.title,
            selftext=post.selftext or "",
            score=post.score,
            num_comments=post.num_comments,
            created_utc=post.created_utc,
            subreddit=post.subreddit,
            author=post.author,
            url=post.url,
            permalink=post.permalink,
        )


class JSONLWriter:
    """流式 JSONL 写入器"""
    
    def __init__(self, path: Path, stream: bool = False):
        self.path = path
        self.stream = stream
        self._file = None
        if stream:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self.path, "w", encoding="utf-8")
    
    def append(self, submission: Submission):
        """追加一条记录"""
        line = asdict(submission)
        if self.stream and self._file:
            self._file.write(json.dumps(line, ensure_ascii=False) + "\n")
            self._file.flush()
    
    def write_all(self, submissions: list[Submission]):
        """批量写入（非流式模式）"""
        if not self.stream:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                for sub in submissions:
                    f.write(json.dumps(asdict(sub), ensure_ascii=False) + "\n")
    
    def close(self):
        """关闭文件"""
        if self._file:
            self._file.close()
            self._file = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


import json


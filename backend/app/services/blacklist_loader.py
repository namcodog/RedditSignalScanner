"""
黑名单加载与应用服务

负责从 config/community_blacklist.yaml 加载黑名单配置，
并提供过滤/降权逻辑供抓取和分析模块使用。
"""
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class BlacklistConfig:
    """黑名单配置类"""

    def __init__(self, config_path: str = "config/community_blacklist.yaml") -> None:
        self.config_path = Path(config_path)
        self.blacklisted_communities: set[str] = set()
        self.downranked_communities: dict[str, dict[str, Any]] = {}
        self.downrank_keywords: dict[str, dict[str, Any]] = {}
        self.filter_keywords: set[str] = set()
        self.whitelist_keywords: dict[str, dict[str, Any]] = {}
        self.blacklisted_authors: dict[str, dict[str, Any]] = {}
        self.filter_patterns: list[dict[str, Any]] = []
        self.author_auto_rules: dict[str, Any] = {}
        self.contextual_filters: list[dict[str, Any]] = []
        self.semantic_expansion_stopwords: set[str] = set()

        self._load_config()

    def _load_config(self) -> None:
        """加载黑名单配置文件"""
        if not self.config_path.exists():
            logger.warning(f"黑名单配置文件不存在: {self.config_path}")
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            # 全局黑名单（新结构）
            for item in config.get("global_blacklist", []) or []:
                if isinstance(item, str):
                    self.blacklisted_communities.add(item.strip().lower())
                elif isinstance(item, dict) and item.get("name"):
                    self.blacklisted_communities.add(str(item["name"]).strip().lower())

            # 上下文过滤组（新结构）
            self.contextual_filters = config.get("contextual_filters", []) or []
            
            # Semantic Expansion Stopwords
            for w in config.get("semantic_expansion_stopwords", []) or []:
                if w and isinstance(w, str):
                    self.semantic_expansion_stopwords.add(w.strip().lower())

            # 加载降权社区
            for item in config.get("downranked_communities", []):
                self.downranked_communities[item["name"]] = {
                    "reason": item.get("reason", ""),
                    "downrank_factor": item.get("downrank_factor", 0.5),
                }

            # 加载降权关键词
            for item in config.get("downrank_keywords", []):
                keyword = item["keyword"].lower()
                self.downrank_keywords[keyword] = {
                    "weight": item.get("weight", -0.3),
                    "reason": item.get("reason", ""),
                }

            # 加载过滤关键词
            for item in config.get("filter_keywords", []):
                self.filter_keywords.add(item["keyword"].lower())

            # 加载白名单关键词
            for item in config.get("whitelist_keywords", []):
                keyword = item["keyword"].lower()
                self.whitelist_keywords[keyword] = {
                    "boost": item.get("boost", 0.3),
                    "reason": item.get("reason", ""),
                }

            # 作者黑名单
            for item in config.get("blacklisted_authors", []) or []:
                username = str(item.get("username") or "").strip().lower()
                if username:
                    self.blacklisted_authors[username] = {"reason": item.get("reason", "")}

            # 作者自动规则
            self.author_auto_rules = config.get("author_auto_blacklist_rules", {}) or {}

            # 正则模式过滤
            for item in config.get("filter_patterns", []) or []:
                try:
                    pattern = str(item.get("pattern") or "").strip()
                    if pattern:
                        self.filter_patterns.append(
                            {"pattern": pattern, "reason": item.get("reason", "")}
                        )
                except Exception:
                    continue

            logger.info(
                f"✅ 黑名单配置加载成功: "
                f"{len(self.blacklisted_communities)} 个黑名单社区, "
                f"{len(self.downranked_communities)} 个降权社区, "
                f"{len(self.downrank_keywords)} 个降权关键词, "
                f"{len(self.filter_keywords)} 个过滤关键词, "
                f"{len(self.blacklisted_authors)} 个黑名单作者, "
                f"{len(self.filter_patterns)} 条正则模式, "
                f"{len(self.contextual_filters)} 个上下文过滤组"
            )

        except Exception as e:
            logger.error(f"❌ 加载黑名单配置失败: {e}")

    def is_community_blacklisted(self, community_name: str) -> bool:
        """检查社区是否在黑名单中"""
        return community_name.lower() in {
            c.lower() for c in self.blacklisted_communities
        }

    def is_community_downranked(self, community_name: str) -> bool:
        """检查社区是否被降权"""
        return community_name.lower() in {
            c.lower() for c in self.downranked_communities
        }

    def get_community_downrank_factor(self, community_name: str) -> float:
        """获取社区降权系数（1.0 = 无降权）"""
        for name, config in self.downranked_communities.items():
            if name.lower() == community_name.lower():
                factor: Any = config["downrank_factor"]
                return float(factor)
        return 1.0

    def should_filter_post(self, title: str, content: str = "") -> bool:
        """检查帖子是否应该被过滤（包含过滤关键词）"""
        text = f"{title} {content}".lower()
        return any(keyword in text for keyword in self.filter_keywords)

    def calculate_keyword_adjustment(self, title: str, content: str = "") -> float:
        """
        计算关键词调整分数

        返回值:
            - 正数: 提升分数（白名单关键词）
            - 负数: 降低分数（降权关键词）
            - 0: 无调整
        """
        text = f"{title} {content}".lower()
        adjustment = 0.0

        # 检查白名单关键词（优先级更高）
        for keyword, config in self.whitelist_keywords.items():
            if keyword in text:
                adjustment += config["boost"]
                logger.debug(f"白名单关键词命中: {keyword} (+{config['boost']})")

        # 检查降权关键词
        for keyword, config in self.downrank_keywords.items():
            if keyword in text:
                adjustment += config["weight"]  # weight 是负数
                logger.debug(f"降权关键词命中: {keyword} ({config['weight']})")

        return adjustment

    def get_blacklist_reason(self, community_name: str) -> str | None:
        """获取社区被列入黑名单的原因"""
        # 这里需要从配置文件中查找原因
        # 简化实现：返回通用原因
        if self.is_community_blacklisted(community_name):
            return "blacklisted"
        if self.is_community_downranked(community_name):
            return self.downranked_communities.get(community_name.lower(), {}).get(
                "reason"
            )
        return None

    def is_author_blacklisted(self, username: str) -> bool:
        key = (username or "").strip().lower()
        return bool(key) and key in self.blacklisted_authors

    def matches_spam_pattern(self, text: str) -> bool:
        import re

        if not text or not self.filter_patterns:
            return False
        for item in self.filter_patterns:
            pat = item.get("pattern")
            try:
                if pat and re.search(pat, text, flags=re.IGNORECASE):
                    return True
            except re.error:
                continue
        return False


# 全局单例
_blacklist_config: BlacklistConfig | None = None


def get_blacklist_config() -> BlacklistConfig:
    """获取黑名单配置单例"""
    global _blacklist_config
    if _blacklist_config is None:
        _blacklist_config = BlacklistConfig()
    return _blacklist_config


def reload_blacklist_config() -> None:
    """重新加载黑名单配置（用于配置更新后）"""
    global _blacklist_config
    _blacklist_config = BlacklistConfig()
    logger.info("🔄 黑名单配置已重新加载")

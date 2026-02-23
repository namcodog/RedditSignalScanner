"""
黑名单加载器单元测试
"""
import pytest
from pathlib import Path
from unittest.mock import patch
import tempfile
import yaml

from app.services.blacklist_loader import BlacklistConfig


class TestBlacklistLoader:
    """测试 BlacklistConfig 类"""

    def test_is_author_blacklisted(self):
        """测试作者黑名单检查"""
        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config = {
                'blacklisted_communities': [],
                'blacklisted_authors': [
                    {'username': 'AutoModerator', 'reason': 'Bot'},
                    {'username': 'SpamBot123', 'reason': 'Spam'},
                ],
                'filter_patterns': [],
                'filter_keywords': [],
            }
            yaml.dump(config, f)
            f.flush()
            
            loader = BlacklistConfig(f.name)
            
            # 测试黑名单作者
            assert loader.is_author_blacklisted('AutoModerator') is True
            assert loader.is_author_blacklisted('automoderator') is True  # 大小写不敏感
            assert loader.is_author_blacklisted('SpamBot123') is True
            
            # 测试非黑名单作者
            assert loader.is_author_blacklisted('LegitUser') is False
            assert loader.is_author_blacklisted('') is False
            assert loader.is_author_blacklisted(None) is False
            
        Path(f.name).unlink()

    def test_matches_spam_pattern(self):
        """测试正则模式匹配"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config = {
                'blacklisted_communities': [],
                'blacklisted_authors': [],
                'filter_patterns': [
                    {'pattern': r'BTC\s*\d+%', 'reason': 'Crypto scam'},
                    {'pattern': r'telegram', 'reason': 'Spam'},
                ],
                'filter_keywords': [],
            }
            yaml.dump(config, f)
            f.flush()
            
            loader = BlacklistConfig(f.name)
            
            # 测试匹配模式
            assert loader.matches_spam_pattern('BTC 500% profit guaranteed!') is True
            assert loader.matches_spam_pattern('Join my telegram group now') is True
            
            # 测试不匹配模式
            assert loader.matches_spam_pattern('Looking for product recommendations') is False
            assert loader.matches_spam_pattern('Normal discussion about market') is False
            assert loader.matches_spam_pattern('') is False
            
        Path(f.name).unlink()

    def test_load_all_fields(self):
        """测试加载所有新增字段"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config = {
                'blacklisted_communities': [{'name': 'r/spam', 'reason': 'spam'}],
                'blacklisted_authors': [
                    {'username': 'Bot1', 'reason': 'Bot'},
                ],
                'author_auto_blacklist_rules': {
                    'min_posts': 3,
                    'avg_score_below': 1,
                    'spam_hit_rate_above': 0.5,
                },
                'filter_patterns': [
                    {'pattern': r'test\d+', 'reason': 'test'},
                ],
                'filter_keywords': [{'keyword': 'giveaway'}],
            }
            yaml.dump(config, f)
            f.flush()
            
            loader = BlacklistConfig(f.name)
            
            # 验证所有字段都已加载
            assert len(loader.blacklisted_communities) == 1
            assert len(loader.blacklisted_authors) == 1
            assert len(loader.filter_patterns) == 1
            assert len(loader.filter_keywords) == 1
            assert loader.author_auto_rules.get('min_posts') == 3
            
        Path(f.name).unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

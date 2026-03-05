import pytest
import importlib

try:
    from backend.scripts.backfill_community_pool_from_csv_97 import read_communities_from_csv
except (ImportError, ModuleNotFoundError) as exc:
    pytest.skip(str(exc), allow_module_level=True)

from collections import Counter


def test_read_communities_from_csv_uses_97_communities() -> None:
    communities = read_communities_from_csv()

    # 基本数量与格式检查
    assert len(communities) == 97
    names = [c["name"] for c in communities]
    assert all(name.startswith("r/") for name in names)
    assert len(set(names)) == 97

    # 按 tier 分布应符合 48 / 15 / 34
    tiers = Counter(c["tier"] for c in communities)
    assert tiers["high"] == 48
    assert tiers["medium"] == 15
    assert tiers["semantic"] == 34

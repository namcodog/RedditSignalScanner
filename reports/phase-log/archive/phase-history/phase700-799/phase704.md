# phase704

## 本轮完成
- 已开始执行 `hotpost` 本地存储拆桶，不再停留在方案层。

## 代码改动
- 新增拆桶实现：
  - `backend/app/services/hotpost/card_storage_layout.py`
- 更新共享读写入口：
  - `backend/app/services/hotpost/card_payload_store.py`
- 更新前台卡片读取入口：
  - `backend/app/services/hotpost/clues_catalog.py`
- 新增迁移脚本：
  - `backend/scripts/hotpost/migrate_hotpost_storage_layout.py`
- 更新旧润色脚本，避免继续直连单桶旧文件：
  - `backend/scripts/deai_polish.py`

## 测试
- `pytest tests/services/hotpost/test_card_payload_store.py tests/services/hotpost/test_card_storage_layout.py -q`
  - `2 passed`
- `pytest tests/api/test_hotpost_clues.py tests/api/test_hotpost_card_candidates.py -q`
  - `14 passed`

## 数据迁移结果
- 已真实执行迁移脚本：
  - `python backend/scripts/hotpost/migrate_hotpost_storage_layout.py`
- 当前新结构已生成：
  - `backend/data/hotpost/categories.json`
  - `backend/data/hotpost/candidates/*.json`
  - `backend/data/hotpost/releases/latest.json`
  - `backend/data/hotpost/releases/<release_id>/index.json`
  - `backend/data/hotpost/releases/<release_id>/cards/*.json`

## 当前结论
- 上层 payload 合同保持不变，但底层已不再依赖单桶 `hotpost_clues.json`。
- `hotpost_clues.json` 现在只应视为历史/迁移来源，不再继续作为运行时真相源扩张。

## 下一步
- 继续把仍然直连旧文件的零散脚本和测试收口到新布局。
- 然后再接 `snapshot push` 到云端。

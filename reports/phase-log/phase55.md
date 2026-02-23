# phase55：把“抓取SOP + 本地生产DB”贯连成唯一参照（DB Atlas + 配置地图）

## 这次要解决什么
Key 的诉求是“读者一眼就能把数据管道讲清楚”：抓取怎么跑、数据落到哪些表、字段口径怎么对齐、ID 怎么串起来、YAML 开关在哪里。

之前的问题是：SOP 里已经在讲“系统口径”，但缺少一个能反映 **本地生产库真实 schema** 的“最终账本”，并且存在引用的 DB Atlas 文件缺失。

## 做了什么

### 1) 落地 DB Atlas（以本地生产库为准）
- 新增脚本：`scripts/generate_db_atlas.py`
  - 读取指定 DB（默认 `postgresql://postgres:postgres@localhost:5432/reddit_signal_scanner`）
  - 自动导出：表清单、字段、约束、索引、ID 字段速查、JSON 字段速查
  - 写入到：`docs/2025-12-14-database-architecture-atlas.md`
- 生成产物：`docs/2025-12-14-database-architecture-atlas.md`
  - 包含 `alembic_version`，用来钉住“这一版库到底长啥样”

### 2) SOP 明确“DB 是最终账本 + 配置地图在哪里”
- 更新 `docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md`
  - 增加“读这份 SOP 的前提”：DB 真实结构以 DB Atlas 为准
  - 增加“配置文件地图”：把抓取相关 YAML/关键 env 开关集中列出来

### 3) 文档导航补齐入口
- 更新 `docs/2025-10-10-文档阅读指南.md`：把 DB Atlas 加进 docs 结构树，避免新人找不到

## 验收（本地操作）

### 1) 确认 DB 版本（本地生产库）
```bash
psql "postgresql://postgres:postgres@localhost:5432/reddit_signal_scanner" -c "SELECT version_num FROM alembic_version;"
```

### 2) 重新生成 DB Atlas（覆盖写）
```bash
python scripts/generate_db_atlas.py \
  --database-url "postgresql://postgres:postgres@localhost:5432/reddit_signal_scanner" \
  --out "docs/2025-12-14-database-architecture-atlas.md"
```

## 对外口径（给 Key / 新同学）
- **SOP 负责讲“流程 + 口径 + 谁能写哪些表/字段”。**
- **DB Atlas 负责讲“库里真实 schema 长啥样（最终账本）”。**
- **YAML/开关统一在一个地方列出来，避免到处找参数。**


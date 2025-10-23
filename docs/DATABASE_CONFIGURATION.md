# 数据库配置规范

## 📋 问题背景

在开发过程中发现数据库配置混乱，导致以下问题：

1. **数据库名称不一致**：
   - `.env` 文件中配置：`reddit_signal_scanner`
   - 部分脚本/查询使用：`reddit_scanner`
   - 导致数据查询失败，找不到数据

2. **多个数据库并存**：
   - `reddit_scanner`：旧数据库，可能包含过时数据
   - `reddit_signal_scanner`：当前使用的数据库

## ✅ 标准配置

### 数据库名称

**唯一标准数据库名称**：`reddit_signal_scanner`

### 环境变量配置

**文件**：`backend/.env`

```bash
# 数据库配置（标准）
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner
```

### 连接参数

- **Host**: `localhost`
- **Port**: `5432`
- **User**: `postgres`
- **Password**: `postgres`
- **Database**: `reddit_signal_scanner` ⚠️ **必须使用此名称**

## 🔧 修复步骤

### 步骤 1：检查当前数据库

```bash
# 连接到 PostgreSQL
psql -U postgres -h localhost

# 列出所有数据库
\l

# 检查两个数据库的数据
\c reddit_scanner
SELECT COUNT(*) FROM tasks;

\c reddit_signal_scanner
SELECT COUNT(*) FROM tasks;
```

### 步骤 2：迁移数据（如果需要）

如果 `reddit_scanner` 中有重要数据，需要迁移到 `reddit_signal_scanner`：

```bash
# 导出旧数据库
pg_dump -U postgres -h localhost reddit_scanner > /tmp/reddit_scanner_backup.sql

# 导入到新数据库
psql -U postgres -h localhost reddit_signal_scanner < /tmp/reddit_scanner_backup.sql
```

### 步骤 3：删除旧数据库（可选）

```bash
# 连接到 PostgreSQL
psql -U postgres -h localhost

# 删除旧数据库
DROP DATABASE reddit_scanner;
```

### 步骤 4：验证配置

```bash
# 运行测试脚本
cd backend
source ../venv/bin/activate
python << 'EOF'
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def verify_db():
    db_url = os.getenv("DATABASE_URL")
    print(f"📊 DATABASE_URL: {db_url}")
    
    # 提取数据库名称
    db_name = db_url.split('/')[-1]
    print(f"📊 数据库名称: {db_name}")
    
    # 连接测试
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database=db_name
    )
    
    # 查询数据
    count = await conn.fetchval("SELECT COUNT(*) FROM tasks")
    print(f"✅ 连接成功！Tasks 表总数: {count}")
    
    await conn.close()

asyncio.run(verify_db())
EOF
```

## 📝 开发规范

### 1. 所有数据库查询必须使用环境变量

❌ **错误示例**：

```python
conn = await asyncpg.connect(
    host='localhost',
    port=5432,
    user='postgres',
    password='postgres',
    database='reddit_scanner'  # 硬编码数据库名称！
)
```

✅ **正确示例**：

```python
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")

# 方法 1：使用完整 URL
engine = create_async_engine(db_url)

# 方法 2：解析 URL
from urllib.parse import urlparse
parsed = urlparse(db_url)
conn = await asyncpg.connect(
    host=parsed.hostname,
    port=parsed.port,
    user=parsed.username,
    password=parsed.password,
    database=parsed.path[1:]  # 去掉开头的 '/'
)
```

### 2. 测试脚本必须加载 .env 文件

```python
from dotenv import load_dotenv
load_dotenv()  # 必须在导入其他模块之前调用
```

### 3. Makefile 命令必须导出环境变量

```makefile
db-query:
	cd backend && \
	source ../venv/bin/activate && \
	export $(cat .env | grep -v '^#' | xargs) && \
	python scripts/query_db.py
```

## 🚨 常见错误

### 错误 1：数据库不存在

```
asyncpg.exceptions.InvalidCatalogNameError: database "reddit_scanner" does not exist
```

**解决方案**：检查 `.env` 文件，确保使用正确的数据库名称

### 错误 2：找不到数据

```
📊 Tasks 表总数: 0
```

**解决方案**：检查是否连接到了正确的数据库

### 错误 3：环境变量未加载

```
DATABASE_URL: None
```

**解决方案**：确保调用了 `load_dotenv()`

## 📚 相关文档

- [Alembic 迁移指南](../backend/alembic/README.md)
- [数据库 Schema](../backend/app/models/)
- [环境变量配置](.env.example)


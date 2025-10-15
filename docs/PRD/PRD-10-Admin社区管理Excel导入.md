# PRD-10: Admin 社区管理 - Excel 批量导入

**创建日期**: 2025-10-14  
**优先级**: P1（MVP 必需）  
**预计工时**: 4-6 小时  
**状态**: 📝 待实现

---

## 1. 概述

### 1.1 背景

**当前问题**：
- ❌ 添加社区需要修改 JSON 文件 + Git 提交
- ❌ 运营人员需要技术背景
- ❌ 流程繁琐，耗时长（30分钟 - 2小时）
- ❌ 容易出错（JSON 格式错误）

**解决方案**：
- ✅ Admin 后台提供 Excel 上传功能
- ✅ 运营人员填写 Excel 模板
- ✅ 系统自动验证 + 导入
- ✅ 5-10分钟完成批量添加

### 1.2 核心目标

- ✅ 运营人员无需技术背景即可添加社区
- ✅ 支持批量添加（一次上传 10-100 个社区）
- ✅ 自动验证数据格式与完整性
- ✅ 即时生效，无需重启服务
- ✅ 提供操作日志与回滚功能

---

## 2. Excel 模板设计

### 2.1 模板字段

| 列名 | 字段名 | 类型 | 必填 | 说明 | 示例 |
|------|--------|------|------|------|------|
| A | name | 文本 | ✅ | 社区名称（带 r/ 前缀） | r/startups |
| B | tier | 文本 | ✅ | 社区层级（seed/gold/silver/admin） | gold |
| C | categories | 文本 | ✅ | 分类标签（逗号分隔） | startup,business,founder |
| D | description_keywords | 文本 | ✅ | 描述关键词（逗号分隔） | startup,founder,product,launch |
| E | daily_posts | 数字 | ❌ | 日均帖子数 | 180 |
| F | avg_comment_length | 数字 | ❌ | 平均评论长度 | 72 |
| G | quality_score | 数字 | ❌ | 质量评分（0.0-1.0） | 0.95 |
| H | priority | 文本 | ❌ | 爬取优先级（high/medium/low） | high |

### 2.2 Excel 模板示例

```
| name          | tier  | categories              | description_keywords           | daily_posts | avg_comment_length | quality_score | priority |
|---------------|-------|-------------------------|--------------------------------|-------------|-------------------|---------------|----------|
| r/startups    | gold  | startup,business,founder| startup,founder,product,launch | 180         | 72                | 0.95          | high     |
| r/Entrepreneur| gold  | business,marketing,sales| marketing,sales,pitch,growth   | 150         | 64                | 0.88          | high     |
| r/SaaS        | silver| saas,pricing,metrics    | subscription,pricing,mrr       | 65          | 84                | 0.80          | medium   |
```

### 2.3 验证规则

**必填字段验证**：
- `name`: 必须以 `r/` 开头，长度 3-100 字符
- `tier`: 必须是 `seed`, `gold`, `silver`, `admin` 之一
- `categories`: 至少 1 个，最多 10 个标签
- `description_keywords`: 至少 1 个，最多 20 个关键词

**可选字段验证**：
- `daily_posts`: 0-10000 之间的整数
- `avg_comment_length`: 0-1000 之间的整数
- `quality_score`: 0.0-1.0 之间的小数
- `priority`: `high`, `medium`, `low` 之一

**业务规则验证**：
- 社区名称不能重复（与数据库中已有社区对比）
- 同一 Excel 中不能有重复的社区名称

---

## 3. API 设计

### 3.1 下载模板

**端点**: `GET /api/admin/communities/template`

**响应**:
```
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="community_template.xlsx"

[Excel 文件二进制数据]
```

**说明**：
- 返回预填充的 Excel 模板
- 包含 3 行示例数据
- 包含字段说明（第一行注释）

---

### 3.2 上传并导入

**端点**: `POST /api/admin/communities/import`

**请求**:
```
Content-Type: multipart/form-data

file: [Excel 文件]
dry_run: false  # true=仅验证，false=验证并导入
```

**响应（验证成功）**:
```json
{
  "status": "success",
  "summary": {
    "total": 10,
    "valid": 10,
    "invalid": 0,
    "duplicates": 0,
    "imported": 10
  },
  "communities": [
    {
      "name": "r/startups",
      "tier": "gold",
      "status": "imported"
    }
  ]
}
```

**响应（验证失败）**:
```json
{
  "status": "error",
  "summary": {
    "total": 10,
    "valid": 8,
    "invalid": 2,
    "duplicates": 0,
    "imported": 0
  },
  "errors": [
    {
      "row": 3,
      "field": "name",
      "value": "startups",
      "error": "社区名称必须以 r/ 开头"
    },
    {
      "row": 5,
      "field": "tier",
      "value": "premium",
      "error": "tier 必须是 seed/gold/silver/admin 之一"
    }
  ]
}
```

---

### 3.3 查看导入历史

**端点**: `GET /api/admin/communities/import-history`

**响应**:
```json
{
  "imports": [
    {
      "id": 1,
      "filename": "communities_2025-10-14.xlsx",
      "uploaded_by": "admin@example.com",
      "uploaded_at": "2025-10-14T10:30:00Z",
      "total": 10,
      "imported": 10,
      "status": "success"
    }
  ]
}
```

---

## 4. 前端设计

### 4.1 页面布局

```
┌─────────────────────────────────────────────┐
│  Admin 后台 > 社区管理 > 批量导入            │
├─────────────────────────────────────────────┤
│                                             │
│  📥 批量导入社区                             │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ 步骤 1：下载模板                     │   │
│  │                                     │   │
│  │ [下载 Excel 模板] 按钮               │   │
│  │                                     │   │
│  │ 💡 提示：请按照模板格式填写社区信息   │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ 步骤 2：上传 Excel 文件              │   │
│  │                                     │   │
│  │ [选择文件] 按钮                      │   │
│  │                                     │   │
│  │ ☑️ 仅验证（不导入）                  │   │
│  │                                     │   │
│  │ [上传并导入] 按钮                    │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ 导入结果                             │   │
│  │                                     │   │
│  │ ✅ 成功导入 10 个社区                │   │
│  │ ❌ 2 个错误                          │   │
│  │                                     │   │
│  │ 错误详情：                           │   │
│  │ - 第 3 行：name 必须以 r/ 开头       │   │
│  │ - 第 5 行：tier 无效                 │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ 导入历史                             │   │
│  │                                     │   │
│  │ 2025-10-14 10:30 | 10个社区 | 成功  │   │
│  │ 2025-10-13 15:20 | 5个社区  | 成功  │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

---

## 5. 后端实现

### 5.1 核心代码结构

```python
# backend/app/api/routes/admin_communities.py

from fastapi import APIRouter, UploadFile, File
from app.services.community_import_service import CommunityImportService

router = APIRouter()

@router.get("/template")
async def download_template():
    """下载 Excel 模板"""
    return CommunityImportService.generate_template()

@router.post("/import")
async def import_communities(
    file: UploadFile = File(...),
    dry_run: bool = False
):
    """上传并导入社区"""
    service = CommunityImportService()
    result = await service.import_from_excel(file, dry_run=dry_run)
    return result

@router.get("/import-history")
async def get_import_history():
    """查看导入历史"""
    service = CommunityImportService()
    return await service.get_import_history()
```

### 5.2 导入服务

```python
# backend/app/services/community_import_service.py

import pandas as pd
from typing import List, Dict, Any
from app.models.community_pool import CommunityPool

class CommunityImportService:
    
    @staticmethod
    def generate_template() -> bytes:
        """生成 Excel 模板"""
        df = pd.DataFrame([
            {
                "name": "r/startups",
                "tier": "gold",
                "categories": "startup,business,founder",
                "description_keywords": "startup,founder,product,launch",
                "daily_posts": 180,
                "avg_comment_length": 72,
                "quality_score": 0.95,
                "priority": "high"
            }
        ])
        
        # 转换为 Excel
        output = BytesIO()
        df.to_excel(output, index=False)
        return output.getvalue()
    
    async def import_from_excel(
        self, 
        file: UploadFile, 
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """从 Excel 导入社区"""
        
        # 1. 读取 Excel
        df = pd.read_excel(file.file)
        
        # 2. 验证数据
        errors = self._validate_dataframe(df)
        if errors:
            return {
                "status": "error",
                "errors": errors
            }
        
        # 3. 导入数据库（如果不是 dry_run）
        if not dry_run:
            imported = await self._import_to_database(df)
            return {
                "status": "success",
                "imported": imported
            }
        
        return {
            "status": "validated",
            "total": len(df)
        }
    
    def _validate_dataframe(self, df: pd.DataFrame) -> List[Dict]:
        """验证 DataFrame"""
        errors = []
        
        for idx, row in df.iterrows():
            # 验证 name
            if not row['name'].startswith('r/'):
                errors.append({
                    "row": idx + 2,  # Excel 行号（从 2 开始）
                    "field": "name",
                    "value": row['name'],
                    "error": "社区名称必须以 r/ 开头"
                })
            
            # 验证 tier
            if row['tier'] not in ['seed', 'gold', 'silver', 'admin']:
                errors.append({
                    "row": idx + 2,
                    "field": "tier",
                    "value": row['tier'],
                    "error": "tier 必须是 seed/gold/silver/admin 之一"
                })
        
        return errors
    
    async def _import_to_database(self, df: pd.DataFrame) -> int:
        """导入到数据库"""
        imported = 0
        
        for _, row in df.iterrows():
            community = CommunityPool(
                name=row['name'],
                tier=row['tier'],
                categories=row['categories'].split(','),
                description_keywords=row['description_keywords'].split(','),
                daily_posts=row.get('daily_posts', 0),
                avg_comment_length=row.get('avg_comment_length', 0),
                quality_score=row.get('quality_score', 0.5),
            )
            
            # 保存到数据库
            await community.save()
            imported += 1
        
        return imported
```

---

## 6. 实施计划

### 6.1 Day 15 实施（4-6 小时）

**上午（2-3 小时）- 后端**
1. ✅ 安装依赖：`pip install pandas openpyxl`
2. ✅ 实现 `CommunityImportService`
3. ✅ 实现 3 个 API 端点
4. ✅ 单元测试

**下午（2-3 小时）- 前端**
1. ✅ 创建 Admin 社区管理页面
2. ✅ 实现文件上传组件
3. ✅ 实现结果展示
4. ✅ 集成测试

---

## 7. 验收标准

### 7.1 功能验收

- [ ] 可以下载 Excel 模板
- [ ] 可以上传 Excel 文件
- [ ] 自动验证数据格式
- [ ] 验证失败时显示详细错误
- [ ] 验证成功后导入数据库
- [ ] 可以查看导入历史

### 7.2 用户体验验收

- [ ] 运营人员无需技术背景即可操作
- [ ] 5-10 分钟完成批量添加
- [ ] 错误提示清晰易懂
- [ ] 支持批量添加（10-100 个社区）

---

## 8. 优势总结

| 方面 | Git 提交方式 | Excel 上传方式 |
|------|-------------|---------------|
| **技术门槛** | ❌ 需要 Git 知识 | ✅ 无需技术背景 |
| **操作时间** | ❌ 30分钟 - 2小时 | ✅ 5-10分钟 |
| **批量添加** | ⚠️  手动编辑 JSON | ✅ Excel 批量填写 |
| **即时生效** | ❌ 需要重启服务 | ✅ 立即生效 |
| **错误处理** | ❌ JSON 格式错误难排查 | ✅ 自动验证 + 详细提示 |
| **操作日志** | ⚠️  Git 历史 | ✅ 导入历史记录 |

---

**结论**：✅ **Excel 上传方式明显优于 Git 提交方式，强烈推荐实现！**


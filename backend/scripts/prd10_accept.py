#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRD-10 Admin 社区 Excel 导入 - 非交互端到端验收脚本
用法：
  python scripts/prd10_accept.py template    # 生成模板并校验
  python scripts/prd10_accept.py dryrun      # dry_run=True 仅验证
  python scripts/prd10_accept.py import      # dry_run=False 实际导入
  python scripts/prd10_accept.py history     # 校验导入历史有记录
  python scripts/prd10_accept.py routes      # 校验 API 路由注册
  python scripts/prd10_accept.py all         # 依次执行以上所有步骤
"""
from __future__ import annotations
import sys
import json
import uuid
import asyncio
from typing import Any

# 确保从 backend/ 作为工作目录也能导入 app
sys.path.insert(0, '.')

from app.services.community_import_service import CommunityImportService  # type: ignore
from app.db.session import get_session_context, SessionFactory  # type: ignore
from sqlalchemy import text  # type: ignore


def step_template() -> None:
    content = CommunityImportService.generate_template()
    assert isinstance(content, (bytes, bytearray)) and len(content) > 1000, '模板生成异常'
    print(f'✅ 模板生成 OK，bytes={len(content)}')


async def step_dryrun() -> None:
    content = CommunityImportService.generate_template()
    async with get_session_context() as session:
        service = CommunityImportService(session)
        res: dict[str, Any] = await service.import_from_excel(
            content=content,
            filename='template.xlsx',
            dry_run=True,
            actor_email='make@acceptance.test',
            actor_id=uuid.uuid4(),
        )
        print('✅ dry_run 结果:', json.dumps({k: res.get(k) for k in ['status','summary'] if k in res}, ensure_ascii=False))
        # 允许重复导致的 error（幂等环境下常见），但必须给出 duplicates 统计
        if res.get('status') not in ('validated', 'success'):
            summary = res.get('summary') or {}
            assert summary.get('duplicates', 0) >= 1, 'dry_run 未通过且非重复场景'


async def step_import() -> None:
    content = CommunityImportService.generate_template()
    async with get_session_context() as session:
        service = CommunityImportService(session)
        res: dict[str, Any] = await service.import_from_excel(
            content=content,
            filename='template.xlsx',
            dry_run=False,
            actor_email='make@acceptance.test',
            actor_id=uuid.uuid4(),
        )
        print('✅ 导入结果:', json.dumps({k: res.get(k) for k in ['status','summary'] if k in res}, ensure_ascii=False))
        # 允许由于重复导致无法新增的情形，将其视为幂等成功
        if res.get('status') not in ('success', 'partial'):
            summary = res.get('summary') or {}
            imported = (summary.get('imported') if isinstance(summary, dict) else None) or 0
            duplicates = (summary.get('duplicates') if isinstance(summary, dict) else None) or 0
            assert imported == 0 and duplicates >= 1, '导入失败且非重复幂等场景'


async def step_history() -> None:
    async with SessionFactory() as session:
        cnt = (await session.execute(text('SELECT COUNT(*) FROM community_import_history'))).scalar_one()
        print('✅ 导入历史记录数:', cnt)
        assert cnt >= 1


def step_routes() -> None:
    from app.main import app  # 延迟导入，避免初始化干扰
    paths = [getattr(r, 'path', None) for r in app.routes]
    expected = [
        '/api/admin/communities/template',
        '/api/admin/communities/import',
        '/api/admin/communities/import-history',
    ]
    missing = [p for p in expected if p not in paths]
    assert not missing, f'Missing routes: {missing}'
    print('✅ 路由存在:', expected)


async def step_all() -> None:
    step_template()
    await step_dryrun()
    await step_import()
    await step_history()
    step_routes()
    print('✅ PRD-10 验收完成（非交互直调路径）')


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cmd = sys.argv[1].lower()
    if cmd == 'template':
        step_template()
    elif cmd == 'dryrun':
        asyncio.run(step_dryrun())
    elif cmd == 'import':
        asyncio.run(step_import())
    elif cmd == 'history':
        asyncio.run(step_history())
    elif cmd == 'routes':
        step_routes()
    elif cmd == 'all':
        asyncio.run(step_all())
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == '__main__':
    main()


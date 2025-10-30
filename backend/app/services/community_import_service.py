from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, List, Optional, Sequence, Tuple

import xlrd  # type: ignore[import-untyped]
import xlsxwriter  # type: ignore[import-untyped]
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_import import CommunityImportHistory
from app.models.community_pool import CommunityPool
from app.models.user import User

logger = logging.getLogger(__name__)


RowRecord = Tuple[int, Dict[str, Any]]


@dataclass(slots=True)
class ParsedCommunityRow:
    row_number: int
    name: str
    tier: str
    categories: List[str]
    description_keywords: List[str]
    daily_posts: Optional[int]
    avg_comment_length: Optional[int]
    quality_score: Optional[float]
    priority: Optional[str]


class CommunityImportService:
    """Excel-based community import aligned with PRD-10 requirements."""

    REQUIRED_COLUMNS: Sequence[str] = (
        "name",
        "tier",
        "categories",
        "description_keywords",
    )
    OPTIONAL_COLUMNS: Sequence[str] = (
        "daily_posts",
        "avg_comment_length",
        "quality_score",
        "priority",
    )
    VALID_TIERS = {"seed", "gold", "silver", "admin"}
    VALID_PRIORITIES = {"high", "medium", "low"}

    COLUMN_HINTS: Dict[str, str] = {
        "name": "社区名称，必须以 r/ 开头，长度 3-100",
        "tier": "社区层级：seed/gold/silver/admin",
        "categories": "分类标签，1-10 个，使用英文逗号分隔",
        "description_keywords": "描述关键词，1-20 个，使用英文逗号分隔",
        "daily_posts": "可选：日均帖子数，0-10000 的整数",
        "avg_comment_length": "可选：平均评论长度，0-1000 的整数",
        "quality_score": "可选：质量评分，0.0-1.0 的小数",
        "priority": "可选：爬取优先级 high/medium/low，默认 medium",
    }

    # 支持常见中文/别名表头，便于直接导入“社区筛选.xlsx”
    # 仅用于列名匹配，不改变字段语义
    HEADER_ALIASES: Dict[str, list[str]] = {
        "name": ["name", "社区", "社区名", "社区名称", "subreddit", "子版块名称"],
        "tier": ["tier", "等级", "层级", "级别"],
        "categories": ["categories", "分类", "类别", "类目", "主要分类"],
        "description_keywords": [
            "description_keywords",
            "关键词",
            "关键字",
            "描述关键词",
            "观察到的核心痛点 (备注)",
        ],
        "daily_posts": ["daily_posts", "日发帖", "日发帖数", "每日帖子数"],
        "avg_comment_length": ["avg_comment_length", "平均评论长度", "评论长度"],
        # 量化健康分 (1-100) 会在解析时自动归一化为 0-1
        "quality_score": ["quality_score", "质量评分", "质量分", "量化健康分 (1-100)"],
        # 可选：是否入选（用于过滤未入选行）
        "is_active": ["is_active", "启用", "活跃", "是否启用", "最终入选"],
        "priority": ["priority", "优先级"],
    }

    SAMPLE_ROWS: Sequence[Dict[str, Any]] = (
        {
            "name": "r/startups",
            "tier": "gold",
            "categories": "startup,business,founder",
            "description_keywords": "startup,founder,product,launch",
            "daily_posts": 180,
            "avg_comment_length": 72,
            "quality_score": 0.95,
            "priority": "high",
        },
        {
            "name": "r/Entrepreneur",
            "tier": "gold",
            "categories": "business,marketing,sales",
            "description_keywords": "marketing,sales,pitch,growth",
            "daily_posts": 150,
            "avg_comment_length": 64,
            "quality_score": 0.88,
            "priority": "high",
        },
        {
            "name": "r/SaaS",
            "tier": "silver",
            "categories": "saas,pricing,metrics",
            "description_keywords": "subscription,pricing,mrr",
            "daily_posts": 65,
            "avg_comment_length": 84,
            "quality_score": 0.80,
            "priority": "medium",
        },
    )

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @classmethod
    def generate_template(cls) -> bytes:
        """Return Excel template with header comments and sample rows."""
        buffer = BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
        worksheet = workbook.add_worksheet("Communities")
        worksheet.freeze_panes(1, 0)

        column_order = cls._column_order()
        for col_idx, column_name in enumerate(column_order):
            worksheet.write(0, col_idx, column_name)
            hint = cls.COLUMN_HINTS.get(column_name)
            if hint:
                worksheet.write_comment(0, col_idx, hint)
            worksheet.set_column(col_idx, col_idx, 22)

        for row_idx, sample in enumerate(cls.SAMPLE_ROWS, start=1):
            for column_name, value in sample.items():
                column_index = column_order.index(column_name)
                worksheet.write(row_idx, column_index, value)

        workbook.close()
        buffer.seek(0)
        return buffer.read()

    async def import_from_excel(
        self,
        *,
        content: bytes,
        filename: str,
        dry_run: bool,
        actor_email: str,
        actor_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Validate the uploaded workbook and optionally persist new communities."""
        actor_ref = await self._resolve_actor(actor_id)

        try:
            rows, present_columns = self._extract_rows(content)
        except ValueError as exc:
            logger.warning("Failed to parse Excel file %s: %s", filename, exc)
            result = self._error_response(
                status="error",
                summary=self._empty_summary(),
                errors=[
                    {
                        "row": 0,
                        "field": "file",
                        "value": filename,
                        "error": "无法读取 Excel 文件，请确认文件格式正确",
                    }
                ],
            )
            await self._persist_history(
                filename=filename,
                actor_email=actor_email,
                actor_ref=actor_ref,
                dry_run=dry_run,
                result=result,
            )
            return result

        missing_columns = [
            col for col in self.REQUIRED_COLUMNS if col not in present_columns
        ]
        if missing_columns:
            result = self._error_response(
                status="error",
                summary=self._empty_summary(),
                errors=[
                    {
                        "row": 0,
                        "field": column,
                        "value": None,
                        "error": "模板缺少必填列",
                    }
                    for column in missing_columns
                ],
            )
            await self._persist_history(
                filename=filename,
                actor_email=actor_email,
                actor_ref=actor_ref,
                dry_run=dry_run,
                result=result,
            )
            return result

        if not rows:
            result = self._error_response(
                status="error",
                summary=self._empty_summary(),
                errors=[
                    {
                        "row": 0,
                        "field": "rows",
                        "value": None,
                        "error": "Excel 文件没有有效数据行",
                    }
                ],
            )
            await self._persist_history(
                filename=filename,
                actor_email=actor_email,
                actor_ref=actor_ref,
                dry_run=dry_run,
                result=result,
            )
            return result

        parsed_rows, row_states, errors = self._validate_rows(rows)

        importable_rows, duplicate_errors = await self._filter_existing_duplicates(
            parsed_rows, row_states
        )
        errors.extend(duplicate_errors)

        imported_records = 0
        if importable_rows and not dry_run:
            imported_records = await self._insert_communities(importable_rows, actor_ref)
            for entry in importable_rows:
                row_states[entry.row_number]["status"] = "imported"
        elif importable_rows and dry_run:
            for entry in importable_rows:
                row_states[entry.row_number]["status"] = "validated"

        summary = self._build_summary(row_states, imported_records)
        response_status = self._resolve_status(summary, dry_run)

        response: Dict[str, Any] = {
            "status": response_status,
            "summary": summary,
            "communities": [
                {
                    "name": state["name"],
                    "tier": state["tier"],
                    "status": state["status"],
                }
                for _, state in sorted(row_states.items())
            ],
        }
        if errors:
            response["errors"] = errors

        await self._persist_history(
            filename=filename,
            actor_email=actor_email,
            actor_ref=actor_ref,
            dry_run=dry_run,
            result=response,
        )
        return response

    async def get_import_history(self, limit: int = 50) -> Dict[str, Any]:
        stmt = (
            select(CommunityImportHistory)
            .order_by(CommunityImportHistory.created_at.desc())
            .limit(limit)
        )
        results = (await self._session.execute(stmt)).scalars().all()
        imports = [
            {
                "id": record.id,
                "filename": record.filename,
                "uploaded_by": record.uploaded_by,
                "uploaded_at": record.created_at,
                "dry_run": record.dry_run,
                "status": record.status,
                "summary": {
                    "total": record.total_rows,
                    "valid": record.valid_rows,
                    "invalid": record.invalid_rows,
                    "duplicates": record.duplicate_rows,
                    "imported": record.imported_rows,
                },
            }
            for record in results
        ]
        return {"imports": imports}

    async def _insert_communities(
        self, rows: Sequence[ParsedCommunityRow], actor_ref: uuid.UUID | None
    ) -> int:
        # 单用户模式：固定的 admin UUID 不作为外键,避免外键约束错误
        fixed_admin_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        is_single_user_mode = actor_ref == fixed_admin_id
        created_by_ref = None if is_single_user_mode else actor_ref
        updated_by_ref = None if is_single_user_mode else actor_ref

        for entry in rows:
            community = CommunityPool(
                name=entry.name,
                tier=entry.tier,
                categories=entry.categories,
                description_keywords=entry.description_keywords,
                daily_posts=int(entry.daily_posts or 0),
                avg_comment_length=int(entry.avg_comment_length or 0),
                quality_score=float(entry.quality_score or 0.5),
                priority=entry.priority or "medium",
                created_by=created_by_ref,
                updated_by=updated_by_ref,
            )
            self._session.add(community)
        await self._session.flush()
        return len(rows)

    async def _persist_history(
        self,
        *,
        filename: str,
        actor_email: str,
        actor_ref: uuid.UUID | None,
        dry_run: bool,
        result: Dict[str, Any],
    ) -> None:
        summary = result["summary"]

        # 单用户模式：固定的 admin UUID 不作为外键,避免外键约束错误
        # 所有外键字段都设置为 None,仅保留 uploaded_by 邮箱字符串用于审计
        fixed_admin_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        is_single_user_mode = actor_ref == fixed_admin_id

        record = CommunityImportHistory(
            filename=filename,
            uploaded_by=actor_email,
            uploaded_by_user_id=None if is_single_user_mode else actor_ref,
            dry_run=dry_run,
            status=result["status"],
            total_rows=summary["total"],
            valid_rows=summary["valid"],
            invalid_rows=summary["invalid"],
            duplicate_rows=summary["duplicates"],
            imported_rows=summary["imported"],
            error_details=result.get("errors"),
            summary_preview={"communities": result.get("communities", [])[:20]},
            created_by=None if is_single_user_mode else actor_ref,
            updated_by=None if is_single_user_mode else actor_ref,
        )
        self._session.add(record)
        await self._session.commit()

    async def _resolve_actor(self, actor_id: uuid.UUID | None) -> uuid.UUID | None:
        if actor_id is None:
            return None

        # 单用户模式：固定的 admin UUID 直接返回,不检查 User 表
        fixed_admin_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        if actor_id == fixed_admin_id:
            return actor_id

        # 其他 UUID 需要检查 User 表
        existing = await self._session.get(User, actor_id)
        if existing is None:
            logger.debug("Actor id %s not found; history entry will omit uploaded_by_user_id", actor_id)
            return None
        return actor_id

    def _extract_rows(self, content: bytes) -> Tuple[List[RowRecord], Sequence[str]]:
        if not content:
            raise ValueError("Excel 内容为空")

        try:
            workbook = xlrd.open_workbook(file_contents=content)
        except Exception as exc:  # pragma: no cover - xlrd raises multiple subclasses
            raise ValueError("无法解析 Excel 文件") from exc

        if workbook.nsheets == 0:
            return [], []

        sheet = workbook.sheet_by_index(0)
        column_order = self._column_order()

        # 建立表头映射（支持别名）
        def _normalize(text: str | None) -> str:
            return (text or "").strip().lower()

        alias_map: Dict[str, str] = {}
        for target, aliases in self.HEADER_ALIASES.items():
            for al in aliases:
                alias_map[_normalize(al)] = target

        # 在前 5 行内搜索最优表头行（匹配到的目标列最多者）
        header_row_idx = 0
        best_match_count = -1
        best_column_map: Dict[int, str] = {}
        for try_row in range(min(5, sheet.nrows)):
            trial_map: Dict[int, str] = {}
            for col_idx in range(sheet.ncols):
                header_raw = self._string_value(sheet.cell_value(try_row, col_idx))
                key = alias_map.get(_normalize(header_raw))
                if key in set(column_order) | {"is_active"}:
                    trial_map[col_idx] = key
            match_count = sum(1 for v in trial_map.values() if v in self.REQUIRED_COLUMNS)
            if match_count > best_match_count:
                best_match_count = match_count
                best_column_map = trial_map
                header_row_idx = try_row

        column_map: Dict[int, str] = best_column_map
        present_columns = [v for v in dict.fromkeys(column_map.values()) if v != "is_active"]

        records: List[RowRecord] = []
        for row_idx in range(header_row_idx + 1, sheet.nrows):
            row_data: Dict[str, Any] = {}
            non_empty = False
            include_row = True
            for col_idx, column_name in column_map.items():
                value = sheet.cell_value(row_idx, col_idx)
                if isinstance(value, str):
                    normalized = value.strip() or None
                else:
                    normalized = value

                # 质量分别名为“量化健康分 (1-100)”时，容忍 >1 的输入并归一化到 0-1
                if column_name == "quality_score" and isinstance(normalized, (int, float)):
                    try:
                        fv = float(normalized)
                        if fv > 1.0:
                            normalized = round(fv / 100.0, 4)
                    except Exception:
                        pass

                # is_active 列：用于过滤未入选行（如“最终入选”=否）
                if column_name == "is_active":
                    text = str(normalized).strip().lower() if normalized is not None else ""
                    include_row = text in {"1", "true", "yes", "y", "是", "真", "启用", "active"} or text == ""
                    # 不写入 row_data，纯粹用于过滤
                    continue

                row_data[column_name] = normalized
                if self._is_non_empty(normalized):
                    non_empty = True
            if not non_empty:
                continue
            if not include_row:
                continue
            for column_name in column_order:
                row_data.setdefault(column_name, None)
            # Convert zero-based row index to Excel numbering (header is row 1)
            records.append((row_idx + 1, row_data))

        return records, present_columns

    def _validate_rows(
        self,
        rows: List[RowRecord],
    ) -> Tuple[
        List[ParsedCommunityRow], Dict[int, Dict[str, str]], List[Dict[str, Any]]
    ]:
        parsed: List[ParsedCommunityRow] = []
        states: Dict[int, Dict[str, str]] = {}
        errors: List[Dict[str, Any]] = []
        seen_names: Dict[str, int] = {}

        for row_number, data in rows:
            raw_name = self._string_value(data.get("name"))
            raw_tier = self._string_value(data.get("tier"))
            states[row_number] = {
                "name": raw_name,
                "tier": raw_tier,
                "status": "invalid",
            }

            row_errors: List[Dict[str, Any]] = []
            if not raw_name:
                row_errors.append(
                    {
                        "row": row_number,
                        "field": "name",
                        "value": raw_name,
                        "error": "社区名称不能为空",
                    }
                )
            elif not raw_name.startswith("r/"):
                row_errors.append(
                    {
                        "row": row_number,
                        "field": "name",
                        "value": raw_name,
                        "error": "社区名称必须以 r/ 开头",
                    }
                )
            elif not 3 <= len(raw_name) <= 100:
                row_errors.append(
                    {
                        "row": row_number,
                        "field": "name",
                        "value": raw_name,
                        "error": "社区名称长度需介于 3-100 之间",
                    }
                )

            # 推断/验证 tier：若缺失则基于 quality_score 推断；否则校验
            tier_value = (raw_tier or "").lower()
            if not tier_value:
                # 尝试根据质量分推断（0-1）
                try:
                    qs = float(data.get("quality_score")) if data.get("quality_score") is not None else None
                except Exception:
                    qs = None
                if isinstance(qs, float):
                    if qs >= 0.8:
                        tier_value = "gold"
                    elif qs >= 0.6:
                        tier_value = "silver"
                    else:
                        tier_value = "seed"
                else:
                    tier_value = "seed"
            elif tier_value not in self.VALID_TIERS:
                row_errors.append(
                    {
                        "row": row_number,
                        "field": "tier",
                        "value": raw_tier,
                        "error": "tier 必须是 seed/gold/silver/admin 之一",
                    }
                )

            categories, category_errors = self._parse_list_field(
                data.get("categories"),
                row_number=row_number,
                field="categories",
                min_items=1,
                max_items=10,
            )
            row_errors.extend(category_errors)

            keywords, keyword_errors = self._parse_list_field(
                data.get("description_keywords"),
                row_number=row_number,
                field="description_keywords",
                min_items=1,
                max_items=20,
            )
            row_errors.extend(keyword_errors)

            daily_posts, daily_posts_errors = self._parse_int_field(
                data.get("daily_posts"),
                row_number=row_number,
                field="daily_posts",
                minimum=0,
                maximum=10000,
            )
            row_errors.extend(daily_posts_errors)

            avg_comment_length, avg_comment_errors = self._parse_int_field(
                data.get("avg_comment_length"),
                row_number=row_number,
                field="avg_comment_length",
                minimum=0,
                maximum=1000,
            )
            row_errors.extend(avg_comment_errors)

            quality_score, quality_errors = self._parse_float_field(
                data.get("quality_score"),
                row_number=row_number,
                field="quality_score",
                minimum=0.0,
                maximum=1.0,
            )
            row_errors.extend(quality_errors)

            priority_value = self._string_value(data.get("priority")).lower()
            priority: Optional[str] = None
            if priority_value:
                if priority_value not in self.VALID_PRIORITIES:
                    row_errors.append(
                        {
                            "row": row_number,
                            "field": "priority",
                            "value": priority_value,
                            "error": "priority 必须是 high/medium/low 之一",
                        }
                    )
                else:
                    priority = priority_value

            if row_errors:
                errors.extend(row_errors)
                continue

            normalized_name = raw_name.lower()
            if normalized_name in seen_names:
                errors.append(
                    {
                        "row": row_number,
                        "field": "name",
                        "value": raw_name,
                        "error": "Excel 中存在重复的社区名称",
                    }
                )
                states[row_number] = {
                    "name": raw_name,
                    "tier": raw_tier,
                    "status": "duplicate",
                }
                continue

            seen_names[normalized_name] = row_number
            states[row_number] = {
                "name": raw_name,
                "tier": raw_tier,
                "status": "pending",
            }
            parsed.append(
                ParsedCommunityRow(
                    row_number=row_number,
                    name=raw_name,
                    tier=tier_value,
                    categories=categories,
                    description_keywords=keywords,
                    daily_posts=daily_posts,
                    avg_comment_length=avg_comment_length,
                    quality_score=quality_score,
                    priority=priority,
                )
            )

        return parsed, states, errors

    async def _filter_existing_duplicates(
        self,
        rows: Sequence[ParsedCommunityRow],
        states: Dict[int, Dict[str, str]],
    ) -> Tuple[List[ParsedCommunityRow], List[Dict[str, Any]]]:
        if not rows:
            return [], []

        lower_names = {row.name.lower() for row in rows}
        stmt = select(CommunityPool.name).where(
            func.lower(CommunityPool.name).in_(lower_names)
        )
        existing = (await self._session.execute(stmt)).scalars().all()
        existing_normalized = {name.lower() for name in existing}

        filtered: List[ParsedCommunityRow] = []
        duplicate_errors: List[Dict[str, Any]] = []

        for entry in rows:
            if entry.name.lower() in existing_normalized:
                states[entry.row_number]["status"] = "duplicate"
                duplicate_errors.append(
                    {
                        "row": entry.row_number,
                        "field": "name",
                        "value": entry.name,
                        "error": "社区已存在于数据库，请勿重复导入",
                    }
                )
                continue
            filtered.append(entry)

        return filtered, duplicate_errors

    @staticmethod
    def _build_summary(
        states: Dict[int, Dict[str, str]], imported: int
    ) -> Dict[str, int]:
        total = len(states)
        invalid = sum(1 for state in states.values() if state["status"] == "invalid")
        duplicates = sum(
            1 for state in states.values() if state["status"] == "duplicate"
        )
        valid = sum(
            1
            for state in states.values()
            if state["status"] in {"imported", "validated", "pending"}
        )
        return {
            "total": total,
            "valid": valid,
            "invalid": invalid,
            "duplicates": duplicates,
            "imported": imported,
        }

    @staticmethod
    def _resolve_status(summary: Dict[str, int], dry_run: bool) -> str:
        if summary["invalid"] == 0 and summary["duplicates"] == 0:
            return "validated" if dry_run else "success"
        return "error"

    @staticmethod
    def _empty_summary() -> Dict[str, int]:
        return {"total": 0, "valid": 0, "invalid": 0, "duplicates": 0, "imported": 0}

    @staticmethod
    def _error_response(
        *,
        status: str,
        summary: Dict[str, int],
        errors: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "status": status,
            "summary": summary,
            "communities": [],
            "errors": list(errors),
        }

    @staticmethod
    def _string_value(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (int, float)):
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                return ""
            if float(value).is_integer():
                return str(int(value))
            return str(value).strip()
        return str(value).strip()

    @staticmethod
    def _is_non_empty(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip() != ""
        if isinstance(value, float):
            return not math.isnan(value)
        return True

    def _parse_list_field(
        self,
        value: Any,
        *,
        row_number: int,
        field: str,
        min_items: int,
        max_items: int,
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        text = self._string_value(value)
        errors: List[Dict[str, Any]] = []
        if not text:
            errors.append(
                {
                    "row": row_number,
                    "field": field,
                    "value": value,
                    "error": f"{field} 至少需要 {min_items} 个值",
                }
            )
            return [], errors

        tokens = [token.strip() for token in text.split(",") if token.strip()]
        if len(tokens) < min_items:
            errors.append(
                {
                    "row": row_number,
                    "field": field,
                    "value": text,
                    "error": f"{field} 至少需要 {min_items} 个值",
                }
            )
        if len(tokens) > max_items:
            errors.append(
                {
                    "row": row_number,
                    "field": field,
                    "value": text,
                    "error": f"{field} 最多允许 {max_items} 个值",
                }
            )
        return tokens, errors

    def _parse_int_field(
        self,
        value: Any,
        *,
        row_number: int,
        field: str,
        minimum: int,
        maximum: int,
    ) -> Tuple[Optional[int], List[Dict[str, Any]]]:
        if value in (None, ""):
            return None, []

        errors: List[Dict[str, Any]] = []
        try:
            numeric = int(float(value))
        except (TypeError, ValueError):
            errors.append(
                {
                    "row": row_number,
                    "field": field,
                    "value": value,
                    "error": f"{field} 需要是整数",
                }
            )
            return None, errors

        if not minimum <= numeric <= maximum:
            errors.append(
                {
                    "row": row_number,
                    "field": field,
                    "value": numeric,
                    "error": f"{field} 需要位于 {minimum}-{maximum} 之间",
                }
            )
        return numeric, errors

    def _parse_float_field(
        self,
        value: Any,
        *,
        row_number: int,
        field: str,
        minimum: float,
        maximum: float,
    ) -> Tuple[Optional[float], List[Dict[str, Any]]]:
        if value in (None, ""):
            return None, []

        errors: List[Dict[str, Any]] = []
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            errors.append(
                {
                    "row": row_number,
                    "field": field,
                    "value": value,
                    "error": f"{field} 需要是数字",
                }
            )
            return None, errors

        if not minimum <= numeric <= maximum:
            errors.append(
                {
                    "row": row_number,
                    "field": field,
                    "value": numeric,
                    "error": f"{field} 需要位于 {minimum}-{maximum} 之间",
                }
            )
        return numeric, errors

    @classmethod
    def _column_order(cls) -> List[str]:
        return list(cls.REQUIRED_COLUMNS) + list(cls.OPTIONAL_COLUMNS)


__all__ = ["CommunityImportService", "ParsedCommunityRow"]

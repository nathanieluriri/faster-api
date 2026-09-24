"""Postgres backend that speaks the subset of the Motor (MongoDB) API used by this project.

Each collection is a table with an ``id`` text primary key and a ``doc`` JSONB column, so the
repositories written for MongoDB run unchanged on Postgres, Supabase or Neon.

Supported: insert_one/insert_many, find/find_one (skip, limit, sort, projection),
find_one_and_update, find_one_and_delete, update_one/update_many, delete_one/delete_many,
count_documents and create_index. Filters support equality, dotted paths, $and, $or, $eq, $ne,
$gt, $gte, $lt, $lte, $in, $nin and $exists. Updates support $set, $unset and $inc.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable
from urllib.parse import urlparse
from uuid import UUID

import asyncpg
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
_BYTES_TAG = "$fasterapi_bytes"
_COMPARISONS = {"$eq": "=", "$ne": "IS DISTINCT FROM", "$gt": ">", "$gte": ">=", "$lt": "<", "$lte": "<="}


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (ObjectId, UUID, Decimal)):
        return str(value)
    if isinstance(value, (set, frozenset, tuple)):
        return list(value)
    if isinstance(value, (bytes, bytearray)):
        # Tagged so reads return bytes again, e.g. bcrypt password hashes.
        return {_BYTES_TAG: base64.b64encode(value).decode("ascii")}
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _dumps(value: Any) -> str:
    return json.dumps(value, default=_json_default)


def _decode_object(value: dict) -> Any:
    if len(value) == 1 and _BYTES_TAG in value:
        return base64.b64decode(value[_BYTES_TAG])
    return value


def _loads(raw: str) -> Any:
    return json.loads(raw, object_hook=_decode_object)


def _load_id(raw: str) -> Any:
    return ObjectId(raw) if ObjectId.is_valid(raw) and len(raw) == 24 else raw


def _quote(name: str) -> str:
    if not _IDENTIFIER.match(name):
        raise ValueError(f"Invalid collection name: {name!r}")
    return f'"{name}"'


def _uses_transaction_pooler(dsn: str) -> bool:
    if os.getenv("DB_TYPE", "").lower() == "supabase":
        return True
    parsed = urlparse(dsn)
    return parsed.port == 6543 or "pooler" in (parsed.hostname or "")


# Match pymongo's result objects, including `acknowledged`, which callers check.
@dataclass
class InsertOneResult:
    inserted_id: Any
    acknowledged: bool = True


@dataclass
class InsertManyResult:
    inserted_ids: list[Any]
    acknowledged: bool = True


@dataclass
class UpdateResult:
    matched_count: int
    modified_count: int
    upserted_id: Any = None
    acknowledged: bool = True


@dataclass
class DeleteResult:
    deleted_count: int
    acknowledged: bool = True


@dataclass
class _Params:
    values: list[Any] = field(default_factory=list)

    def add(self, value: Any) -> str:
        self.values.append(value)
        return f"${len(self.values)}"


def _nest(path: list[str], value: Any) -> dict:
    for key in reversed(path):
        value = {key: value}
    return value


def _id_clause(condition: Any, params: _Params) -> str:
    if isinstance(condition, dict) and condition and all(k.startswith("$") for k in condition):
        clauses = []
        for op, value in condition.items():
            if op == "$eq":
                clauses.append(f"id = {params.add(str(value))}")
            elif op == "$ne":
                clauses.append(f"id <> {params.add(str(value))}")
            elif op in ("$in", "$nin"):
                match = f"id = ANY({params.add([str(v) for v in value])}::text[])"
                clauses.append(match if op == "$in" else f"NOT ({match})")
            else:
                raise NotImplementedError(f"Operator {op} on _id is not supported by the Postgres backend")
        return " AND ".join(clauses)
    return f"id = {params.add(str(condition))}"


def _where(filter_dict: dict | None, params: _Params) -> str:
    clauses: list[str] = []
    for key, condition in (filter_dict or {}).items():
        if key in ("$and", "$or"):
            parts = [f"({_where(sub, params)})" for sub in condition]
            if parts:
                clauses.append("(" + (" AND " if key == "$and" else " OR ").join(parts) + ")")
            continue
        if key.startswith("$"):
            raise NotImplementedError(f"Filter operator {key} is not supported by the Postgres backend")
        if key == "_id":
            clauses.append(_id_clause(condition, params))
            continue

        path = key.split(".")
        if isinstance(condition, dict) and condition and all(k.startswith("$") for k in condition):
            expr = f"(doc #> {params.add(path)}::text[])"
            for op, value in condition.items():
                if op in ("$eq", "$ne"):
                    clauses.append(f"{expr} {_COMPARISONS[op]} {params.add(_dumps(value))}::jsonb")
                elif op in _COMPARISONS:
                    # MongoDB only compares values of the same type; jsonb would order null below numbers.
                    value_param = params.add(_dumps(value))
                    clauses.append(
                        f"({expr} {_COMPARISONS[op]} {value_param}::jsonb "
                        f"AND jsonb_typeof({expr}) = jsonb_typeof({value_param}::jsonb))"
                    )
                elif op in ("$in", "$nin"):
                    match = f"COALESCE({expr} = ANY({params.add([_dumps(v) for v in value])}::jsonb[]), FALSE)"
                    clauses.append(match if op == "$in" else f"NOT {match}")
                elif op == "$exists":
                    clauses.append(f"{expr} IS {'NOT ' if value else ''}NULL")
                else:
                    raise NotImplementedError(f"Filter operator {op} is not supported by the Postgres backend")
        elif condition is None:
            expr = f"(doc #> {params.add(path)}::text[])"
            clauses.append(f"({expr} IS NULL OR {expr} = 'null'::jsonb)")
        else:
            clauses.append(f"doc @> {params.add(_dumps(_nest(path, condition)))}::jsonb")
    return " AND ".join(clauses) or "TRUE"


def _update_expr(update: dict, params: _Params, base: str) -> str:
    if not update or not all(key.startswith("$") for key in update):
        raise NotImplementedError("Only operator updates ($set, $unset, $inc) are supported by the Postgres backend")
    unsupported = set(update) - {"$set", "$unset", "$inc"}
    if unsupported:
        raise NotImplementedError(f"Update operators {sorted(unsupported)} are not supported by the Postgres backend")

    expr = base
    for key in list(update.get("$set", {})) + list(update.get("$inc", {})):
        if "." in key or key == "_id":
            raise NotImplementedError(f"Updating {key!r} is not supported by the Postgres backend")
    if update.get("$set"):
        expr = f"({expr} || {params.add(_dumps(update['$set']))}::jsonb)"
    if update.get("$unset"):
        expr = f"({expr} - {params.add(list(update['$unset']))}::text[])"
    for key, amount in update.get("$inc", {}).items():
        key_param = params.add(key)
        expr = (
            f"jsonb_set({expr}, ARRAY[{key_param}::text], "
            f"to_jsonb(COALESCE(({expr} ->> {key_param}::text)::numeric, 0) + {params.add(str(amount))}::numeric))"
        )
    return expr


def _order_by(sort: list[tuple[str, int]] | None, params: _Params) -> str:
    if not sort:
        return "ORDER BY created_at, id"
    parts = []
    for key, direction in sort:
        column = "id" if key == "_id" else f"(doc #> {params.add(key.split('.'))}::text[])"
        parts.append(f"{column} {'DESC' if direction == -1 else 'ASC'}")
    return "ORDER BY " + ", ".join(parts)


def _project(document: dict, projection: dict | list | None) -> dict:
    if not projection:
        return document
    if isinstance(projection, list):
        projection = {key: 1 for key in projection}
    included = {key for key, flag in projection.items() if flag and key != "_id"}
    if included:
        keep_id = projection.get("_id", 1)
        return {k: v for k, v in document.items() if k in included or (k == "_id" and keep_id)}
    return {k: v for k, v in document.items() if k not in projection}


def _to_document(row: asyncpg.Record) -> dict:
    document = _loads(row["doc"])
    return {"_id": _load_id(row["id"]), **document}


def _row_count(status: str) -> int:
    return int(status.rsplit(" ", 1)[-1])


def _normalize_sort(key_or_list: Any, direction: int = 1) -> list[tuple[str, int]]:
    if isinstance(key_or_list, str):
        return [(key_or_list, direction)]
    return [(key, value) for key, value in key_or_list]


class PostgresCursor:
    def __init__(self, collection: "PostgresCollection", filter_dict: dict | None, projection: Any):
        self._collection = collection
        self._filter = filter_dict or {}
        self._projection = projection
        self._skip = 0
        self._limit = 0
        self._sort: list[tuple[str, int]] | None = None

    def skip(self, count: int) -> "PostgresCursor":
        self._skip = max(int(count), 0)
        return self

    def limit(self, count: int) -> "PostgresCursor":
        self._limit = max(int(count), 0)
        return self

    def sort(self, key_or_list: Any, direction: int = 1) -> "PostgresCursor":
        self._sort = _normalize_sort(key_or_list, direction)
        return self

    async def to_list(self, length: int | None = None) -> list[dict]:
        if length:
            self._limit = min(self._limit, length) if self._limit else length
        params = _Params()
        where = _where(self._filter, params)
        order = _order_by(self._sort, params)
        sql = f"SELECT id, doc FROM {self._collection._table} WHERE {where} {order}"
        if self._limit:
            sql += f" LIMIT {params.add(self._limit)}"
        if self._skip:
            sql += f" OFFSET {params.add(self._skip)}"
        rows = await self._collection._fetch(sql, *params.values)
        return [_project(_to_document(row), self._projection) for row in rows]

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for document in await self.to_list():
            yield document


class PostgresCollection:
    def __init__(self, store: "PostgresDocumentStore", name: str):
        self._store = store
        self.name = name
        self._table = _quote(name)

    async def _ensure_table(self, connection: asyncpg.Connection) -> None:
        if self.name in self._store._ready_tables:
            return
        statements = [
            f"CREATE TABLE IF NOT EXISTS {self._table} ("
            "id TEXT PRIMARY KEY, doc JSONB NOT NULL DEFAULT '{}'::jsonb, "
            "created_at TIMESTAMPTZ NOT NULL DEFAULT now())",
            f'CREATE INDEX IF NOT EXISTS "{self.name}_doc_idx" ON {self._table} USING GIN (doc jsonb_path_ops)',
            f'CREATE INDEX IF NOT EXISTS "{self.name}_created_idx" ON {self._table} (created_at, id)',
            # Keeps tables private from Supabase's auto-generated REST API; the owning role still has access.
            f"ALTER TABLE {self._table} ENABLE ROW LEVEL SECURITY",
        ]
        for statement in statements:
            try:
                await connection.execute(statement)
            except (asyncpg.DuplicateTableError, asyncpg.DuplicateObjectError, asyncpg.UniqueViolationError):
                pass
        self._store._ready_tables.add(self.name)

    async def _run(self, method: str, sql: str, *args: Any) -> Any:
        pool = await self._store._get_pool()
        async with pool.acquire() as connection:
            await self._ensure_table(connection)
            try:
                return await getattr(connection, method)(sql, *args)
            except asyncpg.UniqueViolationError as exc:
                raise DuplicateKeyError(str(exc)) from exc

    async def _fetch(self, sql: str, *args: Any) -> list[asyncpg.Record]:
        return await self._run("fetch", sql, *args)

    async def _fetchrow(self, sql: str, *args: Any) -> asyncpg.Record | None:
        return await self._run("fetchrow", sql, *args)

    async def _execute(self, sql: str, *args: Any) -> str:
        return await self._run("execute", sql, *args)

    async def insert_one(self, document: dict, **_: Any) -> InsertOneResult:
        document.setdefault("_id", ObjectId())
        body = {k: v for k, v in document.items() if k != "_id"}
        await self._execute(
            f"INSERT INTO {self._table} (id, doc) VALUES ($1, $2::jsonb)", str(document["_id"]), _dumps(body)
        )
        return InsertOneResult(document["_id"])

    async def insert_many(self, documents: Iterable[dict], **_: Any) -> InsertManyResult:
        ids = [(await self.insert_one(document)).inserted_id for document in documents]
        return InsertManyResult(ids)

    def find(self, filter: dict | None = None, projection: Any = None, **_: Any) -> PostgresCursor:
        return PostgresCursor(self, filter, projection)

    async def find_one(self, filter: dict | None = None, projection: Any = None, sort: Any = None, **_: Any) -> dict | None:
        cursor = self.find(filter, projection).limit(1)
        if sort:
            cursor.sort(sort)
        documents = await cursor.to_list()
        return documents[0] if documents else None

    async def count_documents(self, filter: dict | None = None, **_: Any) -> int:
        params = _Params()
        row = await self._fetchrow(f"SELECT count(*) AS total FROM {self._table} WHERE {_where(filter, params)}", *params.values)
        return int(row["total"])

    async def find_one_and_update(
        self, filter: dict, update: dict, projection: Any = None, return_document: bool = False, upsert: bool = False, **_: Any
    ) -> dict | None:
        if upsert:
            raise NotImplementedError("upsert is not supported by the Postgres backend")
        params = _Params()
        where = _where(filter, params)
        expr = _update_expr(update, params, base="t.doc")
        row = await self._fetchrow(
            f"WITH target AS (SELECT id, doc FROM {self._table} WHERE {where} ORDER BY created_at, id LIMIT 1 FOR UPDATE) "
            f"UPDATE {self._table} AS t SET doc = {expr} FROM target WHERE t.id = target.id "
            "RETURNING t.id AS id, target.doc AS before, t.doc AS after",
            *params.values,
        )
        if row is None:
            return None
        document = {"_id": _load_id(row["id"]), **_loads(row["after" if return_document else "before"])}
        return _project(document, projection)

    async def find_one_and_delete(self, filter: dict, projection: Any = None, **_: Any) -> dict | None:
        params = _Params()
        row = await self._fetchrow(
            f"DELETE FROM {self._table} WHERE id = (SELECT id FROM {self._table} WHERE {_where(filter, params)} "
            "ORDER BY created_at, id LIMIT 1) RETURNING id, doc",
            *params.values,
        )
        return _project(_to_document(row), projection) if row else None

    async def _update(self, filter: dict, update: dict, single: bool, upsert: bool) -> UpdateResult:
        if upsert:
            raise NotImplementedError("upsert is not supported by the Postgres backend")
        params = _Params()
        where = _where(filter, params)
        expr = _update_expr(update, params, base="t.doc")
        limit = " ORDER BY created_at, id LIMIT 1" if single else ""
        status = await self._execute(
            f"UPDATE {self._table} AS t SET doc = {expr} WHERE t.id IN (SELECT id FROM {self._table} WHERE {where}{limit})",
            *params.values,
        )
        count = _row_count(status)
        return UpdateResult(matched_count=count, modified_count=count)

    async def update_one(self, filter: dict, update: dict, upsert: bool = False, **_: Any) -> UpdateResult:
        return await self._update(filter, update, single=True, upsert=upsert)

    async def update_many(self, filter: dict, update: dict, upsert: bool = False, **_: Any) -> UpdateResult:
        return await self._update(filter, update, single=False, upsert=upsert)

    async def _delete(self, filter: dict | None, single: bool) -> DeleteResult:
        params = _Params()
        limit = " ORDER BY created_at, id LIMIT 1" if single else ""
        status = await self._execute(
            f"DELETE FROM {self._table} WHERE id IN (SELECT id FROM {self._table} WHERE {_where(filter, params)}{limit})",
            *params.values,
        )
        return DeleteResult(deleted_count=_row_count(status))

    async def delete_one(self, filter: dict, **_: Any) -> DeleteResult:
        return await self._delete(filter, single=True)

    async def delete_many(self, filter: dict | None = None, **_: Any) -> DeleteResult:
        return await self._delete(filter, single=False)

    async def create_index(self, keys: Any, unique: bool = False, name: str | None = None, **_: Any) -> str:
        fields = _normalize_sort(keys)
        index_name = name or f"{self.name}_{'_'.join(key.replace('.', '_') for key, _ in fields)}_idx"
        _quote(index_name)
        columns = ", ".join(
            "id" if key == "_id" else "((doc #>> '{" + ",".join(key.split(".")) + "}'))" for key, _ in fields
        )
        for key, _ in fields:
            if not all(_IDENTIFIER.match(part) for part in key.split(".")):
                raise ValueError(f"Invalid index field: {key!r}")
        await self._execute(
            f'CREATE {"UNIQUE " if unique else ""}INDEX IF NOT EXISTS "{index_name}" ON {self._table} ({columns})'
        )
        return index_name

    def __getattr__(self, name: str) -> Any:
        raise NotImplementedError(f"Collection.{name}() is not supported by the Postgres backend")


class PostgresDocumentStore:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pools: dict[asyncio.AbstractEventLoop, asyncio.Future] = {}
        self._collections: dict[str, PostgresCollection] = {}
        self._ready_tables: set[str] = set()

    async def _get_pool(self) -> asyncpg.Pool:
        loop = asyncio.get_running_loop()
        task = self._pools.get(loop)
        if task is None:
            task = asyncio.ensure_future(
                asyncpg.create_pool(
                    self._dsn,
                    min_size=0,
                    max_size=int(os.getenv("DB_POOL_MAX_SIZE") or 5),
                    statement_cache_size=0 if _uses_transaction_pooler(self._dsn) else 100,
                    command_timeout=30,
                )
            )
            self._pools[loop] = task
        try:
            return await task
        except Exception:
            self._pools.pop(loop, None)
            raise

    def __getitem__(self, name: str) -> PostgresCollection:
        collection = self._collections.get(name)
        if collection is None:
            collection = self._collections[name] = PostgresCollection(self, name)
        return collection

    def __getattr__(self, name: str) -> PostgresCollection:
        if name.startswith("_"):
            raise AttributeError(name)
        return self[name]

    async def ping(self) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as connection:
            await connection.execute("SELECT 1")

    async def close(self) -> None:
        task = self._pools.pop(asyncio.get_running_loop(), None)
        if task is not None:
            await (await task).close()

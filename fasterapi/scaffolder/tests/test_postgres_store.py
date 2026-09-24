import asyncio
import os
import sys
import uuid
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "project_template"
DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="set TEST_DATABASE_URL to run Postgres tests")


@pytest.fixture()
def store():
    sys.path.insert(0, str(TEMPLATE))
    try:
        from core.postgres_store import PostgresDocumentStore
    finally:
        sys.path.remove(str(TEMPLATE))
    return PostgresDocumentStore(DATABASE_URL)


def run(coro):
    return asyncio.run(coro)


def test_crud_roundtrip_matches_motor_behaviour(store):
    from bson import ObjectId
    from pymongo import ReturnDocument
    from pymongo.errors import DuplicateKeyError

    items = store[f"t_{uuid.uuid4().hex[:8]}"]

    async def scenario():
        doc = {"name": "ada", "age": 36, "tags": ["x"], "profile": {"city": "Lagos"}}
        inserted = await items.insert_one(doc)
        assert isinstance(inserted.inserted_id, ObjectId) and doc["_id"] == inserted.inserted_id
        await items.insert_many([{"name": "bob", "age": 20}, {"name": "cy", "age": None}])

        found = await items.find_one({"_id": inserted.inserted_id})
        assert found["name"] == "ada" and found["_id"] == inserted.inserted_id
        assert (await items.find_one(filter={"profile.city": "Lagos"}))["name"] == "ada"
        assert await items.find_one({"name": "nobody"}) is None

        assert await items.count_documents({}) == 3
        assert await items.count_documents({"age": {"$gte": 21}}) == 1
        assert await items.count_documents({"age": None}) == 1
        assert await items.count_documents({"name": {"$in": ["ada", "bob"]}}) == 2
        assert await items.count_documents({"name": {"$nin": ["ada"]}}) == 2
        assert await items.count_documents({"$or": [{"name": "ada"}, {"age": 20}]}) == 2
        assert await items.count_documents({"missing": {"$exists": False}}) == 3
        assert await items.count_documents({"missing": {"$in": [1, None]}}) == 3
        assert await items.count_documents({"age": {"$nin": [None]}}) == 2

        names = [d["name"] async for d in items.find({}).sort("name", -1).skip(1).limit(1)]
        assert names == ["bob"]
        assert [d["name"] for d in await items.find({}, {"name": 1}).to_list(length=2)] == ["ada", "bob"]

        before = await items.find_one_and_update({"name": "ada"}, {"$set": {"age": 37}, "$inc": {"logins": 1}})
        assert before["age"] == 36
        after = await items.find_one_and_update(
            {"name": "ada"}, {"$inc": {"logins": 2}, "$unset": {"tags": ""}}, return_document=ReturnDocument.AFTER
        )
        assert after["logins"] == 3 and "tags" not in after and after["age"] == 37

        assert (await items.update_many({"age": {"$lt": 100}}, {"$set": {"seen": True}})).modified_count == 2
        with pytest.raises(DuplicateKeyError):
            await items.insert_one({"_id": inserted.inserted_id})
        with pytest.raises(NotImplementedError):
            await items.find_one({"name": {"$regex": "a"}})

        await items.create_index("name", unique=True)
        with pytest.raises(DuplicateKeyError):
            await items.insert_one({"name": "bob"})

        assert (await items.find_one_and_delete({"name": "cy"}))["name"] == "cy"
        assert (await items.delete_many({})).deleted_count == 2
        await store.close()

    run(scenario())


def test_collection_names_are_validated(store):
    with pytest.raises(ValueError):
        store["users; DROP TABLE x"]

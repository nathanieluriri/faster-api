from pathlib import Path

def create_service_file(name: str):
    db_name = name.lower()
    repo_module = f"repositories.{db_name}"
    schema_module = f"schemas.{db_name}"
    service_path = Path.cwd() / "services" / f"{db_name}.py"

    class_name = "".join([part.capitalize() for part in db_name.split("_")])
    create_class_name = f"{class_name}Create"
    update_class_name = f"{class_name}Update"
    out_class_name = f"{class_name}Out"

    service_code = f'''
from bson import ObjectId
from fastapi import HTTPException
from typing import List

from {repo_module} import (
    create_{db_name},
    get_{db_name},
    get_{db_name}s,
    update_{db_name},
    delete_{db_name},
)
from {schema_module} import {create_class_name}, {update_class_name}, {out_class_name}


async def add_{db_name}({db_name}_data: {create_class_name}) -> {out_class_name}:
    return await create_{db_name}({db_name}_data)


async def remove_{db_name}({db_name}_id: str):
    if not ObjectId.is_valid({db_name}_id):
        raise HTTPException(status_code=400, detail="Invalid {db_name} ID format")

    filter_dict = {{"_id": ObjectId({db_name}_id)}}
    result = await delete_{db_name}(filter_dict)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="{class_name} not found")


async def retrieve_{db_name}_by_{db_name}_id({db_name}_id: str) -> {out_class_name}:
    if not ObjectId.is_valid({db_name}_id):
        raise HTTPException(status_code=400, detail="Invalid {db_name} ID format")

    filter_dict = {{"_id": ObjectId({db_name}_id)}}
    result = await get_{db_name}(filter_dict)

    if not result:
        raise HTTPException(status_code=404, detail="{class_name} not found")

    return result


async def retrieve_{db_name}s() -> List[{out_class_name}]:
    return await get_{db_name}s()


async def update_{db_name}_by_id({db_name}_id: str, {db_name}_data: {update_class_name}) -> {out_class_name}:
    if not ObjectId.is_valid({db_name}_id):
        raise HTTPException(status_code=400, detail="Invalid {db_name} ID format")

    filter_dict = {{"_id": ObjectId({db_name}_id)}}
    result = await update_{db_name}(filter_dict, {db_name}_data)

    if not result:
        raise HTTPException(status_code=404, detail="{class_name} not found or update failed")

    return result
'''.strip()

    service_path.parent.mkdir(parents=True, exist_ok=True)
    with open(service_path, "w") as f:
        f.write(service_code)

    print(f"✅ Service for '{db_name}' created at services/{db_name}_services.py")

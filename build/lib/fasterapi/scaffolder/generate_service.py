from pathlib import Path
from datetime import datetime
def create_service_file(name: str):
    db_name = name.lower()
    repo_module = f"repositories.{db_name}"
    schema_module = f"schemas.{db_name}"
    service_path = Path.cwd() / "services" / f"{db_name}_service.py"

    class_name = "".join([part.capitalize() for part in db_name.split("_")])
    create_class_name = f"{class_name}Create"
    update_class_name = f"{class_name}Update"
    out_class_name = f"{class_name}Out"

    service_code = f'''
# ============================================================================
# {db_name.upper()} SERVICE
# ============================================================================
# This file was auto-generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S WAT')}
# It contains  asynchrounous functions that make use of the repo functions 
# 
# ============================================================================

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
    """adds an entry of {create_class_name} to the database and returns an object

    Returns:
        _type_: {out_class_name}
    """
    return await create_{db_name}({db_name}_data)


async def remove_{db_name}({db_name}_id: str):
    """deletes a field from the database and removes {create_class_name}object 

    Raises:
        HTTPException 400: Invalid {db_name} ID format
        HTTPException 404:  {class_name} not found
    """
    if not ObjectId.is_valid({db_name}_id):
        raise HTTPException(status_code=400, detail="Invalid {db_name} ID format")

    filter_dict = {{"_id": ObjectId({db_name}_id)}}
    result = await delete_{db_name}(filter_dict)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="{class_name} not found")


async def retrieve_{db_name}_by_{db_name}_id(id: str) -> {out_class_name}:
    """Retrieves {db_name} object based specific Id 

    Raises:
        HTTPException 404(not found): if  {class_name} not found in the db
        HTTPException 400(bad request): if  Invalid {db_name} ID format

    Returns:
        _type_: {out_class_name}
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid {db_name} ID format")

    filter_dict = {{"_id": ObjectId(id)}}
    result = await get_{db_name}(filter_dict)

    if not result:
        raise HTTPException(status_code=404, detail="{class_name} not found")

    return result


async def retrieve_{db_name}s(start=0,stop=100) -> List[{out_class_name}]:
    """Retrieves {out_class_name} Objects in a list

    Returns:
        _type_: {out_class_name}
    """
    return await get_{db_name}s(start=start,stop=stop)


async def update_{db_name}_by_id({db_name}_id: str, {db_name}_data: {update_class_name}) -> {out_class_name}:
    """updates an entry of {db_name} in the database

    Raises:
        HTTPException 404(not found): if {class_name} not found or update failed
        HTTPException 400(not found): Invalid {db_name} ID format

    Returns:
        _type_: {out_class_name}
    """
    if not ObjectId.is_valid({db_name}_id):
        raise HTTPException(status_code=400, detail="Invalid {db_name} ID format")

    filter_dict = {{"_id": ObjectId({db_name}_id)}}
    result = await update_{db_name}(filter_dict, {db_name}_data)

    if not result:
        raise HTTPException(status_code=404, detail="{class_name} not found or update failed")

    return result
'''.strip()

    service_path.parent.mkdir(parents=True, exist_ok=True)
    with open(service_path, "w",encoding="utf-8") as f:
        f.write(service_code)

    print(f"✅ Service for '{db_name}' created at services/{db_name}_services.py")

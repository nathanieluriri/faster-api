
import os

def get_latest_modified_api_version(base_path=None):
    # If no base path is provided, look for 'api' in the current working directory
    if base_path is None:
        base_path = os.path.join(os.getcwd(), 'api')
    else:
        base_path = os.path.abspath(base_path)

    if not os.path.exists(base_path):
        raise FileNotFoundError(f"The directory '{base_path}' does not exist.")
    
    subdirs = [
        os.path.join(base_path, d) for d in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, d))
    ]
    
    if not subdirs:
        raise FileNotFoundError(f"No version folders found in '{base_path}'.")

    latest_subdir = max(subdirs, key=os.path.getmtime)
    return os.path.basename(latest_subdir)

import re

def get_highest_numbered_api_version(base_path=None):
    if base_path is None:
        base_path = os.path.join(os.getcwd(), 'api')
    else:
        base_path = os.path.abspath(base_path)

    if not os.path.exists(base_path):
        raise FileNotFoundError(f"The directory '{base_path}' does not exist.")
    
    version_dirs = [
        d for d in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, d)) and re.match(r'^v\d+$', d)
    ]

    if not version_dirs:
        raise FileNotFoundError(f"No version folders like 'v1', 'v2' found in '{base_path}'.")

    highest_version = max(version_dirs, key=lambda v: int(v[1:]))
    return highest_version


def create_route_file(name: str,version:str):
    from pathlib import Path

    db_name = name.lower()
    schema_path = Path.cwd() / "schemas" / f"{db_name}.py"
    service_path = Path.cwd() / "services" / f"{db_name}_service.py"
    repo_path = Path.cwd() / "repositories" / f"{db_name}.py"
    route_path = Path.cwd() / "api" /version/ f"{db_name}.py"
    if not schema_path.exists():
        print(f"❌ Schema file {schema_path} not found. Schema needed to generate route for {db_name}")
        return
    if not repo_path.exists():
        print(f"❌ Repository file {repo_path} not found. Repo needed to generate route for {db_name}")
        return
    if not service_path.exists():
        print(f"❌ Service file {service_path} not found. Service needed to generate route for {db_name}")
        return
    class_name = "".join(part.capitalize() for part in db_name.split("_"))
    from pydantic import BaseModel
    from inspect import signature

    def get_extra_fields(create_model: BaseModel, base_model: BaseModel):
        return list(set(create_model.model_fields.keys()) - set(base_model.model_fields.keys()))
    import importlib

    schema_module = importlib.import_module(f"schemas.{db_name}")
    create_model = getattr(schema_module, f"{class_name}Create")
    base_model = getattr(schema_module, f"{class_name}Base")
    def generate_dynamic_create_route(class_name: str, db_name: str):
        schema_module = importlib.import_module(f"schemas.{db_name}")
        create_model = getattr(schema_module, f"{class_name}Create")
        base_model = getattr(schema_module, f"{class_name}Base")
        extras = get_extra_fields(create_model, base_model)

        if not extras:
            return f'''
    @router.post("/", response_model=APIResponse[{class_name}Out], status_code=status.HTTP_201_CREATED)
    async def create_{db_name}(item: {class_name}Base):
        payload = {class_name}Create(**item.model_dump())
        created = await add_{db_name}({db_name}Data=payload)
        return APIResponse(status_code=201, data=created, detail="Created successfully")
    '''

        # Construct path and param declarations
        path_string = "/".join([f'{{{field}}}' for field in extras])
        param_decls = "\n".join([
            f'    {field}: str = Path(..., description="Path parameter: {field}")' for field in extras
        ])
        param_names = ", ".join([f"{field}={field}" for field in extras])

        return f'''
    @router.post("/{path_string}/", response_model=APIResponse[{class_name}Out], status_code=status.HTTP_201_CREATED)
    async def create_{db_name}(item: {class_name}Base,{chr(10)}{param_decls}):
        payload = {class_name}Create(**item.model_dump(), {param_names})
        created = await add_{db_name}({db_name}Data=payload)
        return APIResponse(status_code=201, data=created, detail="Created successfully")
    '''


    route_code = f'''from fastapi import APIRouter, HTTPException, Query, status
from typing import List
from schemas.response_schema import APIResponse
from schemas.{db_name} import (
    {class_name}Create,
    {class_name}Out,
    {class_name}Base,
    {class_name}Update,
)
from services.{db_name}_service import (
    add_{db_name},
    remove_{db_name},
    retrieve_{db_name}s,
    retrieve_{db_name}s_by_user,
    update_{db_name},
)

router = APIRouter(prefix="/{db_name}s", tags=["{class_name}s"])


@router.get("/", response_model=APIResponse[List[{class_name}Out]])
async def list_{db_name}s():
    items = await retrieve_{db_name}s()
    return APIResponse(status_code=200, data=items, detail="Fetched successfully")


@router.get("/me", response_model=APIResponse[List[{class_name}Out]])
async def get_my_{db_name}s(userId: str = Query(..., description="User ID to fetch user-specific items")):
    items = await retrieve_{db_name}s_by_user(userId=userId)
    return APIResponse(status_code=200, data=items, detail="User's items fetched")
'''
    dynamic_create_route = generate_dynamic_create_route(class_name, db_name, create_model, base_model)



    with open(route_path, "w") as f:
        f.write(route_code)
        f.write(dynamic_create_route)
    print(f"✅ Route file created: api/{version}/{db_name}.py")
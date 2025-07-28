import os
import re
import sys
from pathlib import Path
from pydantic import BaseModel
import importlib

def get_latest_modified_api_version(base_dir: str = None) -> str:
    """
    Get the latest modified API version directory (e.g., 'v1', 'v2').
    
    Args:
        base_dir (str): Base directory of the project. Defaults to current directory.
    
    Returns:
        str: Name of the latest modified version directory.
    
    Raises:
        FileNotFoundError: If the API directory or version folders are not found.
    """
    if base_dir is None:
        base_path = os.path.join(os.getcwd(), 'api')
    else:
        base_path = os.path.abspath(os.path.join(base_dir, 'api'))

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

def get_highest_numbered_api_version(base_dir: str = None) -> str:
    """
    Get the highest numbered API version directory (e.g., 'v2' > 'v1').
    
    Args:
        base_dir (str): Base directory of the project. Defaults to current directory.
    
    Returns:
        str: Name of the highest numbered version directory.
    
    Raises:
        FileNotFoundError: If the API directory or version folders are not found.
    """
    if base_dir is None:
        base_path = os.path.join(os.getcwd(), 'api')
    else:
        base_path = os.path.abspath(os.path.join(base_dir, 'api'))

    if not os.path.exists(base_path):
        raise FileNotFoundError(f"The directory '{base_path}' does not exist.")
    
    version_dirs = [
        d for d in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, d)) and re.match(r'^v\d+$', d)
    ]

    if not version_dirs:
        raise FileNotFoundError(f"No version folders like 'v1', 'v2' found in '{base_path}'.")

    return max(version_dirs, key=lambda v: int(v[1:]))

def create_route_file(name: str, version: str = None, base_dir: str = None) -> bool:
    """
    Create a FastAPI route file for a given resource name and API version.
    
    Args:
        name (str): Name of the resource (e.g., 'user' or 'order_item').
        version (str): API version (e.g., 'v1'). If None, uses highest numbered version.
        base_dir (str): Base directory of the project. Defaults to current directory.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    # Set base directory
    base_path = Path(base_dir) if base_dir else Path.cwd()
    
    # Ensure schemas and services are in sys.path
    sys.path.append(str(base_path))
    
    # Determine API version
    if not version:
        try:
            version = get_highest_numbered_api_version(base_dir)
        except FileNotFoundError as e:
            print(f"❌ {e}")
            return False

    db_name = name.lower()
    class_name = "".join(part.capitalize() for part in db_name.split("_"))
    
    # Define file paths
    schema_path = base_path / "schemas" / f"{db_name}.py"
    service_path = base_path / "services" / f"{db_name}_service.py"
    repo_path = base_path / "repositories" / f"{db_name}.py"
    route_path = base_path / "api" / version / f"{db_name}.py"
    
    # Check for required files
    for path, desc in [
        (schema_path, "Schema"),
        (service_path, "Service"),
        (repo_path, "Repository")
    ]:
        if not path.exists():
            print(f"❌ {desc} file {path} not found.")
            return False
    
    # Dynamically import schema to verify models
   


    # Generate route code
    route_code = f"""
from fastapi import APIRouter, HTTPException, Query, status, Path
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
""" 

    # Write route file
    try:
        route_path.parent.mkdir(parents=True, exist_ok=True)
        with route_path.open("w") as f:
            f.write(route_code)
         
        print(f"✅ Route file created: {route_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to write route file: {e}")
        return False
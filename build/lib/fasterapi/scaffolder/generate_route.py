import os
import re
import sys
import json # Added import for parsing filter JSON
from pathlib import Path
from pydantic import BaseModel
import importlib
from datetime import datetime # Added missing import

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
    # NOTE: Added 'import json' to route_code and updated the list route for filters.
    route_code = f"""
from fastapi import APIRouter, HTTPException, Query, Path, status
from typing import List, Optional
import json
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
    retrieve_{db_name}_by_{db_name}_id,
    update_{db_name}_by_id,
)

router = APIRouter(prefix="/{db_name}s", tags=["{class_name}s"])


# ------------------------------
# List {class_name}s (with pagination and filtering)
# ------------------------------
@router.get("/", response_model=APIResponse[List[{class_name}Out]])
async def list_{db_name}s(
    start: Optional[int] = Query(None, description="Start index for range-based pagination"),
    stop: Optional[int] = Query(None, description="Stop index for range-based pagination"),
    page_number: Optional[int] = Query(None, description="Page number for page-based pagination (0-indexed)"),
    # New: Filter parameter expects a JSON string
    filters: Optional[str] = Query(None, description="Optional JSON string of MongoDB filter criteria (e.g., '{{\\"field\\": \\"value\\"}}')")
):
    \"""
    Retrieves a list of {class_name}s with pagination and optional filtering.
    - Priority 1: Range-based (start/stop)
    - Priority 2: Page-based (page_number)
    - Priority 3: Default (first 100)
    \"""
    PAGE_SIZE = 50
    parsed_filters = {{}}

    # 1. Handle Filters
    if filters:
        try:
            parsed_filters = json.loads(filters)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON format for 'filters' query parameter."
            )

    # 2. Determine Pagination
    # Case 1: Prefer start/stop if provided
    if start is not None or stop is not None:
        if start is None or stop is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Both 'start' and 'stop' must be provided together.")
        if stop < start:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'stop' cannot be less than 'start'.")
        
        # Pass filters to the service layer
        items = await retrieve_{db_name}s(filters=parsed_filters, start=start, stop=stop)
        return APIResponse(status_code=200, data=items, detail="Fetched successfully")

    # Case 2: Use page_number if provided
    elif page_number is not None:
        if page_number < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'page_number' cannot be negative.")
        
        start_index = page_number * PAGE_SIZE
        stop_index = start_index + PAGE_SIZE
        # Pass filters to the service layer
        items = await retrieve_{db_name}s(filters=parsed_filters, start=start_index, stop=stop_index)
        return APIResponse(status_code=200, data=items, detail=f"Fetched page {{page_number}} successfully")

    # Case 3: Default (no params)
    else:
        # Pass filters to the service layer
        items = await retrieve_{db_name}s(filters=parsed_filters, start=0, stop=100)
        detail_msg = "Fetched first 100 records successfully"
        if parsed_filters:
            # If filters were applied, adjust the detail message
            detail_msg = f"Fetched first 100 records successfully (with filters applied)"
        return APIResponse(status_code=200, data=items, detail=detail_msg)


# ------------------------------
# Retrieve a single {class_name}
# ------------------------------
@router.get("/{{id}}", response_model=APIResponse[{class_name}Out])
async def get_{db_name}_by_id(
    id: str = Path(..., description="{db_name} ID to fetch specific item")
):
    \"""
    Retrieves a single {class_name} by its ID.
    \"""
    item = await retrieve_{db_name}_by_{db_name}_id(id=id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{class_name} not found")
    return APIResponse(status_code=200, data=item, detail="{db_name} item fetched")


# ------------------------------
# Create a new {class_name}
# ------------------------------
# Uses {class_name}Base for input (correctly)
@router.post("/", response_model=APIResponse[{class_name}Out], status_code=status.HTTP_201_CREATED)
async def create_{db_name}(payload: {class_name}Base):
    \"""
    Creates a new {class_name}.
    \"""
    # Creates {class_name}Create object which includes date_created/last_updated
    new_data = {class_name}Create(**payload.model_dump()) 
    new_item = await add_{db_name}(new_data)
    if not new_item:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create {db_name}")
    
    return APIResponse(status_code=201, data=new_item, detail=f"{class_name} created successfully")


# ------------------------------
# Update an existing {class_name}
# ------------------------------
# Uses PATCH for partial update (correctly)
@router.patch("/{{id}}", response_model=APIResponse[{class_name}Out])
async def update_{db_name}(
    id: str = Path(..., description="ID of the {{db_name}} to update"),
    payload: {class_name}Update = None
):
    \"""
    Updates an existing {class_name} by its ID.
    Assumes the service layer handles partial updates (e.g., ignores None fields in payload).
    \"""
    updated_item = await update_{db_name}_by_id(id=id, data=payload)
    if not updated_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{class_name} not found or update failed")
    
    return APIResponse(status_code=200, data=updated_item, detail=f"{class_name} updated successfully")


# ------------------------------
# Delete an existing {class_name}
# ------------------------------
@router.delete("/{{id}}", response_model=APIResponse[None])
async def delete_{db_name}(id: str = Path(..., description="ID of the {db_name} to delete")):
    \"""
    Deletes an existing {class_name} by its ID.
    \"""
    deleted = await remove_{db_name}(id)
    if not deleted:
        # This assumes remove_{db_name} returns a boolean or similar
        # to indicate if deletion was successful (i.e., item was found).
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{class_name} not found or deletion failed")
    
    return APIResponse(status_code=200, data=None, detail=f"{class_name} deleted successfully")
"""


    # Write route file
    try:
        route_path.parent.mkdir(parents=True, exist_ok=True)
        # Use utf-8 encoding for reliable file writing
        with route_path.open("w",encoding="utf-8") as f:
            f.write(route_code)
          
        print(f"✅ Route file created: {route_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to write route file: {e}")
        return False
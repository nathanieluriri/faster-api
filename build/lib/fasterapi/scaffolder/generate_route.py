
def get_latest_modified_api_version(base_path='templates/project_template/api'):
    import os
    api_path = os.path.abspath(base_path)
    if not os.path.exists(api_path):
        raise FileNotFoundError(f"The directory '{api_path}' does not exist.")
    
    subdirs = [
        os.path.join(api_path, d) for d in os.listdir(api_path)
        if os.path.isdir(os.path.join(api_path, d))
    ]
    
    if not subdirs:
        raise FileNotFoundError(f"No version folders found in '{api_path}'.")

    latest_subdir = max(subdirs, key=os.path.getmtime)
    return os.path.basename(latest_subdir)


def get_highest_numbered_api_version(base_path='templates/project_template/api'):
    import os
    import re
    api_path = os.path.abspath(base_path)
    if not os.path.exists(api_path):
        raise FileNotFoundError(f"The directory '{api_path}' does not exist.")
    
    version_dirs = [
        d for d in os.listdir(api_path)
        if os.path.isdir(os.path.join(api_path, d)) and re.match(r'^v\d+$', d)
    ]

    if not version_dirs:
        raise FileNotFoundError(f"No version folders with pattern 'vN' found in '{api_path}'.")

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
    route_code=route_code = f'''from fastapi import APIRouter, HTTPException, status  # , Depends
from typing import List
from schemas.response_schema import APIResponse
from schemas.{db_name} import (
    {class_name}Create,
    {class_name}Out,
    {class_name}BaseRequest,
    {class_name}Update,
)
from services.{db_name}_service import (
    add_{db_name},
    remove_{db_name},
    retrieve_{db_name}s,
    retrieve_{db_name}s_by_user,
    update_{db_name},
)

# from services.user_service import get_user_details_with_accessToken
# from services.admin_services import get_admin_details_with_accessToken_service
# from security.auth import verify_any_token

router = APIRouter(prefix="/{db_name}s", tags=["{class_name}s"])


@router.get("/", response_model=APIResponse[List[{class_name}Out]])
async def list_{db_name}s():
    items = await retrieve_{db_name}s()
    return APIResponse(status_code=200, data=items, detail="Fetched successfully")


# @router.get("/me", response_model=APIResponse[List[{class_name}Out]], dependencies=[Depends(verify_any_token)])
# async def get_my_{db_name}s(dep=Depends(verify_any_token)):
#     user = await (
#         get_admin_details_with_accessToken_service(dep["accessToken"])
#         if dep["role"] == "admin"
#         else get_user_details_with_accessToken(dep["accessToken"])
#     )
#     items = await retrieve_{db_name}s_by_user(userId=user.userId)
#     return APIResponse(status_code=200, data=items, detail="User's items fetched")

@router.get("/me", response_model=APIResponse[List[{class_name}Out]])
async def get_my_{db_name}s(userId: str = Query(..., description="User ID to fetch user-specific items")):
    items = await retrieve_{db_name}s_by_user(userId=userId)
    return APIResponse(status_code=200, data=items, detail="User's items fetched")


@router.post("/", response_model=APIResponse[{class_name}Out], status_code=status.HTTP_201_CREATED)
async def create_{db_name}(item: {class_name}BaseRequest, userId: str = Query(...)):
    payload = {class_name}Create(**item.model_dump(), userId=userId)  # , role=dep["role"]
    created = await add_{db_name}({db_name}Data=payload)
    return APIResponse(status_code=201, data=created, detail="Created successfully")


# @router.post("/", response_model=APIResponse[{class_name}Out], status_code=status.HTTP_201_CREATED)
# async def create_{db_name}(item: {class_name}BaseRequest):  # , dep=Depends(verify_any_token)
    # user = await (
    #     get_admin_details_with_accessToken_service(dep["accessToken"])
    #     if dep["role"] == "admin"
    #     else get_user_details_with_accessToken(dep["accessToken"])
    # )
    payload = {class_name}Create(**item.model_dump())  # , userId=user.userId, role=dep["role"]
    created = await add_{db_name}({db_name}Data=payload)
    return APIResponse(status_code=201, data=created, detail="Created successfully")


@router.delete("/{{id}}", response_model=APIResponse[{class_name}Out])
async def delete_{db_name}(id: str):
    deleted = await remove_{db_name}({db_name}Id=id)
    if deleted:
        return APIResponse(status_code=200, data=deleted, detail="Deleted successfully")
    raise HTTPException(status_code=404, detail="Resource not found")


@router.patch("/{{id}}", response_model=APIResponse[{class_name}Out])
async def update_{db_name}(id: str, update_data: {class_name}Update):
    updated = await update_{db_name}({db_name}Id=id, data=update_data)
    return APIResponse(status_code=200, data=updated, detail="Updated successfully")
'''

    with open(route_path, "w") as f:
        f.write(route_code)
    print(f"✅ Route file created: api/{version}/{db_name}.py")
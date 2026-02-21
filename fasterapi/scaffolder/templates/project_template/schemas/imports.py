from bson import ObjectId
from pydantic import GetJsonSchemaHandler
from pydantic import BaseModel, EmailStr, Field,model_validator
from pydantic_core import core_schema
from datetime import datetime,timezone
from typing import Optional,List,Any
from enum import Enum
import time


class LoginType(str, Enum):
    google = "GOOGLE"
    email = "EMAIL"

class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"

class Permission(BaseModel):
    name: str
    methods: List[str]
    path: str
    key: Optional[str] = None
    description: Optional[str] = None

class PermissionList(BaseModel):
    permissions: List[Permission]

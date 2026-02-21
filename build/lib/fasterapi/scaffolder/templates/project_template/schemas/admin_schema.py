from schemas.imports import *
from pydantic import Field
import time
from security.hash import hash_password
from typing import List, Optional
from pydantic import BaseModel, EmailStr, model_validator

class AdminBase(BaseModel):

    full_name: str
    email: EmailStr
    password: str | bytes
    accountStatus: AccountStatus = AccountStatus.ACTIVE
    permissionList: Optional[PermissionList] = None


class AdminLogin(BaseModel):
    # Add other fields here 
    email:EmailStr
    password:str | bytes
    pass
class AdminRefresh(BaseModel):
    # Add other fields here 
    refresh_token:str
    pass


class AdminCreate(AdminBase):
    # Add other fields here
    invited_by:str 
    date_created: int = Field(default_factory=lambda: int(time.time()))
    last_updated: int = Field(default_factory=lambda: int(time.time()))
    @model_validator(mode='after')
    def obscure_password(self):
        self.password=hash_password(self.password)
        return self
class AdminUpdate(BaseModel):
    # Add other fields here 
    password:Optional[str | bytes]=None
    last_updated: int = Field(default_factory=lambda: int(time.time()))
    @model_validator(mode='after') # type: ignore
    def obscure_password(self):
        if self.password:
            self.password=hash_password(self.password)
            return self
class AdminOut(AdminBase):
    # Add other fields here 
    id: Optional[str] = Field(default=None, alias="_id")

    date_created: Optional[int] = None
    last_updated: Optional[int] = None
    refresh_token: Optional[str] =None
    access_token:Optional[str]=None
    @model_validator(mode="before")
    @classmethod
    def convert_objectid(cls, values):
        if "_id" in values and isinstance(values["_id"], ObjectId):
            values["_id"] = str(values["_id"])  # coerce to string before validation
        return values
            
    class Config:
        populate_by_name = True  # allows using `id` when constructing the model
        arbitrary_types_allowed = True  # allows ObjectId type
        json_encoders = {
            ObjectId: str  # automatically converts ObjectId → str
        }

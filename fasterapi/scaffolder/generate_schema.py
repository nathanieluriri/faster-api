from pathlib import Path
from datetime import datetime
from datetime import datetime
def create_schema_file(name: str):
    db_name=name.lower()
    schema_dir = Path.cwd() / "schemas"
    schema_path = schema_dir / f"{db_name}.py"
    schema_dir.mkdir(exist_ok=True)

    if schema_path.exists():
        print(f"⚠️  Schema already exists: schemas/{db_name}.py")
        return

    # Convert snake_case to PascalCase
    class_name = "".join(part.capitalize() for part in db_name.split("_"))

    schema_code = f'''
# ============================================================================
#{db_name.upper()} SCHEMA 
# ============================================================================
# This file was auto-generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S WAT')}
# It contains Pydantic classes  database
# for managing attributes and validation of data in and out of the MongoDB database.
#
# ============================================================================

from schemas.imports import *
from pydantic import Field
import time

class {class_name}Base(BaseModel):
    # Add other fields here 
    pass

class {class_name}Create({class_name}Base):
    # Add other fields here 
    date_created: int = Field(default_factory=lambda: int(time.time()))
    last_updated: int = Field(default_factory=lambda: int(time.time()))

class {class_name}Update(BaseModel):
    # Add other fields here 
    last_updated: int = Field(default_factory=lambda: int(time.time()))

class {class_name}Out({class_name}Base):
    # Add other fields here 
    id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("_id", "id"),
        serialization_alias="id",
    )
    date_created: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("date_created", "dateCreated"),
        serialization_alias="dateCreated",
    )
    last_updated: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("last_updated", "lastUpdated"),
        serialization_alias="lastUpdated",
    )
    
    @model_validator(mode="before")
    @classmethod
    def convert_objectid(cls, values):
        if "_id" in values and isinstance(values["_id"], ObjectId):
            values["_id"] = str(values["_id"])  # coerce to string before validation
        return values
            
    class Config:
        populate_by_name = True  # allows using `id` when constructing the model
        arbitrary_types_allowed = True  # allows ObjectId type
        json_encoders ={{
            ObjectId: str  # automatically converts ObjectId → str
        }}
    
'''.strip()

    with open(schema_path, "w", encoding="utf-8") as f:
        f.write(schema_code)

    print(f"✅ Schema file created: schemas/{db_name}.py")

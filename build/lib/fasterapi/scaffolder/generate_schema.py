from pathlib import Path
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
    id: Optional[str] =None
    date_created: Optional[int] = None
    last_updated: Optional[int] = None
    
    @model_validator(mode='before')
    def set_dynamic_values(cls,values):
        values['id']= str(values.get('_id'))
        return values
    class Config:
        orm_mode = True
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {{
            ObjectId: str
        }}
'''.strip()

    with open(schema_path, "w") as f:
        f.write(schema_code)

    print(f"✅ Schema file created: schemas/{db_name}.py")

import shutil
from pathlib import Path

def create_project(project_name):
    source = Path(__file__).parent / "templates" / "project_template"
    target = Path.cwd() / project_name

    if target.exists():
        print("❌ Project already exists.")
        return

    shutil.copytree(source, target)
    print(f"✅ Project created at {target}")
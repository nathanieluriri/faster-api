import shutil
from pathlib import Path
from typing import List


def _get_template_source() -> Path:
    return Path(__file__).parent / "templates" / "project_template"


def _find_conflicts(source: Path, target: Path) -> List[str]:
    conflicts: List[str] = []
    for item in source.iterdir():
        if (target / item.name).exists():
            conflicts.append(item.name)
    return sorted(conflicts)


def create_project(project_name: str) -> bool:
    source = _get_template_source()
    target = Path.cwd() / project_name

    if target.exists():
        print("❌ Project already exists.")
        return False

    shutil.copytree(source, target)
    print(f"✅ Project created at {target}")
    return True


def create_project_in_current_directory() -> bool:
    source = _get_template_source()
    target = Path.cwd()
    conflicts = _find_conflicts(source, target)

    if conflicts:
        print("❌ Cannot scaffold into the current directory.")
        print(f"   Conflicting paths already exist: {', '.join(conflicts)}")
        print("   Use 'fasterapi new <name>' or remove the conflicting paths and try again.")
        return False

    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)

    print(f"✅ Project scaffolded in current directory: {target}")
    return True

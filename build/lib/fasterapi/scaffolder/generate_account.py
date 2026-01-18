from pathlib import Path
import re


def _apply_replacements(content: str, name: str) -> str:
    class_name = "".join(part.capitalize() for part in name.split("_"))

    replacements = [
        ("schemas.user_schema", f"schemas.{name}_schema"),
        ("repositories.user_repo", f"repositories.{name}_repo"),
        ("services.user_service", f"services.{name}_service"),
        ("api.v1.user_route", f"api.v1.{name}_route"),
        ("user_schema", f"{name}_schema"),
        ("user_repo", f"{name}_repo"),
        ("user_service", f"{name}_service"),
        ("user_route", f"{name}_route"),
    ]

    for old, new in replacements:
        content = content.replace(old, new)

    content = re.sub(r"\bUserBase\b", f"{class_name}Base", content)
    content = re.sub(r"\bUserCreate\b", f"{class_name}Create", content)
    content = re.sub(r"\bUserUpdate\b", f"{class_name}Update", content)
    content = re.sub(r"\bUserOut\b", f"{class_name}Out", content)
    content = re.sub(r"\bUserRefresh\b", f"{class_name}Refresh", content)
    content = re.sub(r"\bUsers\b", f"{class_name}s", content)
    content = re.sub(r"\busers\b", f"{name}s", content)
    content = re.sub(r"\bUser\b", class_name, content)
    content = re.sub(r"\buser\b", name, content)

    return content


def create_account_files(name: str):
    db_name = name.lower()
    class_name = "".join(part.capitalize() for part in db_name.split("_"))

    template_root = Path(__file__).parent / "templates" / "project_template"
    targets = {
        template_root / "schemas" / "user_schema.py": Path.cwd() / "schemas" / f"{db_name}_schema.py",
        template_root / "repositories" / "user_repo.py": Path.cwd() / "repositories" / f"{db_name}_repo.py",
        template_root / "services" / "user_service.py": Path.cwd() / "services" / f"{db_name}_service.py",
        template_root / "api" / "v1" / "user_route.py": Path.cwd() / "api" / "v1" / f"{db_name}_route.py",
    }

    for source_path, target_path in targets.items():
        if not source_path.exists():
            print(f"❌ Missing template file: {source_path}")
            return
        if target_path.exists():
            print(f"❌ Target file already exists: {target_path}")
            return

    for source_path, target_path in targets.items():
        target_path.parent.mkdir(parents=True, exist_ok=True)
        content = source_path.read_text(encoding="utf-8")
        content = _apply_replacements(content, db_name)
        target_path.write_text(content, encoding="utf-8")

    print(
        f"✅ {class_name} account scaffolding created: "
        f"schemas/{db_name}_schema.py, repositories/{db_name}_repo.py, "
        f"services/{db_name}_service.py, api/v1/{db_name}_route.py"
    )

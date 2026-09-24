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


def create_account_files(name: str) -> bool:
    # Imported here because split_user_roles imports _apply_replacements from this module.
    from fasterapi.scaffolder.split_user_roles import add_account_role

    return add_account_role(name)

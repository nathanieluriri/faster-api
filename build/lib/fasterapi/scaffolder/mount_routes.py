from pathlib import Path

def update_main_routes():
    project_path = Path.cwd()
    api_dir = project_path / "api"
    main_file = project_path / "main.py"

    if not api_dir.exists():
        print("⚠️  Couldn't find 'api/' folder. Are you running this from your project root directory?")
        return

    if not main_file.exists():
        print("❌ 'main.py' not found in project root. Make sure you're in the right directory.")
        return

    route_imports = []
    include_lines = []

    for version_dir in sorted(api_dir.glob("v*")):
        if not version_dir.is_dir():
            continue

        version = version_dir.name  # e.g., "v1"

        for py_file in sorted(version_dir.glob("*.py")):
            if py_file.name == "__init__.py":
                continue

            module_name = py_file.stem  # e.g., 'admin'
            module_path = f"api.{version}.{module_name}"
            router_alias = f"{version}_{module_name}_router"

            # Import line
            route_imports.append(f"from {module_path} import router as {router_alias}")

            # Include line
            prefix = f"/{version}"
            include_lines.append(f"app.include_router({router_alias}, prefix='{prefix}')")

    if not route_imports:
        print("⚠️  No route modules found in version folders.")
        return

    # Prepare block
    start_tag = "# --- auto-routes-start ---"
    end_tag = "# --- auto-routes-end ---"
    new_block = f"{start_tag}\n" + "\n".join(route_imports + [""] + include_lines) + f"\n{end_tag}"

    try:
        main_contents = main_file.read_text()
    except Exception as e:
        print(f"❌ Failed to read main.py: {e}")
        return

    if start_tag in main_contents and end_tag in main_contents:
        updated = (
            main_contents.split(start_tag)[0]
            + new_block
            + main_contents.split(end_tag)[1]
        )
    else:
        updated = main_contents.strip() + "\n\n" + new_block

    try:
        main_file.write_text(updated)
        print(f"✅ main.py updated with routes from: {[f.name for f in version_dir.glob('*.py') if f.name != '__init__.py']}")
    except Exception as e:
        print(f"❌ Failed to write to main.py: {e}")

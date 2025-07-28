from pathlib import Path

def update_main_routes():
    project_path = Path.cwd()
    api_dir = project_path / "api"
    main_file = project_path / "main.py"

    if not api_dir.exists():
        print("⚠️  Couldn't find 'api/' folder. Are you running this from your project root directory?")
        return

    version_dirs = [d for d in api_dir.iterdir() if d.is_dir() and d.name.startswith("v")]
    version_dirs.sort()

    if not version_dirs:
        print("⚠️  No versioned API directories found in 'api/'. Expected folders like 'v1', 'v2', etc.")
        return

    route_lines = []

    for vdir in version_dirs:
        version = vdir.name
        module_path = f"api.{version}.routes"
        route_lines.append(f"from {module_path} import router as {version}_router")
    
    route_lines.append("")
    for vdir in version_dirs:
        version = vdir.name
        route_lines.append(f"app.include_router({version}_router, prefix='/{version}')")

    if not main_file.exists():
        print("❌ 'main.py' not found in project root. Make sure you're in the right directory.")
        return

    try:
        main_contents = main_file.read_text()
    except Exception as e:
        print(f"❌ Failed to read main.py: {e}")
        return

    # Replace a block between special comments or append if not found
    start_tag = "# --- auto-routes-start ---"
    end_tag = "# --- auto-routes-end ---"

    new_block = f"{start_tag}\n" + "\n".join(route_lines) + f"\n{end_tag}"

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
        print(f"✅ main.py updated with routes: {[v.name for v in version_dirs]}")
    except Exception as e:
        print(f"❌ Failed to write to main.py: {e}")

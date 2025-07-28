import re
from pathlib import Path

VERSION_FILE = Path("fasterapi/__version__.py")

def bump_version():
    if not VERSION_FILE.exists():
        print(f"❌ Error: {VERSION_FILE} not found.")
        return

    content = VERSION_FILE.read_text()

    match = re.search(r'__version__\s*=\s*["\'](\d+)\.(\d+)\.(\d+)["\']', content)
    if not match:
        print("❌ Could not find a valid version string in __version__.py.")
        return

    major, minor, patch = map(int, match.groups())
    patch += 1
    new_version = f"{major}.{minor}.{patch}"
    new_line = f'__version__ = "{new_version}"'

    updated_content = re.sub(r'__version__\s*=\s*["\'].*?["\']', new_line, content)
    VERSION_FILE.write_text(updated_content)

    print(f"✅ Version bumped to {new_version}")
    return new_version

if __name__ == "__main__":
    bump_version()

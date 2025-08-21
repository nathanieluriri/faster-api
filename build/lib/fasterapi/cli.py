import click
from fasterapi.scaffolder.generate_project import create_project
from fasterapi.scaffolder.generate_crud import create_crud_file
from fasterapi.scaffolder.generate_schema import create_schema_file
from fasterapi.scaffolder.generate_service import create_service_file
from fasterapi.scaffolder.generate_route import create_route_file,get_highest_numbered_api_version,get_latest_modified_api_version
from fasterapi.__version__ import __version__
from fasterapi.scaffolder.mount_routes import update_main_routes
from fasterapi.scaffolder.generate_tokens_repo import create_token_file
from fasterapi.scaffolder.generate_dependencies import create_dependency_file
import subprocess

@click.group()
@click.version_option(__version__, '--version', '-v', message='FasterAPI version %(version)s')
def cli():
    """⚡ FasterAPI CLI — Scaffold FastAPI apps with ease"""
    pass


@cli.command()
@click.argument("name")
def new(name):
    """Create a new FastAPI project."""
    create_project(name)

@cli.command()
@click.argument("name")
def make_crud(name):
    """
    Generate CRUD repository functions for a schema.

    Requires that a schema with the given NAME already exists.

    \b
    ✅ Good usage:
        fasterapi make-crud user
        fasterapi make-crud product
        fasterapi make-crud order

    ❌ Bad usage:
        fasterapi make-crud        # Missing name
        fasterapi make-crud User   # Avoid capital letters
        fasterapi make-crud user profile  # Too many arguments

    Notes:
        - The corresponding schema must already exist before running this.
    """
    create_crud_file(name)
    
@cli.command()
@click.argument("name")
def make_schema(name):
    """
    Generate Pydantic class templates for a schema.

    \b
    ✅ Good usage:
        fasterapi make-schema user
        fasterapi make-schema product
        fasterapi make-schema order

    ❌ Bad usage:
        fasterapi make-schema        # Missing name
        fasterapi make-schema User   # Avoid capital letters
        fasterapi make-schema user profile  # Too many arguments

    Notes:
        - The schema will be created in the appropriate project folder.
    """
    create_schema_file(name)
    

@cli.command()
@click.argument("name")
def make_service(name):
    """
    Generate Python service templates to interact with a schema and repository.

    \b
    ✅ Good usage:
        fasterapi make-service user
        fasterapi make-service product
        fasterapi make-service order

    ❌ Bad usage:
        fasterapi make-service        # Missing name
        fasterapi make-service User   # Avoid capital letters
        fasterapi make-service user profile  # Too many arguments

    Notes:
      
        - A matching schema and repository should already exist.
    """
    create_service_file(name)
    
@cli.command()
def mount():
    """
    Mount all API routes into the main FastAPI application file.

    This command scans the `api/v*` directories and automatically updates
    your `main.py` (the entrypoint file) to include the discovered routes.

    \b
    ✅ Good usage:
        fasterapi mount
        
    ❌ Bad usage:
        fasterapi mount user       # This command takes no arguments
        fasterapi mount --help me  # Use only 'fasterapi mount' or 'fasterapi mount --help'
        
    Notes:
        - Run this after generating new routes (e.g., with `make-route`).
        - Existing imports and route mounts will be preserved.
    """
    try:
        update_main_routes()
        click.secho("✅ Routes successfully mounted into main.py.", fg="green")
    except Exception as e:
        click.secho(f"❌ Failed to mount routes: {e}", fg="red")
        raise click.Abort()
    
@cli.command(name="run-d")
def run_d():
    """
    Run the FastAPI development server with Uvicorn (auto-reload enabled).

    \b
    ✅ Good usage:
        fasterapi run-d

    ❌ Bad usage:
        fasterapi run-d extra       # This command takes no arguments

    Notes:
        - This is equivalent to running:
            uvicorn main:app --reload
        - Ensure you have Uvicorn installed (pip install uvicorn).
    """
    try:
        subprocess.run(["uvicorn", "main:app", "--reload"], check=True)
    except FileNotFoundError:
        click.secho("❌ Uvicorn is not installed. Run 'pip install uvicorn' and try again.", fg="red")
    except subprocess.CalledProcessError as e:
        click.secho(f"❌ Failed to start server: {e}", fg="red")
        raise click.Abort()


@cli.command()
def update():
    """
    Upgrade the FasterAPI CLI to the latest version.

    \b
    ✅ Good usage:
        fasterapi update

    ❌ Bad usage:
        fasterapi update extra   # This command takes no arguments

    Notes:
        - This will run:
            pip install --upgrade nats-fasterapi
        - Ensure you have pip available in your PATH.
    """
    try:
        subprocess.run(
            ["pip", "install", "--upgrade", "nats-fasterapi"],
            check=True
        )
        click.secho("✅ FasterAPI has been upgraded to the latest version!", fg="green")
    except FileNotFoundError:
        click.secho("❌ Pip is not installed or not found in PATH.", fg="red", err=True)
        raise click.Abort()
    except subprocess.CalledProcessError:
        click.secho("❌ Failed to upgrade FasterAPI. Please try again.", fg="red", err=True)
        raise click.Abort()

@cli.command()
@click.argument("name")
@click.option(
    "--version-mode",
    type=click.Choice(["latest-modified", "highest-number"], case_sensitive=True),
    required=False,
    help="Choose API versioning strategy: 'latest-modified' or 'highest-number'.",
)
@click.option(
    "-y", "--yes",
    is_flag=True,
    help="Skip prompts and use default options (non-interactive mode).",
)
def make_route(name, version_mode, yes):
    """
    Generate an API route file for a given schema.

    \b
    ✅ Good usage:
        fasterapi make-route user --version-mode latest-modified
        fasterapi make-route product --version-mode highest-number
        fasterapi make-route order                # Will ask interactively
        fasterapi make-route order -y             # Skips prompt, uses default

    ❌ Bad usage:
        fasterapi make-route                      # Missing name
        fasterapi make-route user foo             # Invalid version-mode

    Notes:
        - NAME should be a lowercase schema name (e.g., 'user').
        - If no --version-mode is provided:
            → Prompt interactively (unless -y is used).
            → Defaults to 'highest-number' when skipped.
    """
    if not version_mode:
        if yes:
            version_mode = "highest-number"
            click.secho("⚠️ No version mode provided. Using default: highest-number", fg="yellow")
        else:
            version_mode = click.prompt(
                "Select version mode",
                type=click.Choice(["latest-modified", "highest-number"]),
                default="highest-number",
                show_choices=True,
            )

    if version_mode == "latest-modified":
        version = get_latest_modified_api_version()
    else:  # "highest-number"
        version = get_highest_numbered_api_version()

    click.secho(f"📌 Selected API version: {version}", fg="cyan")
    create_route_file(name, version)
    click.secho(f"✅ Route for '{name}' created successfully.", fg="green")

 
@cli.command()
@click.argument("roles", nargs=-1)
def make_token_repo(roles):
    """
    Generate a token repository based on roles.

    \b
    ✅ Good usage:
        fasterapi make-token-repo admin user
        fasterapi make-token-repo staff guest-editor
        fasterapi make-token-repo                 # Defaults will be used

    ❌ Bad usage:
        fasterapi make-token-repo admin 1 3 , @! user staff extra-role arg  

    Notes:
        - Provide one or more roles (space-separated).
        - If no roles are provided, defaults will be used:
          admin, user, staff, guest-editor
    """
    if not roles:
        roles = ["admin", "user"]
        click.secho(
            f"⚠️ No roles provided. Using default roles: {', '.join(roles)}",
            fg="yellow"
        )

    create_token_file(roles)
    click.secho(
        f"✅ Token repository generated successfully for roles: {', '.join(roles)}",
        fg="green"
    )


@cli.command()
def make_token_deps():
    """
    Generate the token dependency file from the token repository.

    \b
    ✅ Good usage:
        fasterapi make-token-deps

    ❌ Bad usage:
        fasterapi make-token-deps extra-arg   # This command takes no arguments

    Notes:
        - Run this after creating a token repository (make-token-repo).
        - The generated file contains dependency utilities for authentication.
    """
    try:
        create_dependency_file()
        click.secho("✅ Token dependency file generated successfully.", fg="green")
    except Exception as e:
        click.secho(f"❌ Failed to generate token dependencies: {e}", fg="red")
        raise click.Abort()

@cli.command(name="git-push-auto")
def git_push_auto():
    """
    Automates a three-step Git workflow: add, commit, and push.

    \b
    ✅ Good usage:
        fasterapi git-push-auto

    ❌ Bad usage:
        fasterapi git-push-auto extra    # This command takes no arguments

    Notes:
        - This is equivalent to running:
            git add .
            git commit -m "automated commit"
            git push origin master
    """
    try:
        click.secho("Adding all changes...", fg="cyan")
        subprocess.run(["git", "add", "."], check=True)

        click.secho("Committing with message 'automated commit'...", fg="cyan")
        subprocess.run(["git", "commit", "-m", "automated commit"], check=True)

        click.secho("Pushing to origin master...", fg="cyan")
        subprocess.run(["git", "push", "origin", "master"], check=True)

        click.secho("✅ Git workflow completed successfully!", fg="green")

    except FileNotFoundError:
        click.secho("❌ Git is not installed or not in your PATH. Please install Git and try again.", fg="red")
        raise click.Abort()

    except subprocess.CalledProcessError as e:
        click.secho(f"❌ Failed to complete Git workflow: {e}", fg="red")
        click.secho("A Git command failed. Please check your repository status and try the commands manually.", fg="red")
        raise click.Abort()



if __name__ == "__main__":
    cli()

import click
from fasterapi.scaffolder.generate_project import create_project
from fasterapi.scaffolder.generate_crud import create_crud_file
from fasterapi.scaffolder.generate_schema import create_schema_file
from fasterapi.scaffolder.generate_service import create_service_file
from fasterapi.scaffolder.generate_route import create_route_file,get_highest_numbered_api_version,get_latest_modified_api_version
from fasterapi.__version__ import __version__
from fasterapi.scaffolder.mount_routes import update_main_routes
from fasterapi.scaffolder.generate_tokens_repo import create_token_file
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
    """Generate CRUD repository functions for a schema."""
    create_crud_file(name)
    
@cli.command()
@click.argument("name")
def make_schema(name):
    """Generate Pydantic classes templates for a schema."""
    create_schema_file(name)
    

@cli.command()
@click.argument("name")
def make_service(name):
    """Generates Python services templates to interact with schema and repository."""
    create_service_file(name)
    

@cli.command()
def mount():
    """Updates the main file with routes from the api/v system."""
    update_main_routes()
    
@cli.command()
def run_d():
    """runs the dev environment using the normal uvicorn way"""
    subprocess.run(["uvicorn", "main:app", "--reload"])

@cli.command()
def update():
    """Upgrades a pip package to the latest version"""
    try:
        subprocess.run(["pip", "install", "nats-fasterapi","--upgrade", ], check=True)
        click.secho(f"✅ Fasterapi is now even faster", fg="green")
    except subprocess.CalledProcessError:
        click.secho(f"❌ Failed to speed up fasterapi'", fg="red", err=True)

@cli.command()
@click.argument("name")
@click.option(
    "--version-mode",
    type=click.Choice(["latest-modified", "highest-number"], case_sensitive=True),
    prompt="Select version mode (latest-modified / highest-number)",
    help="Choose whether to use the latest modified version or the highest numbered version"
)
def make_route(name,version_mode):
    """Generate Route function based on templates and examples in schema and services"""
    if version_mode == "latest-modified":
        version = get_latest_modified_api_version()
    else:
        version = get_highest_numbered_api_version()
        
    print(f"Selected API version: {version}")
    create_route_file(name,version)
    
 
@cli.command()
@click.argument("roles", nargs=-1)
def make_token_repo(roles):
    """Generates token repository based on roles (e.g., admin, user, staff). by default will generate for admin and user role always"""
    if not roles:
        # Default roles if none provided
        roles = ["admin",  "user", ]
        click.secho("⚠️ No roles provided. Using default roles: admin, staff, user, guest-editor", fg="yellow")

    create_token_file(roles)
    click.secho("✅ Token repository generated successfully!", fg="green")


if __name__ == "__main__":
    cli()

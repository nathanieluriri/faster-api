import click
from fasterapi.scaffolder.generate_project import create_project
from fasterapi.scaffolder.generate_crud import create_crud_file
from fasterapi.scaffolder.generate_schema import create_schema_file
from fasterapi.scaffolder.generate_service import create_service_file
from fasterapi.scaffolder.generate_route import create_route_file,get_highest_numbered_api_version,get_latest_modified_api_version
from fasterapi.__version__ import __version__
from fasterapi.scaffolder.mount_routes import update_main_routes
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
    subprocess.run(["uvicorn", "app.main:app", "--reload"])

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

if __name__ == "__main__":
    cli()

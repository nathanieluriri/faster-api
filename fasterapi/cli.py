import click
from fasterapi.scaffolder.generate_project import create_project, create_project_in_current_directory
from fasterapi.scaffolder.generate_crud import create_crud_file
from fasterapi.scaffolder.generate_schema import create_schema_file
from fasterapi.scaffolder.generate_service import create_service_file
from fasterapi.scaffolder.generate_route import create_route_file,get_highest_numbered_api_version,get_latest_modified_api_version
from fasterapi.__version__ import __version__
from fasterapi.scaffolder.mount_routes import update_main_routes
from fasterapi.scaffolder.generate_tokens_repo import create_token_file
from fasterapi.scaffolder.generate_account import create_account_files
from fasterapi.scaffolder.split_user_roles import (
    current_account_roles,
    run_split_user_wizard,
    run_unsplit_user_wizard,
)
from fasterapi.scaffolder.project_python import project_python
from fasterapi.scaffolder.email_templates import (
    add_email_template,
    mount_custom_email_templates,
    mount_email_templates,
)
from fasterapi.scaffolder.database_setup import BACKENDS, use_database
from fasterapi.scaffolder import deploy as deploy_tools
from pathlib import Path
import shutil
import subprocess
import sys

@click.group()
@click.version_option(__version__, '--version', '-v', message='FasterAPI version %(version)s')
def cli():
    """⚡ FasterAPI CLI — Scaffold FastAPI apps with ease"""
    pass


DB_OPTION = click.option(
    "--db",
    type=click.Choice(BACKENDS),
    default="mongodb",
    show_default=True,
    help="Database backend. 'supabase' is Postgres through Supabase's connection pooler.",
)
DEPLOY_OPTION = click.option(
    "--deploy",
    type=click.Choice(deploy_tools.TARGETS),
    default=None,
    help="Also prepare the project for Vercel or Google Cloud Run.",
)


def _finish_new_project(project, db, deploy):
    if db != "mongodb" and not use_database(db, project):
        raise click.Abort()
    if deploy and not deploy_tools.init_target(deploy, project):
        raise click.Abort()


@cli.command()
@click.argument("name")
@DB_OPTION
@DEPLOY_OPTION
def new(name, db, deploy):
    """Create a new FastAPI project.

    \b
    Examples:
        fasterapi new shop
        fasterapi new shop --db supabase --deploy vercel
        fasterapi new shop --db postgres --deploy cloudrun
    """
    if not create_project(name):
        raise click.Abort()
    _finish_new_project(Path.cwd() / name, db, deploy)


@cli.command(name="new-here")
@DB_OPTION
@DEPLOY_OPTION
def new_here(db, deploy):
    """Create a new FastAPI project in the current directory."""
    if not create_project_in_current_directory():
        raise click.Abort()
    _finish_new_project(Path.cwd(), db, deploy)


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
    if not create_crud_file(name):
        raise click.Abort()
    
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
    if not create_schema_file(name):
        raise click.Abort()
    

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
    result = create_service_file(name)
    if not result:
        raise click.Abort()


@cli.command(name="make-account")
@click.argument("name")
def make_account(name):
    """
    Generate a full account scaffold (schema, repo, service, route) based on the user template.

    \b
    ✅ Good usage:
        fasterapi make-account customer
        fasterapi make-account client

    Notes:
        - Copies the built-in user account (signup, login, refresh, Google OAuth,
          profile, account deletion) and renames it.
        - Wires the new role into tokens, auth, permission checks and rate limits,
          and keeps it through split-user and unsplit-user.
    """
    if not create_account_files(name):
        raise click.Abort()


@cli.command(name="split-user")
@click.option(
    "--force",
    is_flag=True,
    help="Override conflict-marker safety checks and continue conversion.",
)
def split_user(force):
    """
    Interactively split the canonical user role into multiple custom roles.
    """
    if not run_split_user_wizard(force=force):
        raise click.Abort()


@cli.command(name="unsplit-user")
@click.option(
    "--force",
    is_flag=True,
    help="Override conflict-marker safety checks and continue conversion.",
)
def unsplit_user(force):
    """
    Collapse split custom roles back to a single canonical user role.
    """
    if not run_unsplit_user_wizard(force=force):
        raise click.Abort()
    
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
            python -m uvicorn main:app --reload
        - Uses the active virtualenv, or a .venv/venv folder in the project, so the
          app runs with the project's own dependencies.
    """
    process = subprocess.Popen([project_python(), "-m", "uvicorn", "main:app", "--reload"])
    try:
        return_code = process.wait()
    except KeyboardInterrupt:
        # Uvicorn got the same Ctrl+C; let it finish shutting down instead of killing it.
        return_code = process.wait()
    if return_code not in (0, -2, 130):
        click.secho("❌ The server exited with an error. Is uvicorn installed in the project environment?", fg="red")
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
        - This will run pip for the Python that runs this CLI:
            python -m pip install --upgrade nats-fasterapi
    """
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "nats-fasterapi"],
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

    try:
        if version_mode == "latest-modified":
            version = get_latest_modified_api_version()
        else:  # "highest-number"
            version = get_highest_numbered_api_version()
    except FileNotFoundError as e:
        click.secho(f"❌ {e}", fg="red")
        click.secho("💡 Run this from your project root, which needs an api/v1 folder.", fg="yellow")
        raise click.Abort()

    click.secho(f"📌 Selected API version: {version}", fg="cyan")
    if not create_route_file(name, version):
        raise click.Abort()
    click.secho(f"✅ Route for '{name}' created successfully.", fg="green")

 
@cli.command()
@click.argument("roles", nargs=-1)
@click.option("--force", is_flag=True, help="Replace an existing repositories/tokens_repo.py (a .bak copy is kept).")
def make_token_repo(roles, force):
    """
    Generate repositories/tokens_repo.py with token helpers for each role.

    \b
    ✅ Good usage:
        fasterapi make-token-repo --force                  # the project's current roles
        fasterapi make-token-repo admin user support --force

    ❌ Bad usage:
        fasterapi make-token-repo admin 1 @!               # invalid role names

    Notes:
        - Without ROLES, uses the project's current roles: admin, user (or its
          split-user roles) and any make-account roles.
        - Role names are lowercase letters, digits and underscores ("-" becomes "_").
    """
    if not roles:
        roles = ["admin", *current_account_roles(Path.cwd())]
        click.secho(f"ℹ️ Using the project's roles: {', '.join(roles)}", fg="cyan")

    target = Path.cwd() / "repositories" / "tokens_repo.py"
    if target.exists() and not force:
        click.secho(
            "❌ repositories/tokens_repo.py already exists. Re-run with --force to replace it (a .bak copy is kept).",
            fg="red",
        )
        raise click.Abort()

    backup = target.with_name("tokens_repo.py.bak")
    if target.exists():
        shutil.copy2(target, backup)
    try:
        create_token_file(list(roles))
    except ValueError as e:
        click.secho(f"❌ {e}", fg="red")
        raise click.Abort()


@cli.group()
def email():
    """
    Manage email templates and email template mounting.
    """
    pass


@email.command(name="add-template")
@click.option(
    "--template-key",
    required=False,
    help="Optional template key for non-interactive use.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite destination template if it already exists.",
)
def email_add_template(template_key, force):
    """
    Add one of the built-in email template examples into email_templates/.
    """
    if not add_email_template(template_key=template_key, force=force):
        raise click.Abort()


@email.command(name="mount")
def email_mount():
    """
    Mount templates in email_templates/ into core/email/mounted_templates.py.
    """
    if not mount_email_templates():
        raise click.Abort()


@email.command(name="mount-custom")
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing template files in email_templates/ while moving custom templates.",
)
def email_mount_custom(force):
    """
    Move custom_templates/*.py into email_templates/ and mount all templates.
    """
    if not mount_custom_email_templates(force=force):
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
            git push origin <current branch>
    """
    try:
        click.secho("Adding all changes...", fg="cyan")
        subprocess.run(["git", "add", "."], check=True)

        click.secho("Committing with message 'automated commit'...", fg="cyan")
        subprocess.run(["git", "commit", "-m", "automated commit"], check=True)

        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()
        click.secho(f"Pushing to origin {branch}...", fg="cyan")
        subprocess.run(["git", "push", "origin", branch], check=True)

        click.secho("✅ Git workflow completed successfully!", fg="green")

    except FileNotFoundError:
        click.secho("❌ Git is not installed or not in your PATH. Please install Git and try again.", fg="red")
        raise click.Abort()

    except subprocess.CalledProcessError as e:
        click.secho(f"❌ Failed to complete Git workflow: {e}", fg="red")
        click.secho("A Git command failed. Please check your repository status and try the commands manually.", fg="red")
        raise click.Abort()



@cli.group()
def db():
    """
    Choose the project's database backend.
    """
    pass


@db.command(name="use")
@click.argument("backend", type=click.Choice(BACKENDS))
def db_use(backend):
    """
    Switch the current project to MongoDB, Postgres or Supabase.

    \b
    Examples:
        fasterapi db use postgres
        fasterapi db use supabase

    Notes:
        - Updates DB_TYPE in .env/.env.example and adds asyncpg to requirements.txt.
        - Existing repositories keep working: the Postgres backend speaks the same
          MongoDB-style API (tables are created automatically).
    """
    if not use_database(backend):
        raise click.Abort()


@cli.group()
def deploy():
    """
    Prepare, check and deploy to Vercel or Google Cloud Run.
    """
    pass


TARGET_ARGUMENT = click.argument("target", type=click.Choice(deploy_tools.TARGETS))
ENV_FILE_OPTION = click.option("--env-file", default=None, help="Env file to read (default: .env, then .env.example).")


@deploy.command(name="check")
@click.option("--target", type=click.Choice(deploy_tools.TARGETS), required=True, help="Platform to check against.")
@ENV_FILE_OPTION
def deploy_check(target, env_file):
    """
    Report features and settings that won't work on the target platform.

    \b
    Examples:
        fasterapi deploy check --target vercel
        fasterapi deploy check --target cloudrun --env-file .env.production

    Exits with status 1 when blocking errors are found, so it can run in CI.
    """
    findings, env_name = deploy_tools.check_project(target, env_file=env_file)
    if not deploy_tools.print_findings(findings, target, env_name):
        raise SystemExit(1)


@deploy.command(name="init")
@TARGET_ARGUMENT
@click.option("--force", is_flag=True, help="Overwrite existing deployment files (backups are kept as .bak).")
def deploy_init(target, force):
    """
    Add the files a platform needs (vercel.json, or a Cloud Run ready Dockerfile).

    \b
    Examples:
        fasterapi deploy init vercel
        fasterapi deploy init cloudrun
    """
    if not deploy_tools.init_target(target, force=force):
        raise click.Abort()


@deploy.command(name="vercel")
@click.option("--prod", is_flag=True, help="Deploy to production instead of a preview URL.")
@click.option("--push-env", is_flag=True, help="Upload env vars from the env file with 'vercel env add'.")
@ENV_FILE_OPTION
@click.option("--dry-run", is_flag=True, help="Print the commands without running them.")
@click.option("--force", is_flag=True, help="Deploy even if the check finds errors.")
def deploy_vercel(prod, push_env, env_file, dry_run, force):
    """
    Check the project, then deploy it with the Vercel CLI.

    \b
    Examples:
        fasterapi deploy vercel --dry-run
        fasterapi deploy vercel --prod --push-env
    """
    if not deploy_tools.deploy_vercel(prod=prod, push_env=push_env, env_file=env_file, dry_run=dry_run, force=force):
        raise click.Abort()


@deploy.command(name="cloudrun")
@click.option("--service", required=True, help="Cloud Run service name.")
@click.option("--region", default="us-central1", show_default=True, help="Region (Tier 1 regions are cheapest).")
@click.option("--project", "gcp_project", default=None, help="Google Cloud project ID (default: gcloud config).")
@ENV_FILE_OPTION
@click.option("--allow-unauthenticated/--no-allow-unauthenticated", default=True, show_default=True, help="Make the API public.")
@click.option("--min-instances", default=0, show_default=True, help="0 scales to zero so idle time is free.")
@click.option("--max-instances", default=3, show_default=True, help="Caps scale-out to cap cost.")
@click.option("--memory", default="512Mi", show_default=True)
@click.option("--cpu", default="1", show_default=True)
@click.option("--dry-run", is_flag=True, help="Print the gcloud command without running it.")
@click.option("--force", is_flag=True, help="Deploy even if the check finds errors.")
def deploy_cloudrun(service, region, gcp_project, env_file, allow_unauthenticated, min_instances, max_instances, memory, cpu, dry_run, force):
    """
    Check the project, then build and deploy it to Google Cloud Run from source.

    \b
    Examples:
        fasterapi deploy cloudrun --service my-api --dry-run
        fasterapi deploy cloudrun --service my-api --region europe-west1 --project my-gcp-project

    Notes:
        - Uses 'gcloud run deploy --source .', which builds the Dockerfile with Cloud Build.
        - Env vars come from the env file; empty values and Cloud Run reserved names are skipped.
    """
    if not deploy_tools.deploy_cloudrun(
        service=service,
        region=region,
        gcp_project=gcp_project,
        env_file=env_file,
        allow_unauthenticated=allow_unauthenticated,
        min_instances=min_instances,
        max_instances=max_instances,
        memory=memory,
        cpu=cpu,
        dry_run=dry_run,
        force=force,
    ):
        raise click.Abort()


if __name__ == "__main__":
    cli()

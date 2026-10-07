"""
Lost & Found CLI - Main Entry Point

A command-line interface for interacting with the Lost & Found backend API.
"""

import click
from rich.console import Console

import sys
import os

# Add parent directory to path for relative imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli import __version__
from cli.commands.auth import auth_group
from cli.commands.items import items_group
from cli.commands.matches import matches_group
from cli.commands.notifications import notifications_group
from cli.commands.config import config_group


console = Console()


LOGO = """
╔═══════════════════════════════════════════════════════════╗
║     _               _    ___    ___                  _    ║
║    | |   ___  ___  | |_ ( _ )  | __|___  _  _ _ _  __| |   ║
║    | |__/ _ \\(_-<  |  _|/ _ \\  | _/ _ \\| || | ' \\/ _` |   ║
║    |____\\___//__/   \\__|\\___/  |_|\\___/ \\_,_|_||_\\__,_|   ║
║                                                           ║
║              CLI Tool for Lost & Found API                ║
╚═══════════════════════════════════════════════════════════╝
"""


@click.group()
@click.version_option(version=__version__, prog_name="Lost & Found CLI")
@click.pass_context
def cli(ctx):
    """
    Lost & Found CLI - Manage lost and found items from the command line.
    
    \b
    Quick Start:
      1. Configure API URL:  lf config set-url http://localhost:8000
      2. Register account:   lf auth register
      3. Login:              lf auth login
      4. Create item:        lf items create --type phone --lost --title "My Phone" ...
      5. Upload image:       lf items upload-image <item-id> photo.jpg
      6. Find matches:       lf matches find <item-id>
    
    \b
    Use 'lf <command> --help' for more information on a command.
    """
    ctx.ensure_object(dict)


# Register command groups
cli.add_command(auth_group)
cli.add_command(items_group)
cli.add_command(matches_group)
cli.add_command(notifications_group)
cli.add_command(config_group)


# Convenience aliases for common commands
@cli.command(name="login")
@click.option("--email", "-e", required=True, prompt=True, help="Email address")
@click.option("--password", "-p", required=True, prompt=True, hide_input=True, help="Password")
@click.pass_context
def login_shortcut(ctx, email, password):
    """Shortcut for 'auth login'."""
    ctx.invoke(auth_group.commands['login'], email=email, password=password)


@cli.command(name="logout")
@click.pass_context
def logout_shortcut(ctx):
    """Shortcut for 'auth logout'."""
    ctx.invoke(auth_group.commands['logout'])


@cli.command(name="status")
@click.pass_context
def status_shortcut(ctx):
    """Shortcut for 'auth status'."""
    ctx.invoke(auth_group.commands['status'])


@cli.command(name="whoami")
@click.pass_context
def whoami_shortcut(ctx):
    """Shortcut for 'auth profile'."""
    ctx.invoke(auth_group.commands['profile'])


@cli.command(name="banner")
def show_banner():
    """Show the CLI banner."""
    console.print(LOGO, style="bold cyan")
    console.print(f"  Version: {__version__}", style="dim")
    console.print("  https://github.com/your-repo/lost-and-found\n", style="dim")


def main():
    """Main entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled.[/yellow]")
        raise SystemExit(130)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

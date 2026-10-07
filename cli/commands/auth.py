"""
Authentication Commands

Commands for user registration, login, and logout.
"""

import click
from rich.console import Console
from rich.table import Table

from cli.api_client import APIClient, APIError
from cli.config import TokenData, CLIConfig


console = Console()


@click.group(name="auth")
def auth_group():
    """Authentication commands (login, register, logout)."""
    pass


@auth_group.command(name="register")
@click.option("--email", "-e", required=True, prompt=True, help="Email address")
@click.option("--password", "-p", required=True, prompt=True, hide_input=True, 
              confirmation_prompt=True, help="Password (min 8 characters)")
@click.option("--name", "-n", default=None, help="Full name")
@click.option("--phone", default=None, help="Phone number")
def register(email: str, password: str, name: str, phone: str):
    """Register a new user account."""
    try:
        client = APIClient()
        result = client.register(
            email=email,
            password=password,
            full_name=name,
            phone_number=phone
        )
        
        console.print("\n[bold green]✓ Registration successful![/bold green]")
        console.print(f"  User ID: {result['id']}")
        console.print(f"  Email: {result['email']}")
        if result.get('full_name'):
            console.print(f"  Name: {result['full_name']}")
        console.print("\n[dim]You can now login with 'lf auth login'[/dim]")
        
    except APIError as e:
        console.print(f"[bold red]✗ Registration failed:[/bold red] {e.detail}")
        raise SystemExit(1)


@auth_group.command(name="login")
@click.option("--email", "-e", required=True, prompt=True, help="Email address")
@click.option("--password", "-p", required=True, prompt=True, hide_input=True, help="Password")
def login(email: str, password: str):
    """Login to your account."""
    try:
        client = APIClient()
        result = client.login(email=email, password=password)
        
        # Save token
        token = TokenData(
            access_token=result["access_token"],
            token_type=result.get("token_type", "bearer"),
            expires_in=result.get("expires_in", 1800)
        )
        token.save()
        
        console.print("\n[bold green]✓ Login successful![/bold green]")
        console.print(f"  Token expires in: {result.get('expires_in', 1800) // 60} minutes")
        console.print("\n[dim]You can now use all CLI commands.[/dim]")
        
    except APIError as e:
        console.print(f"[bold red]✗ Login failed:[/bold red] {e.detail}")
        raise SystemExit(1)


@auth_group.command(name="logout")
def logout():
    """Logout and clear stored credentials."""
    TokenData.delete()
    console.print("[bold green]✓ Logged out successfully![/bold green]")


@auth_group.command(name="status")
def status():
    """Check authentication status."""
    token = TokenData.load()
    config = CLIConfig.load()
    
    if token:
        console.print("[bold green]✓ Logged in[/bold green]")
        console.print(f"  API URL: {config.api_url}")
        
        # Try to get profile
        try:
            client = APIClient()
            profile = client.get_profile()
            console.print(f"  Email: {profile['email']}")
            if profile.get('full_name'):
                console.print(f"  Name: {profile['full_name']}")
        except APIError:
            console.print("  [dim](Could not fetch profile - token may be expired)[/dim]")
    else:
        console.print("[bold yellow]✗ Not logged in[/bold yellow]")
        console.print(f"  API URL: {config.api_url}")
        console.print("\n[dim]Run 'lf auth login' to authenticate.[/dim]")


@auth_group.command(name="profile")
def profile():
    """View your user profile."""
    try:
        client = APIClient()
        result = client.get_profile()
        
        table = Table(title="User Profile", show_header=False)
        table.add_column("Field", style="cyan")
        table.add_column("Value")
        
        table.add_row("ID", result['id'])
        table.add_row("Email", result['email'])
        table.add_row("Name", result.get('full_name') or "[dim]Not set[/dim]")
        table.add_row("Active", "Yes" if result['is_active'] else "No")
        table.add_row("Verified", "Yes" if result['is_verified'] else "No")
        table.add_row("Created", result['created_at'])
        
        console.print(table)
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)


@auth_group.command(name="update-profile")
@click.option("--name", "-n", default=None, help="Update full name")
@click.option("--phone", default=None, help="Update phone number")
def update_profile(name: str, phone: str):
    """Update your profile information."""
    if not name and not phone:
        console.print("[yellow]No updates specified. Use --name or --phone.[/yellow]")
        return
    
    try:
        client = APIClient()
        result = client.update_profile(full_name=name, phone_number=phone)
        
        console.print("[bold green]✓ Profile updated![/bold green]")
        console.print(f"  Name: {result.get('full_name') or '[dim]Not set[/dim]'}")
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)


@auth_group.command(name="delete-account")
@click.confirmation_option(
    prompt="Are you sure you want to delete your account? This cannot be undone!"
)
def delete_account():
    """Delete your account permanently."""
    try:
        client = APIClient()
        client.delete_account()
        TokenData.delete()
        
        console.print("[bold green]✓ Account deleted successfully.[/bold green]")
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)

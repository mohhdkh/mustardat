"""
Configuration Commands

Commands for managing CLI configuration.
"""

import click
from rich.console import Console
from rich.table import Table

from cli.config import CLIConfig, CONFIG_FILE, TOKEN_FILE
from cli.api_client import APIClient, APIError


console = Console()


@click.group(name="config")
def config_group():
    """Manage CLI configuration."""
    pass


@config_group.command(name="show")
def show_config():
    """Show current configuration."""
    config = CLIConfig.load()
    
    table = Table(title="CLI Configuration", show_header=False)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    
    table.add_row("Base URL", config.base_url)
    table.add_row("API Prefix", config.api_prefix)
    table.add_row("Full API URL", config.api_url)
    table.add_row("Timeout", f"{config.timeout} seconds")
    table.add_row("Config File", str(CONFIG_FILE))
    table.add_row("Token File", str(TOKEN_FILE))
    
    console.print(table)


@config_group.command(name="set-url")
@click.argument("url")
def set_url(url):
    """Set the backend API URL."""
    config = CLIConfig.load()
    
    # Remove trailing slash
    url = url.rstrip("/")
    
    config.base_url = url
    config.save()
    
    console.print(f"[bold green]✓ API URL set to:[/bold green] {url}")
    console.print(f"[dim]Full API URL: {config.api_url}[/dim]")


@config_group.command(name="set-timeout")
@click.argument("seconds", type=int)
def set_timeout(seconds):
    """Set the request timeout in seconds."""
    if seconds < 1:
        console.print("[red]Timeout must be at least 1 second.[/red]")
        raise SystemExit(1)
    
    config = CLIConfig.load()
    config.timeout = seconds
    config.save()
    
    console.print(f"[bold green]✓ Timeout set to:[/bold green] {seconds} seconds")


@config_group.command(name="reset")
@click.confirmation_option(prompt="Reset configuration to defaults?")
def reset_config():
    """Reset configuration to defaults."""
    config = CLIConfig()
    config.save()
    
    console.print("[bold green]✓ Configuration reset to defaults.[/bold green]")


@config_group.command(name="test")
def test_connection():
    """Test connection to the backend API."""
    config = CLIConfig.load()
    
    console.print(f"Testing connection to: {config.base_url}")
    
    try:
        client = APIClient(config)
        
        with console.status("[bold blue]Connecting...[/bold blue]"):
            result = client.health_check()
        
        console.print("\n[bold green]✓ Connection successful![/bold green]")
        console.print(f"  Status: {result.get('status', 'N/A')}")
        console.print(f"  Version: {result.get('version', 'N/A')}")
        console.print(f"  Environment: {result.get('environment', 'N/A')}")
        
    except APIError as e:
        console.print(f"\n[bold red]✗ Connection failed:[/bold red] {e.detail}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"\n[bold red]✗ Connection failed:[/bold red] {str(e)}")
        console.print("\n[dim]Make sure the backend server is running.[/dim]")
        raise SystemExit(1)

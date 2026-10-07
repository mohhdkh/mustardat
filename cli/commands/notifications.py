"""
Notification Commands

Commands for viewing and managing notifications.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from cli.api_client import APIClient, APIError


console = Console()


@click.group(name="notifications")
def notifications_group():
    """Manage notifications."""
    pass


@notifications_group.command(name="list")
@click.option("--unread", "-u", is_flag=True, help="Show only unread notifications")
@click.option("--page", "-p", default=1, type=int, help="Page number")
@click.option("--size", default=20, type=int, help="Items per page")
def list_notifications(unread, page, size):
    """List your notifications."""
    try:
        client = APIClient()
        result = client.list_notifications(
            unread_only=unread,
            page=page,
            page_size=size
        )
        
        notifications = result.get('notifications', [])
        
        if not notifications:
            console.print("[yellow]No notifications found.[/yellow]")
            return
        
        # Show unread count
        unread_count = result.get('unread_count', 0)
        if unread_count > 0:
            console.print(f"[bold cyan]📬 {unread_count} unread notification(s)[/bold cyan]\n")
        
        table = Table(title="Notifications")
        table.add_column("", max_width=2)  # Read indicator
        table.add_column("ID", style="dim", max_width=8)
        table.add_column("Type", style="cyan")
        table.add_column("Title")
        table.add_column("Date")
        
        for notif in notifications:
            read_indicator = "  " if notif['is_read'] else "🔵"
            
            table.add_row(
                read_indicator,
                notif['id'][:8],
                notif.get('notification_type', 'N/A'),
                notif.get('title', 'N/A')[:40],
                notif['created_at'][:16]
            )
        
        console.print(table)
        console.print(f"\n[dim]Total: {result.get('total', 0)} notifications[/dim]")
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)


@notifications_group.command(name="get")
@click.argument("notification_id")
def get_notification(notification_id):
    """View a specific notification."""
    try:
        client = APIClient()
        notif = client.get_notification(notification_id)
        
        read_status = "Read" if notif['is_read'] else "Unread"
        
        content = f"""
[bold]Type:[/bold] {notif.get('notification_type', 'N/A')}
[bold]Status:[/bold] {read_status}

[bold]Title:[/bold]
{notif.get('title', 'N/A')}

[bold]Message:[/bold]
{notif.get('message', 'N/A')}

[bold]Created:[/bold] {notif['created_at']}
"""
        
        if notif.get('read_at'):
            content += f"[bold]Read at:[/bold] {notif['read_at']}\n"
        
        if notif.get('match_id'):
            content += f"\n[bold]Related Match:[/bold] {notif['match_id']}"
        
        panel = Panel(
            content.strip(),
            title=f"Notification: {notif['id'][:8]}...",
            border_style="blue" if notif['is_read'] else "cyan"
        )
        console.print(panel)
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)


@notifications_group.command(name="read")
@click.argument("notification_ids", nargs=-1, required=True)
def mark_read(notification_ids):
    """Mark notification(s) as read."""
    try:
        client = APIClient()
        result = client.mark_notifications_read(list(notification_ids))
        
        console.print(f"[bold green]✓ {result.get('updated_count', 0)} notification(s) marked as read.[/bold green]")
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)


@notifications_group.command(name="read-all")
def mark_all_read():
    """Mark all notifications as read."""
    try:
        client = APIClient()
        result = client.mark_all_notifications_read()
        
        console.print(f"[bold green]✓ {result.get('updated_count', 0)} notification(s) marked as read.[/bold green]")
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)


@notifications_group.command(name="delete")
@click.argument("notification_id")
@click.confirmation_option(prompt="Are you sure you want to delete this notification?")
def delete_notification(notification_id):
    """Delete a notification."""
    try:
        client = APIClient()
        client.delete_notification(notification_id)
        
        console.print("[bold green]✓ Notification deleted.[/bold green]")
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)

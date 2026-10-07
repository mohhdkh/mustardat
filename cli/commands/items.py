"""
Item Management Commands

Commands for creating, listing, updating, and deleting lost/found items.
"""

import click
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from cli.api_client import APIClient, APIError


console = Console()

# Valid item types
ITEM_TYPES = [
    "phone", "wallet", "keys", "bag", "laptop", "tablet", "watch",
    "jewelry", "glasses", "headphones", "camera", "documents",
    "pet", "clothing", "electronics", "other"
]

ITEM_STATUSES = ["active", "matched", "resolved", "expired", "cancelled"]


@click.group(name="items")
def items_group():
    """Manage lost and found items."""
    pass


@items_group.command(name="create")
@click.option("--type", "-t", "item_type", required=True, 
              type=click.Choice(ITEM_TYPES, case_sensitive=False),
              help="Item category")
@click.option("--lost/--found", "is_lost", default=True,
              help="Whether item was lost or found")
@click.option("--title", required=True, help="Brief title for the item")
@click.option("--description", "-d", default=None, help="Detailed description")
@click.option("--lat", "latitude", required=True, type=float, 
              help="Latitude where item was lost/found")
@click.option("--lng", "longitude", required=True, type=float,
              help="Longitude where item was lost/found")
@click.option("--location", "-l", "location_name", default=None,
              help="Human-readable location name")
@click.option("--date", "event_date", required=True,
              help="Date/time when item was lost/found (ISO format: YYYY-MM-DDTHH:MM:SS)")
def create_item(item_type, is_lost, title, description, latitude, longitude, 
                location_name, event_date):
    """Create a new lost or found item listing."""
    try:
        # Parse date
        try:
            parsed_date = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
            date_str = parsed_date.isoformat()
        except ValueError:
            console.print("[red]Invalid date format. Use ISO format: YYYY-MM-DDTHH:MM:SS[/red]")
            raise SystemExit(1)
        
        client = APIClient()
        result = client.create_item(
            item_type=item_type.lower(),
            lost_or_found="lost" if is_lost else "found",
            title=title,
            description=description,
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            event_date=date_str
        )
        
        console.print("\n[bold green]✓ Item created successfully![/bold green]")
        console.print(f"  ID: {result['id']}")
        console.print(f"  Title: {result['title']}")
        console.print(f"  Type: {result['item_type']}")
        console.print(f"  Status: {'Lost' if is_lost else 'Found'}")
        console.print("\n[dim]Upload images with: lf items upload-image <item-id> <file>[/dim]")
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)


@items_group.command(name="list")
@click.option("--type", "-t", "item_type", default=None,
              type=click.Choice(ITEM_TYPES, case_sensitive=False),
              help="Filter by item type")
@click.option("--filter", "-f", "filter_type", default=None,
              type=click.Choice(["lost", "found"], case_sensitive=False),
              help="Filter by lost or found")
@click.option("--status", "-s", default=None,
              type=click.Choice(ITEM_STATUSES, case_sensitive=False),
              help="Filter by status")
@click.option("--page", "-p", default=1, type=int, help="Page number")
@click.option("--size", default=20, type=int, help="Items per page")
def list_items(item_type, filter_type, status, page, size):
    """List your items."""
    try:
        client = APIClient()
        
        result = client.list_items(
            item_type=item_type.lower() if item_type else None,
            lost_or_found=filter_type.lower() if filter_type else None,
            status=status.lower() if status else None,
            page=page,
            page_size=size
        )
        
        if not result['items']:
            console.print("[yellow]No items found.[/yellow]")
            return
        
        table = Table(title=f"Your Items (Page {result['page']}/{result['total_pages']})")
        table.add_column("ID", style="dim", max_width=8)
        table.add_column("Type", style="cyan")
        table.add_column("L/F", style="magenta")
        table.add_column("Title")
        table.add_column("Status", style="green")
        table.add_column("Images", justify="center")
        table.add_column("Date")
        
        for item in result['items']:
            table.add_row(
                item['id'][:8],
                item['item_type'],
                "Lost" if item['lost_or_found'] == "lost" else "Found",
                item['title'][:30] + ("..." if len(item['title']) > 30 else ""),
                item['status'],
                str(len(item.get('images', []))),
                item['event_date'][:10]
            )
        
        console.print(table)
        console.print(f"\n[dim]Total: {result['total']} items[/dim]")
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)


@items_group.command(name="get")
@click.argument("item_id")
def get_item(item_id):
    """Get details of a specific item."""
    try:
        client = APIClient()
        item = client.get_item(item_id)
        
        # Create a nice panel with item details
        content = f"""
[bold]Title:[/bold] {item['title']}
[bold]Type:[/bold] {item['item_type']}
[bold]Status:[/bold] {item['status']}
[bold]Lost/Found:[/bold] {item['lost_or_found'].capitalize()}

[bold]Description:[/bold]
{item.get('description') or '[dim]No description[/dim]'}

[bold]Location:[/bold]
  Name: {item.get('location_name') or '[dim]Not specified[/dim]'}
  Coordinates: {item['latitude']}, {item['longitude']}

[bold]Event Date:[/bold] {item['event_date']}
[bold]Created:[/bold] {item['created_at']}
[bold]Updated:[/bold] {item['updated_at']}

[bold]Images:[/bold] {len(item.get('images', []))} uploaded
"""
        
        panel = Panel(
            content.strip(),
            title=f"Item: {item['id']}",
            border_style="blue"
        )
        console.print(panel)
        
        # Show images if any
        if item.get('images'):
            console.print("\n[bold]Images:[/bold]")
            for img in item['images']:
                status = "✓ Processed" if img['is_processed'] else "⏳ Processing"
                console.print(f"  - {img['id'][:8]} ({status})")
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)


@items_group.command(name="update")
@click.argument("item_id")
@click.option("--title", default=None, help="Update title")
@click.option("--description", "-d", default=None, help="Update description")
@click.option("--lat", "latitude", default=None, type=float, help="Update latitude")
@click.option("--lng", "longitude", default=None, type=float, help="Update longitude")
@click.option("--location", "-l", "location_name", default=None, help="Update location name")
@click.option("--status", "-s", default=None,
              type=click.Choice(ITEM_STATUSES, case_sensitive=False),
              help="Update status")
def update_item(item_id, title, description, latitude, longitude, location_name, status):
    """Update an existing item."""
    updates = {}
    if title:
        updates["title"] = title
    if description:
        updates["description"] = description
    if latitude is not None:
        updates["latitude"] = latitude
    if longitude is not None:
        updates["longitude"] = longitude
    if location_name:
        updates["location_name"] = location_name
    if status:
        updates["status"] = status.lower()
    
    if not updates:
        console.print("[yellow]No updates specified.[/yellow]")
        return
    
    try:
        client = APIClient()
        result = client.update_item(item_id, **updates)
        
        console.print("[bold green]✓ Item updated successfully![/bold green]")
        console.print(f"  ID: {result['id']}")
        console.print(f"  Title: {result['title']}")
        console.print(f"  Status: {result['status']}")
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)


@items_group.command(name="delete")
@click.argument("item_id")
@click.confirmation_option(prompt="Are you sure you want to delete this item?")
def delete_item(item_id):
    """Delete an item and all its images."""
    try:
        client = APIClient()
        client.delete_item(item_id)
        
        console.print("[bold green]✓ Item deleted successfully![/bold green]")
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)


# ==========================================
# Image Commands
# ==========================================

@items_group.command(name="upload-image")
@click.argument("item_id")
@click.argument("file_path", type=click.Path(exists=True))
def upload_image(item_id, file_path):
    """Upload an image for an item."""
    try:
        client = APIClient()
        
        with console.status("[bold blue]Uploading image...[/bold blue]"):
            result = client.upload_image(item_id, file_path)
        
        console.print("\n[bold green]✓ Image uploaded successfully![/bold green]")
        console.print(f"  Image ID: {result['id']}")
        console.print(f"  Filename: {result['original_filename']}")
        console.print(f"  Size: {result['file_size'] / 1024:.1f} KB")
        console.print(f"  Processed: {'Yes' if result['is_processed'] else 'No'}")
        console.print(f"  Message: {result.get('message', '')}")
        
    except FileNotFoundError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise SystemExit(1)
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)


@items_group.command(name="list-images")
@click.argument("item_id")
def list_images(item_id):
    """List all images for an item."""
    try:
        client = APIClient()
        images = client.list_images(item_id)
        
        if not images:
            console.print("[yellow]No images found for this item.[/yellow]")
            return
        
        table = Table(title=f"Images for Item {item_id[:8]}...")
        table.add_column("ID", style="dim")
        table.add_column("Filename")
        table.add_column("Size")
        table.add_column("Processed", justify="center")
        table.add_column("Order", justify="center")
        
        for img in images:
            table.add_row(
                img['id'][:8],
                img.get('original_filename', 'N/A'),
                f"{img.get('file_size', 0) / 1024:.1f} KB",
                "✓" if img['is_processed'] else "⏳",
                str(img.get('display_order', 0))
            )
        
        console.print(table)
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)


@items_group.command(name="delete-image")
@click.argument("item_id")
@click.argument("image_id")
@click.confirmation_option(prompt="Are you sure you want to delete this image?")
def delete_image(item_id, image_id):
    """Delete an image from an item."""
    try:
        client = APIClient()
        client.delete_image(item_id, image_id)
        
        console.print("[bold green]✓ Image deleted successfully![/bold green]")
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)

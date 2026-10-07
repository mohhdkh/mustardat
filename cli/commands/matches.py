"""
Match Management Commands

Commands for finding, viewing, and managing matches.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from cli.api_client import APIClient, APIError


console = Console()

MATCH_STATUSES = ["pending", "source_confirmed", "target_confirmed", "both_confirmed", "rejected"]


@click.group(name="matches")
def matches_group():
    """Manage item matches."""
    pass


@matches_group.command(name="find")
@click.argument("item_id")
@click.option("--radius", "-r", default=None, type=float,
              help="Search radius in kilometers (1-500)")
@click.option("--days", "-d", default=None, type=int,
              help="Time range in days (1-365)")
@click.option("--min-score", "-m", default=None, type=float,
              help="Minimum match score (0-1)")
def find_matches(item_id, radius, days, min_score):
    """Find potential matches for an item."""
    try:
        client = APIClient()
        
        with console.status("[bold blue]Searching for matches...[/bold blue]"):
            result = client.find_matches(
                item_id=item_id,
                radius_km=radius,
                time_range_days=days,
                min_score=min_score
            )
        
        matches = result.get('matches', [])
        
        if not matches:
            console.print("[yellow]No matches found.[/yellow]")
            console.print("\n[dim]Try adjusting search parameters:[/dim]")
            console.print("  --radius: Increase search radius")
            console.print("  --days: Extend time range")
            console.print("  --min-score: Lower minimum score threshold")
            return
        
        console.print(f"\n[bold green]Found {len(matches)} potential matches![/bold green]")
        
        # Show search params
        params = result.get('search_params', {})
        console.print(f"\n[dim]Search params: radius={params.get('radius_km')}km, "
                     f"days={params.get('time_range_days')}, "
                     f"min_score={params.get('min_score')}[/dim]")
        
        table = Table(title="Matches")
        table.add_column("ID", style="dim", max_width=8)
        table.add_column("Score", justify="right", style="green")
        table.add_column("Target Item")
        table.add_column("Type")
        table.add_column("Distance")
        table.add_column("Status")
        
        for match in matches:
            target = match.get('target_item', {})
            distance = match.get('distance_km')
            distance_str = f"{distance:.1f} km" if distance else "N/A"
            
            table.add_row(
                match['id'][:8],
                f"{match['overall_score']:.2f}",
                target.get('title', 'N/A')[:25],
                target.get('item_type', 'N/A'),
                distance_str,
                match['status']
            )
        
        console.print(table)
        console.print("\n[dim]Use 'lf matches get <match-id>' to view details[/dim]")
        console.print("[dim]Use 'lf matches confirm <match-id>' to confirm a match[/dim]")
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)


@matches_group.command(name="list")
@click.option("--status", "-s", default=None,
              type=click.Choice(MATCH_STATUSES, case_sensitive=False),
              help="Filter by status")
@click.option("--page", "-p", default=1, type=int, help="Page number")
@click.option("--size", default=20, type=int, help="Items per page")
def list_matches(status, page, size):
    """List all your matches."""
    try:
        client = APIClient()
        matches = client.list_matches(
            status=status,
            page=page,
            page_size=size
        )
        
        if not matches:
            console.print("[yellow]No matches found.[/yellow]")
            return
        
        table = Table(title="Your Matches")
        table.add_column("ID", style="dim", max_width=8)
        table.add_column("Score", justify="right", style="green")
        table.add_column("Source Item")
        table.add_column("Target Item")
        table.add_column("Status", style="cyan")
        table.add_column("Created")
        
        for match in matches:
            source = match.get('source_item', {})
            target = match.get('target_item', {})
            
            table.add_row(
                match['id'][:8],
                f"{match['overall_score']:.2f}",
                source.get('title', 'N/A')[:20],
                target.get('title', 'N/A')[:20],
                match['status'],
                match['created_at'][:10]
            )
        
        console.print(table)
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)


@matches_group.command(name="get")
@click.argument("match_id")
def get_match(match_id):
    """Get details of a specific match."""
    try:
        client = APIClient()
        match = client.get_match(match_id)
        
        source = match.get('source_item', {})
        target = match.get('target_item', {})
        
        # Build detailed view
        content = f"""
[bold]Status:[/bold] {match['status']}
[bold]Overall Score:[/bold] {match['overall_score']:.3f}

[bold cyan]Score Breakdown:[/bold cyan]
  Vector Similarity: {match.get('vector_similarity', 0):.3f}
  pHash Similarity: {match.get('phash_similarity', 0):.3f}
  ORB Match Score: {match.get('orb_match_score', 0):.3f}
  Location Score: {match.get('location_score', 0):.3f}
  Distance: {match.get('distance_km', 'N/A')} km

[bold cyan]Source Item:[/bold cyan]
  ID: {source.get('id', 'N/A')}
  Title: {source.get('title', 'N/A')}
  Type: {source.get('item_type', 'N/A')}
  Lost/Found: {source.get('lost_or_found', 'N/A')}

[bold cyan]Target Item:[/bold cyan]
  ID: {target.get('id', 'N/A')}
  Title: {target.get('title', 'N/A')}
  Type: {target.get('item_type', 'N/A')}
  Lost/Found: {target.get('lost_or_found', 'N/A')}

[bold]Timestamps:[/bold]
  Created: {match['created_at']}
  Updated: {match['updated_at']}
"""
        
        # Add confirmation info
        if match.get('source_confirmed_at'):
            content += f"  Source Confirmed: {match['source_confirmed_at']}\n"
        if match.get('target_confirmed_at'):
            content += f"  Target Confirmed: {match['target_confirmed_at']}\n"
        if match.get('rejected_at'):
            content += f"  Rejected: {match['rejected_at']} by {match.get('rejected_by', 'N/A')}\n"
            if match.get('rejection_reason'):
                content += f"  Reason: {match['rejection_reason']}\n"
        
        # Show contact info if both confirmed
        contact = match.get('contact_info')
        if contact:
            content += f"""
[bold green]Contact Information (Both Confirmed!):[/bold green]
  Name: {contact.get('full_name') or 'N/A'}
  Email: {contact.get('email')}
  Phone: {contact.get('phone_number') or 'N/A'}
"""
        
        panel = Panel(
            content.strip(),
            title=f"Match: {match['id']}",
            border_style="blue"
        )
        console.print(panel)
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)


@matches_group.command(name="confirm")
@click.argument("match_id")
def confirm_match(match_id):
    """Confirm a potential match."""
    try:
        client = APIClient()
        result = client.confirm_match(match_id, confirmed=True)
        
        console.print("[bold green]✓ Match confirmed![/bold green]")
        console.print(f"  Status: {result['status']}")
        
        if result['status'] == 'both_confirmed':
            console.print("\n[bold green]🎉 Both parties have confirmed![/bold green]")
            contact = result.get('contact_info')
            if contact:
                console.print("\n[bold]Contact Information:[/bold]")
                console.print(f"  Name: {contact.get('full_name') or 'N/A'}")
                console.print(f"  Email: {contact.get('email')}")
                console.print(f"  Phone: {contact.get('phone_number') or 'N/A'}")
        else:
            console.print("\n[dim]Waiting for the other party to confirm...[/dim]")
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)


@matches_group.command(name="reject")
@click.argument("match_id")
@click.option("--reason", "-r", default=None, help="Reason for rejection")
@click.confirmation_option(prompt="Are you sure you want to reject this match?")
def reject_match(match_id, reason):
    """Reject a potential match."""
    try:
        client = APIClient()
        result = client.reject_match(match_id, reason=reason)
        
        console.print("[bold yellow]✓ Match rejected.[/bold yellow]")
        console.print(f"  Status: {result['status']}")
        
    except APIError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.detail}")
        raise SystemExit(1)

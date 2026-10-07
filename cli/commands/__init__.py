"""
CLI Commands Package
"""

from cli.commands.auth import auth_group
from cli.commands.items import items_group
from cli.commands.matches import matches_group
from cli.commands.notifications import notifications_group
from cli.commands.config import config_group

__all__ = [
    "auth_group",
    "items_group",
    "matches_group",
    "notifications_group",
    "config_group",
]

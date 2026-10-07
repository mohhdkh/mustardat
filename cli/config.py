"""
CLI Configuration and Token Management

Handles storing/loading authentication tokens and CLI settings.
"""

import json
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict


# Default config directory
CONFIG_DIR = Path.home() / ".lostfound"
CONFIG_FILE = CONFIG_DIR / "config.json"
TOKEN_FILE = CONFIG_DIR / "token.json"


@dataclass
class CLIConfig:
    """CLI configuration settings."""
    base_url: str = "http://localhost:8000"
    api_prefix: str = "/api/v1"
    timeout: int = 30
    
    @property
    def api_url(self) -> str:
        return f"{self.base_url}{self.api_prefix}"
    
    def save(self) -> None:
        """Save config to file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(asdict(self), f, indent=2)
    
    @classmethod
    def load(cls) -> "CLIConfig":
        """Load config from file or return defaults."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                return cls(**data)
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()


@dataclass
class TokenData:
    """Stored authentication token."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800
    
    def save(self) -> None:
        """Save token to file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            json.dump(asdict(self), f, indent=2)
        # Set restrictive permissions on token file
        os.chmod(TOKEN_FILE, 0o600)
    
    @classmethod
    def load(cls) -> Optional["TokenData"]:
        """Load token from file."""
        if TOKEN_FILE.exists():
            try:
                with open(TOKEN_FILE, "r") as f:
                    data = json.load(f)
                return cls(**data)
            except (json.JSONDecodeError, TypeError):
                pass
        return None
    
    @staticmethod
    def delete() -> None:
        """Delete stored token (logout)."""
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()


def get_auth_header() -> Optional[dict]:
    """Get authorization header if token exists."""
    token = TokenData.load()
    if token:
        return {"Authorization": f"{token.token_type.capitalize()} {token.access_token}"}
    return None


def require_auth() -> dict:
    """Get auth header or raise error if not logged in."""
    header = get_auth_header()
    if not header:
        raise click.ClickException(
            "Not logged in. Please run 'lf login' first."
        )
    return header


# Import click here to avoid circular imports
try:
    import click
except ImportError:
    pass

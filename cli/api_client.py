"""
API Client for Lost & Found Backend

Handles all HTTP requests to the backend API.
"""

import httpx
from typing import Optional, Any, Dict, List
from pathlib import Path

from cli.config import CLIConfig, get_auth_header


class APIError(Exception):
    """API request error."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API Error ({status_code}): {detail}")


class APIClient:
    """HTTP client for the Lost & Found API."""
    
    def __init__(self, config: Optional[CLIConfig] = None):
        self.config = config or CLIConfig.load()
        self.base_url = self.config.api_url
        self.timeout = self.config.timeout
    
    def _get_headers(self, auth: bool = True) -> Dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if auth:
            auth_header = get_auth_header()
            if auth_header:
                headers.update(auth_header)
        return headers
    
    def _handle_response(self, response: httpx.Response) -> Any:
        """Handle API response and raise errors if needed."""
        if response.status_code >= 400:
            try:
                error_data = response.json()
                detail = error_data.get("detail", str(error_data))
            except Exception:
                detail = response.text or f"HTTP {response.status_code}"
            raise APIError(response.status_code, detail)
        
        if response.status_code == 204:
            return None
        
        try:
            return response.json()
        except Exception:
            return response.text
    
    # ==========================================
    # Authentication
    # ==========================================
    
    def login(self, email: str, password: str) -> Dict:
        """Login and get access token."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/auth/login",
                json={"email": email, "password": password}
            )
            return self._handle_response(response)
    
    def register(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> Dict:
        """Register a new user."""
        data = {"email": email, "password": password}
        if full_name:
            data["full_name"] = full_name
        if phone_number:
            data["phone_number"] = phone_number
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/users",
                json=data
            )
            return self._handle_response(response)
    
    # ==========================================
    # User Profile
    # ==========================================
    
    def get_profile(self) -> Dict:
        """Get current user profile."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/users/me",
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    def update_profile(
        self,
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> Dict:
        """Update current user profile."""
        params = {}
        if full_name is not None:
            params["full_name"] = full_name
        if phone_number is not None:
            params["phone_number"] = phone_number
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.patch(
                f"{self.base_url}/users/me",
                params=params,
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    def delete_account(self) -> None:
        """Delete current user account."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.delete(
                f"{self.base_url}/users/me",
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    # ==========================================
    # Items
    # ==========================================
    
    def create_item(
        self,
        item_type: str,
        lost_or_found: str,
        title: str,
        latitude: float,
        longitude: float,
        event_date: str,
        description: Optional[str] = None,
        location_name: Optional[str] = None
    ) -> Dict:
        """Create a new lost/found item."""
        data = {
            "item_type": item_type,
            "lost_or_found": lost_or_found,
            "title": title,
            "latitude": latitude,
            "longitude": longitude,
            "event_date": event_date
        }
        if description:
            data["description"] = description
        if location_name:
            data["location_name"] = location_name
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/items",
                json=data,
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    def list_items(
        self,
        item_type: Optional[str] = None,
        lost_or_found: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict:
        """List user's items with optional filters."""
        params = {"page": page, "page_size": page_size}
        if item_type:
            params["item_type"] = item_type
        if lost_or_found:
            params["lost_or_found"] = lost_or_found
        if status:
            params["item_status"] = status
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/items",
                params=params,
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    def get_item(self, item_id: str) -> Dict:
        """Get a specific item by ID."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/items/{item_id}",
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    def update_item(self, item_id: str, **updates) -> Dict:
        """Update an existing item."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.patch(
                f"{self.base_url}/items/{item_id}",
                json=updates,
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    def delete_item(self, item_id: str) -> None:
        """Delete an item."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.delete(
                f"{self.base_url}/items/{item_id}",
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    # ==========================================
    # Images
    # ==========================================
    
    def upload_image(self, item_id: str, file_path: str) -> Dict:
        """Upload an image for an item."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Determine content type
        suffix = path.suffix.lower()
        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp"
        }
        content_type = content_types.get(suffix, "image/jpeg")
        
        headers = self._get_headers()
        del headers["Content-Type"]  # Let httpx set multipart content type
        
        with open(path, "rb") as f:
            files = {"file": (path.name, f, content_type)}
            with httpx.Client(timeout=60) as client:  # Longer timeout for uploads
                response = client.post(
                    f"{self.base_url}/items/{item_id}/images",
                    files=files,
                    headers=headers
                )
                return self._handle_response(response)
    
    def list_images(self, item_id: str) -> List[Dict]:
        """List all images for an item."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/items/{item_id}/images",
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    def delete_image(self, item_id: str, image_id: str) -> None:
        """Delete an image from an item."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.delete(
                f"{self.base_url}/items/{item_id}/images/{image_id}",
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    # ==========================================
    # Matches
    # ==========================================
    
    def find_matches(
        self,
        item_id: str,
        radius_km: Optional[float] = None,
        time_range_days: Optional[int] = None,
        min_score: Optional[float] = None
    ) -> Dict:
        """Find potential matches for an item."""
        params = {}
        if radius_km is not None:
            params["radius_km"] = radius_km
        if time_range_days is not None:
            params["time_range_days"] = time_range_days
        if min_score is not None:
            params["min_score"] = min_score
        
        with httpx.Client(timeout=120) as client:  # Longer timeout for matching
            response = client.get(
                f"{self.base_url}/items/{item_id}/matches",
                params=params,
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    def list_matches(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> List[Dict]:
        """List all matches for user's items."""
        params = {"page": page, "page_size": page_size}
        if status:
            params["status_filter"] = status
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/matches",
                params=params,
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    def get_match(self, match_id: str) -> Dict:
        """Get a specific match by ID."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/matches/{match_id}",
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    def confirm_match(
        self,
        match_id: str,
        confirmed: bool = True,
        rejection_reason: Optional[str] = None
    ) -> Dict:
        """Confirm or reject a match."""
        data = {"confirmed": confirmed}
        if rejection_reason:
            data["rejection_reason"] = rejection_reason
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/matches/{match_id}/confirm",
                json=data,
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    def reject_match(
        self,
        match_id: str,
        reason: Optional[str] = None
    ) -> Dict:
        """Reject a match."""
        params = {}
        if reason:
            params["rejection_reason"] = reason
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/matches/{match_id}/reject",
                params=params,
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    # ==========================================
    # Notifications
    # ==========================================
    
    def list_notifications(
        self,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20
    ) -> Dict:
        """List user notifications."""
        params = {
            "unread_only": unread_only,
            "page": page,
            "page_size": page_size
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/notifications",
                params=params,
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    def get_notification(self, notification_id: str) -> Dict:
        """Get a specific notification."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/notifications/{notification_id}",
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    def mark_notifications_read(self, notification_ids: List[str]) -> Dict:
        """Mark notifications as read."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/notifications/mark-read",
                json={"notification_ids": notification_ids},
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    def mark_all_notifications_read(self) -> Dict:
        """Mark all notifications as read."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/notifications/mark-all-read",
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    def delete_notification(self, notification_id: str) -> None:
        """Delete a notification."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.delete(
                f"{self.base_url}/notifications/{notification_id}",
                headers=self._get_headers()
            )
            return self._handle_response(response)
    
    # ==========================================
    # Health Check
    # ==========================================
    
    def health_check(self) -> Dict:
        """Check API health status."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self.config.base_url}/health")
            return self._handle_response(response)


# Global client instance
client = APIClient()

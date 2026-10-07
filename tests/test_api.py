"""
API endpoint tests.
"""

import pytest
from httpx import AsyncClient


class TestHealthCheck:
    """Tests for health check endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check returns healthy status."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestUserRegistration:
    """Tests for user registration."""
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, client: AsyncClient):
        """Test successful user registration."""
        response = await client.post(
            "/api/v1/users",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "full_name": "New User"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "id" in data
        assert "hashed_password" not in data
    
    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(
        self, client: AsyncClient, test_user
    ):
        """Test registration fails with duplicate email."""
        response = await client.post(
            "/api/v1/users",
            json={
                "email": test_user.email,
                "password": "anotherpassword123"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_user_invalid_email(self, client: AsyncClient):
        """Test registration fails with invalid email."""
        response = await client.post(
            "/api/v1/users",
            json={
                "email": "not-an-email",
                "password": "securepassword123"
            }
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_user_short_password(self, client: AsyncClient):
        """Test registration fails with short password."""
        response = await client.post(
            "/api/v1/users",
            json={
                "email": "test@example.com",
                "password": "short"
            }
        )
        assert response.status_code == 422


class TestAuthentication:
    """Tests for authentication endpoints."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Test login fails with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login fails for nonexistent user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "anypassword"
            }
        )
        assert response.status_code == 401


class TestItems:
    """Tests for item endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_item_success(
        self, client: AsyncClient, auth_headers, sample_item_data
    ):
        """Test successful item creation."""
        response = await client.post(
            "/api/v1/items",
            json=sample_item_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_item_data["title"]
        assert data["item_type"] == sample_item_data["item_type"]
        assert data["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_create_item_unauthorized(
        self, client: AsyncClient, sample_item_data
    ):
        """Test item creation fails without auth."""
        response = await client.post(
            "/api/v1/items",
            json=sample_item_data
        )
        assert response.status_code == 403  # No auth header
    
    @pytest.mark.asyncio
    async def test_create_item_invalid_coordinates(
        self, client: AsyncClient, auth_headers, sample_item_data
    ):
        """Test item creation fails with invalid coordinates."""
        sample_item_data["latitude"] = 100  # Invalid: must be -90 to 90
        response = await client.post(
            "/api/v1/items",
            json=sample_item_data,
            headers=auth_headers
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_list_items(
        self, client: AsyncClient, auth_headers, sample_item_data
    ):
        """Test listing items."""
        # Create an item first
        await client.post(
            "/api/v1/items",
            json=sample_item_data,
            headers=auth_headers
        )
        
        # List items
        response = await client.get(
            "/api/v1/items",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1
    
    @pytest.mark.asyncio
    async def test_get_item(
        self, client: AsyncClient, auth_headers, sample_item_data
    ):
        """Test getting a specific item."""
        # Create an item
        create_response = await client.post(
            "/api/v1/items",
            json=sample_item_data,
            headers=auth_headers
        )
        item_id = create_response.json()["id"]
        
        # Get the item
        response = await client.get(
            f"/api/v1/items/{item_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["id"] == item_id
    
    @pytest.mark.asyncio
    async def test_update_item(
        self, client: AsyncClient, auth_headers, sample_item_data
    ):
        """Test updating an item."""
        # Create an item
        create_response = await client.post(
            "/api/v1/items",
            json=sample_item_data,
            headers=auth_headers
        )
        item_id = create_response.json()["id"]
        
        # Update the item
        response = await client.patch(
            f"/api/v1/items/{item_id}",
            json={"title": "Updated Title"},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"
    
    @pytest.mark.asyncio
    async def test_delete_item(
        self, client: AsyncClient, auth_headers, sample_item_data
    ):
        """Test deleting an item."""
        # Create an item
        create_response = await client.post(
            "/api/v1/items",
            json=sample_item_data,
            headers=auth_headers
        )
        item_id = create_response.json()["id"]
        
        # Delete the item
        response = await client.delete(
            f"/api/v1/items/{item_id}",
            headers=auth_headers
        )
        assert response.status_code == 204
        
        # Verify it's deleted
        get_response = await client.get(
            f"/api/v1/items/{item_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404


class TestNotifications:
    """Tests for notification endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_notifications(
        self, client: AsyncClient, auth_headers
    ):
        """Test listing notifications."""
        response = await client.get(
            "/api/v1/notifications",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "total" in data
        assert "unread_count" in data
    
    @pytest.mark.asyncio
    async def test_mark_all_read(
        self, client: AsyncClient, auth_headers
    ):
        """Test marking all notifications as read."""
        response = await client.post(
            "/api/v1/notifications/mark-all-read",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "updated_count" in response.json()

# API Examples

This document contains example request/response payloads for the Lost & Found API.

## Authentication

### Register User

**Request:**
```http
POST /api/v1/users
Content-Type: application/json

{
    "email": "john@example.com",
    "password": "securepassword123",
    "full_name": "John Doe",
    "phone_number": "+1234567890"
}
```

**Response (201 Created):**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "john@example.com",
    "full_name": "John Doe",
    "is_active": true,
    "is_verified": false,
    "created_at": "2024-01-15T10:30:00Z"
}
```

### Login

**Request:**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
    "email": "john@example.com",
    "password": "securepassword123"
}
```

**Response (200 OK):**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJleHAiOjE3MDUzMTQ2MDAsImlhdCI6MTcwNTMxMjgwMH0.abc123",
    "token_type": "bearer",
    "expires_in": 1800
}
```

---

## Items

### Create Lost Item

**Request:**
```http
POST /api/v1/items
Authorization: Bearer <token>
Content-Type: application/json

{
    "item_type": "phone",
    "lost_or_found": "lost",
    "title": "Black iPhone 14 Pro",
    "description": "Lost my iPhone 14 Pro with a black silicone case. Has a small scratch on the screen corner. Lock screen shows a photo of my dog.",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "location_name": "Central Park, New York",
    "event_date": "2024-01-15T14:30:00Z"
}
```

**Response (201 Created):**
```json
{
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "item_type": "phone",
    "lost_or_found": "lost",
    "status": "active",
    "title": "Black iPhone 14 Pro",
    "description": "Lost my iPhone 14 Pro with a black silicone case...",
    "latitude": 40.7128,
    "longitude": -74.006,
    "location_name": "Central Park, New York",
    "event_date": "2024-01-15T14:30:00Z",
    "created_at": "2024-01-15T15:00:00Z",
    "updated_at": "2024-01-15T15:00:00Z",
    "images": []
}
```

### Create Found Item

**Request:**
```http
POST /api/v1/items
Authorization: Bearer <token>
Content-Type: application/json

{
    "item_type": "wallet",
    "lost_or_found": "found",
    "title": "Brown Leather Wallet",
    "description": "Found a brown leather wallet near the subway entrance. Contains some cards.",
    "latitude": 40.7580,
    "longitude": -73.9855,
    "location_name": "Times Square Subway Station",
    "event_date": "2024-01-15T18:00:00Z"
}
```

### List Items

**Request:**
```http
GET /api/v1/items?item_type=phone&status=active&page=1&page_size=20
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
    "items": [
        {
            "id": "660e8400-e29b-41d4-a716-446655440001",
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "item_type": "phone",
            "lost_or_found": "lost",
            "status": "active",
            "title": "Black iPhone 14 Pro",
            "description": "Lost my iPhone 14 Pro...",
            "latitude": 40.7128,
            "longitude": -74.006,
            "location_name": "Central Park, New York",
            "event_date": "2024-01-15T14:30:00Z",
            "created_at": "2024-01-15T15:00:00Z",
            "updated_at": "2024-01-15T15:00:00Z",
            "images": [
                {
                    "id": "770e8400-e29b-41d4-a716-446655440002",
                    "s3_key_thumbnail": "items/660e.../images/770e.../thumbnail.jpg",
                    "display_order": 1,
                    "is_processed": true
                }
            ]
        }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
}
```

---

## Image Upload

### Upload Image

**Request:**
```http
POST /api/v1/items/660e8400-e29b-41d4-a716-446655440001/images
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <binary image data>
```

**Response (201 Created):**
```json
{
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "original_filename": "iphone_photo.jpg",
    "s3_key_original": "items/660e8400.../images/770e8400.../original.jpg",
    "file_size": 2048576,
    "content_type": "image/jpeg",
    "is_processed": true,
    "message": "Image uploaded successfully. Processing complete."
}
```

### Get Image Details

**Request:**
```http
GET /api/v1/items/660e8400.../images
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
[
    {
        "id": "770e8400-e29b-41d4-a716-446655440002",
        "item_id": "660e8400-e29b-41d4-a716-446655440001",
        "original_filename": "iphone_photo.jpg",
        "s3_key_original": "items/660e.../images/770e.../original.jpg",
        "s3_key_processed": "items/660e.../images/770e.../processed.jpg",
        "s3_key_thumbnail": "items/660e.../images/770e.../thumbnail.jpg",
        "content_type": "image/jpeg",
        "file_size": 2048576,
        "width": 1920,
        "height": 1080,
        "exif_data": {
            "Make": "Apple",
            "Model": "iPhone 14 Pro",
            "DateTime": "2024:01:15 14:25:00",
            "gps": {
                "latitude": 40.7128,
                "longitude": -74.006
            }
        },
        "exif_latitude": 40.7128,
        "exif_longitude": -74.006,
        "exif_datetime": "2024-01-15T14:25:00Z",
        "is_processed": true,
        "processing_error": null,
        "display_order": 1,
        "created_at": "2024-01-15T15:05:00Z"
    }
]
```

---

## Matching

### Find Matches

**Request:**
```http
GET /api/v1/items/660e8400.../matches?radius_km=50&time_range_days=30&min_score=0.5
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
    "matches": [
        {
            "id": "880e8400-e29b-41d4-a716-446655440003",
            "source_item_id": "660e8400-e29b-41d4-a716-446655440001",
            "target_item_id": "990e8400-e29b-41d4-a716-446655440004",
            "status": "pending",
            "overall_score": 0.87,
            "vector_similarity": 0.92,
            "phash_similarity": 0.85,
            "orb_match_score": 0.78,
            "location_score": 0.95,
            "distance_km": 2.5,
            "score_details": {
                "weights": {
                    "vector": 0.4,
                    "phash": 0.25,
                    "orb": 0.2,
                    "location": 0.15
                },
                "raw_vector_distance": 0.28
            },
            "created_at": "2024-01-15T16:00:00Z",
            "updated_at": "2024-01-15T16:00:00Z",
            "source_confirmed_at": null,
            "target_confirmed_at": null,
            "rejected_at": null,
            "rejected_by": null,
            "rejection_reason": null,
            "target_item": {
                "id": "990e8400-e29b-41d4-a716-446655440004",
                "item_type": "phone",
                "lost_or_found": "found",
                "status": "active",
                "title": "iPhone Found in Park",
                "description": "Found an iPhone with black case...",
                "latitude": 40.7148,
                "longitude": -74.008,
                "location_name": "Near Central Park Zoo",
                "event_date": "2024-01-15T16:00:00Z",
                "images": [...]
            },
            "contact_info": null
        }
    ],
    "total": 1,
    "search_params": {
        "radius_km": 50,
        "time_range_days": 30,
        "min_score": 0.5
    }
}
```

### Confirm Match

**Request:**
```http
POST /api/v1/matches/880e8400.../confirm
Authorization: Bearer <token>
Content-Type: application/json

{
    "confirmed": true
}
```

**Response (200 OK) - First confirmation:**
```json
{
    "id": "880e8400-e29b-41d4-a716-446655440003",
    "status": "source_confirmed",
    "source_confirmed_at": "2024-01-15T17:00:00Z",
    "target_confirmed_at": null,
    "contact_info": null,
    ...
}
```

**Response (200 OK) - Both confirmed:**
```json
{
    "id": "880e8400-e29b-41d4-a716-446655440003",
    "status": "both_confirmed",
    "source_confirmed_at": "2024-01-15T17:00:00Z",
    "target_confirmed_at": "2024-01-15T17:30:00Z",
    "contact_info": {
        "full_name": "Jane Smith",
        "email": "jane@example.com",
        "phone_number": "+1987654321"
    },
    ...
}
```

### Reject Match

**Request:**
```http
POST /api/v1/matches/880e8400.../confirm
Authorization: Bearer <token>
Content-Type: application/json

{
    "confirmed": false,
    "rejection_reason": "This is not my phone - different model"
}
```

**Response (200 OK):**
```json
{
    "id": "880e8400-e29b-41d4-a716-446655440003",
    "status": "rejected",
    "rejected_at": "2024-01-15T17:00:00Z",
    "rejected_by": "source",
    "rejection_reason": "This is not my phone - different model",
    ...
}
```

---

## Notifications

### List Notifications

**Request:**
```http
GET /api/v1/notifications?unread_only=true&page=1&page_size=20
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
    "notifications": [
        {
            "id": "aa0e8400-e29b-41d4-a716-446655440005",
            "notification_type": "match_found",
            "channel": "email",
            "subject": "Potential match found for your item!",
            "body": "Hello John,\n\nWe found a potential match for your item: Black iPhone 14 Pro\n\nMatch Score: 87%\nDistance: 2.5 km away\n\nPlease log in to review this match...",
            "related_item_id": "660e8400-e29b-41d4-a716-446655440001",
            "related_match_id": "880e8400-e29b-41d4-a716-446655440003",
            "is_sent": true,
            "is_read": false,
            "sent_at": "2024-01-15T16:05:00Z",
            "read_at": null,
            "created_at": "2024-01-15T16:05:00Z"
        }
    ],
    "total": 1,
    "unread_count": 1,
    "page": 1,
    "page_size": 20
}
```

### Mark Notifications as Read

**Request:**
```http
POST /api/v1/notifications/mark-read
Authorization: Bearer <token>
Content-Type: application/json

{
    "notification_ids": [
        "aa0e8400-e29b-41d4-a716-446655440005"
    ]
}
```

**Response (200 OK):**
```json
{
    "message": "Marked 1 notifications as read",
    "updated_count": 1
}
```

---

## Error Responses

### 400 Bad Request
```json
{
    "detail": "Maximum 6 images per item"
}
```

### 401 Unauthorized
```json
{
    "detail": "Invalid or expired token"
}
```

### 403 Forbidden
```json
{
    "detail": "You don't have permission to access this resource"
}
```

### 404 Not Found
```json
{
    "detail": "Item not found"
}
```

### 422 Validation Error
```json
{
    "detail": "Validation error",
    "errors": [
        {
            "field": "body.latitude",
            "message": "Input should be greater than or equal to -90",
            "type": "greater_than_equal"
        }
    ]
}
```

### 429 Too Many Requests
```json
{
    "detail": "Too many requests. Please try again later.",
    "retry_after": 60
}
```

---

## cURL Examples

### Register and Login
```bash
# Register
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","full_name":"Test User"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

### Create Item and Upload Image
```bash
# Create item
curl -X POST http://localhost:8000/api/v1/items \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "phone",
    "lost_or_found": "lost",
    "title": "Lost iPhone",
    "latitude": 40.7128,
    "longitude": -74.006,
    "event_date": "2024-01-15T14:30:00Z"
  }'

# Upload image
curl -X POST http://localhost:8000/api/v1/items/<item_id>/images \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/image.jpg"
```

### Find and Confirm Matches
```bash
# Find matches
curl -X GET "http://localhost:8000/api/v1/items/<item_id>/matches?radius_km=50" \
  -H "Authorization: Bearer <token>"

# Confirm match
curl -X POST http://localhost:8000/api/v1/matches/<match_id>/confirm \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"confirmed": true}'
```

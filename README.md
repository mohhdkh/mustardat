# Lost & Found Image-Matching System

> دليل النشر المجاني الحالي: [Render + Supabase](docs/deploy-supabase.md)

A full-stack web application for matching lost and found items using AI-powered image processing, vector embeddings, and multi-signal similarity search.

## 🌟 Features

### Core Functionality
- **Item Management**: Create and manage lost/found item listings with up to 6 images
- **Smart Matching**: AI-powered matching between lost and found items
- **Privacy Protection**: Contact info revealed only after mutual confirmation
- **Real-time Notifications**: Get notified when matches are found

### Image Processing Pipeline
- **YOLO Object Detection**: Automatic object detection and cropping
- **CLIP Embeddings**: Semantic similarity using OpenAI's CLIP model
- **Perceptual Hashing**: pHash, dHash, aHash for visual similarity
- **ORB Descriptors**: Geometric keypoint matching
- **EXIF Extraction**: GPS and metadata from photos

### User Interface
- **Responsive Design**: Works on desktop and mobile
- **Camera Capture**: Take photos directly from your phone
- **Image Gallery**: Thumbnail previews with full-size lightbox
- **Drag & Drop**: Easy image upload

## 🛠 Tech Stack

- **Backend**: FastAPI (Python 3.10+)
- **Database**: SQLite with async support (aiosqlite)
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Storage**: Local file system
- **ML Models**: YOLOv8, OpenCLIP (ViT-B/32), OpenCV
- **Authentication**: JWT tokens with bcrypt password hashing

## Project Structure

```
lost&found/
├── app/
│   ├── __init__.py
│   ├── config.py              # Configuration and settings
│   ├── main.py                # FastAPI application entry point
│   ├── api/
│   │   ├── deps.py            # Dependencies (auth, db)
│   │   └── routes/
│   │       ├── auth.py        # Authentication endpoints
│   │       ├── users.py       # User management
│   │       ├── items.py       # Item CRUD + image upload
│   │       ├── matches.py     # Match confirmation/rejection
│   │       └── notifications.py
│   ├── db/
│   │   └── database.py        # Database connection
│   ├── models/
│   │   ├── user.py            # User model
│   │   ├── item.py            # Item model
│   │   ├── image.py           # Image model
│   │   ├── embedding.py       # Embedding model (pgvector)
│   │   ├── match.py           # Match model
│   │   └── notification.py    # Notification model
│   ├── schemas/               # Pydantic schemas
│   ├── services/
│   │   ├── auth.py            # Authentication service
│   │   ├── storage.py         # S3 storage service
│   │   ├── image_processing.py # Image processing pipeline
│   │   ├── matching.py        # Matching engine
│   │   └── notification.py    # Email/SMS service
│   └── middleware/
│       └── security.py        # Rate limiting, sanitization
├── alembic/                   # Database migrations
├── scripts/
│   └── schema.sql             # Raw SQL schema
├── tests/                     # Test files
├── .env.example               # Environment variables template
├── requirements.txt           # Python dependencies
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Conda (recommended) or pip
- CUDA-capable GPU (optional, for faster ML inference)
- Docker & Docker Compose (for containerized deployment)

## 🐳 Docker Deployment (Recommended)

### Quick Start with Docker

```bash
# 1. Build the Docker image
docker-compose build

# 2. Start the server
docker-compose up -d

# 3. Access the application
# Frontend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Docker Commands

```bash
# Production mode (detached)
docker-compose up -d

# Development mode with hot reload
docker-compose --profile dev up api-dev

# View logs
docker-compose logs -f

# Stop containers
docker-compose down

# Clean up everything
docker-compose down -v --rmi local
```

### Using Helper Scripts

**Windows:**
```batch
docker-run.bat build    # Build image
docker-run.bat up       # Start production
docker-run.bat dev      # Start development
docker-run.bat logs     # View logs
docker-run.bat down     # Stop containers
```

**Linux/Mac:**
```bash
./docker-run.sh build
./docker-run.sh up
./docker-run.sh dev
```

### Docker Configuration

1. Copy the environment file:
```bash
cp .env.docker.example .env.docker
```

2. Edit `.env.docker` with your settings (especially `JWT_SECRET_KEY`)

3. Data is persisted in the `./data` directory

---

## 💻 Local Development Setup

### 1. Clone and Create Environment

```bash
cd lost&found

# Using Conda (recommended)
conda create -n myenv python=3.10
conda activate myenv

# Or using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your configuration
```

Key variables:
```env
# Security
JWT_SECRET_KEY=your-super-secret-key-change-this

# Database (SQLite - auto-created)
DATABASE_PATH=data/lostfound.db

# File uploads
UPLOAD_DIR=uploads
MAX_IMAGE_SIZE_MB=10

# Matching defaults
DEFAULT_SEARCH_RADIUS_KM=50
DEFAULT_TIME_RANGE_DAYS=30
```

### 4. Run the Server

```bash
# Development (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or simply
python -m uvicorn app.main:app --reload
```

### 5. Access the Application

- **Frontend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📱 Usage Guide

### Reporting a Lost/Found Item

1. Go to **Report Item** page
2. Select "I Lost Something" or "I Found Something"
3. Fill in the details:
   - Category (phone, wallet, keys, etc.)
   - Title and description
   - Location (use GPS or enter manually)
   - Date and time
4. Upload photos:
   - **Choose from Gallery**: Select existing photos
   - **Take Photo**: Capture directly from camera (mobile)
   - **Drag & Drop**: Drop images onto the upload area
5. Submit the report

### Finding Matches

1. Go to **My Items** page
2. Click **Find Matches** on any item
3. Adjust search parameters:
   - **Search Radius**: How far to search (km)
   - **Time Range**: Days before/after the event
   - **Minimum Score**: Match confidence threshold (0-1)
4. Click **Search for Matches**
5. Review potential matches and confirm/reject

### Confirming a Match

1. When both parties confirm a match, contact info is revealed
2. You'll receive a notification with the other person's email/phone
3. Coordinate to return the item!

## 📡 API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Login and get JWT token |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/users` | Register new user |
| GET | `/api/v1/users/me` | Get current user profile |
| PATCH | `/api/v1/users/me` | Update profile |
| DELETE | `/api/v1/users/me` | Delete account |

### Items

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/items` | Create lost/found item |
| GET | `/api/v1/items` | List user's items |
| GET | `/api/v1/items/{id}` | Get item details |
| PATCH | `/api/v1/items/{id}` | Update item |
| DELETE | `/api/v1/items/{id}` | Delete item |
| POST | `/api/v1/items/{id}/images` | Upload image |
| GET | `/api/v1/items/{id}/images` | List item images |
| DELETE | `/api/v1/items/{id}/images/{image_id}` | Delete image |
| GET | `/api/v1/items/{id}/matches` | Find matches |

### Matches

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/matches` | List all matches |
| GET | `/api/v1/matches/{id}` | Get match details |
| POST | `/api/v1/matches/{id}/confirm` | Confirm/reject match |
| POST | `/api/v1/matches/{id}/reject` | Reject match |

### Notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/notifications` | List notifications |
| GET | `/api/v1/notifications/{id}` | Get notification |
| POST | `/api/v1/notifications/mark-read` | Mark as read |
| POST | `/api/v1/notifications/mark-all-read` | Mark all as read |
| DELETE | `/api/v1/notifications/{id}` | Delete notification |

## Example Payloads

See [docs/examples.md](docs/examples.md) for detailed request/response examples.

## Matching Pipeline

1. **Metadata Filtering**
   - Same item type (phone, wallet, etc.)
   - Within location radius (default 50km)
   - Within time range (default 30 days)
   - Opposite lost/found status

2. **Vector Similarity Search**
   - Uses pgvector with HNSW index
   - Cosine similarity on CLIP embeddings
   - Returns top 50 candidates

3. **Multi-Signal Re-ranking**
   - Vector similarity (40% weight)
   - pHash similarity (25% weight)
   - ORB keypoint matches (20% weight)
   - Location proximity (15% weight)

4. **Final Output**
   - Top 10 matches with scores
   - Detailed score breakdown

## Security Features

- JWT authentication with configurable expiry
- Password hashing with bcrypt
- Rate limiting (100 requests/minute default)
- Input sanitization middleware
- Security headers (HSTS, CSP, etc.)
- Secure file upload validation
- Contact info hidden until mutual confirmation

## ⚙️ Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_SECRET_KEY` | Secret for JWT signing | Required |
| `JWT_ALGORITHM` | JWT algorithm | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | 1440 (24h) |
| `DATABASE_PATH` | SQLite database path | data/lostfound.db |
| `UPLOAD_DIR` | Image upload directory | uploads |
| `MAX_IMAGE_SIZE_MB` | Max upload size | 10 |
| `DEFAULT_SEARCH_RADIUS_KM` | Match search radius | 50 |
| `DEFAULT_TIME_RANGE_DAYS` | Match time range | 30 |
| `VECTOR_SIMILARITY_THRESHOLD` | Min match score | 0.5 |

## 🧪 Development

### Running Tests

```bash
pytest tests/ -v
```

### Database Reset

```bash
# Delete the database file to start fresh
rm data/lostfound.db

# Restart the server - tables will be recreated
uvicorn app.main:app --reload
```

### Folder Structure for Uploads

```
uploads/
└── items/
    └── {item_id}/
        └── images/
            └── {image_id}/
                ├── original.jpg
                ├── processed.jpg
                └── thumbnail.jpg
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - feel free to use this project for personal or commercial purposes.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [OpenCLIP](https://github.com/mlfoundations/open_clip) - Open source CLIP implementation
- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) - Object detection
- [ImageHash](https://github.com/JohannesBuchner/imagehash) - Perceptual hashing

"""
Configuration module for the Lost & Found backend.
Loads environment variables and provides typed settings.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ===========================================
    # DATABASE
    # ===========================================
    database_url: Optional[str] = Field(
        default=None,
        description=(
            "SQLAlchemy database URL. Set this to the Supabase PostgreSQL "
            "connection string in production; SQLite is used when omitted."
        )
    )
    database_path: str = Field(
        default="./data/lostfound.db",
        description="Path to the fallback SQLite database file"
    )
    
    # ===========================================
    # JWT AUTHENTICATION
    # ===========================================
    jwt_secret_key: str = Field(
        default="change-this-in-production",
        description="Secret key for JWT token signing"
    )
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    
    # ===========================================
    # FILE STORAGE
    # ===========================================
    storage_backend: str = Field(
        default="local",
        description="File storage backend: local or supabase"
    )
    upload_dir: str = Field(
        default="./data/uploads",
        description="Directory for storing images when using local storage"
    )
    supabase_url: Optional[str] = Field(default=None)
    supabase_service_role_key: Optional[str] = Field(default=None)
    supabase_storage_bucket: str = Field(default="mustardat-images")
    supabase_storage_public: bool = Field(default=True)
    
    # ===========================================
    # IMAGE PROCESSING
    # ===========================================
    max_image_size_mb: int = Field(default=10)
    allowed_image_types: str = Field(default="image/jpeg,image/png,image/webp")
    yolo_model_path: str = Field(default="yolov8n.pt")
    clip_model_name: str = Field(default="ViT-B/32")
    
    # ===========================================
    # MATCHING CONFIGURATION
    # ===========================================
    default_search_radius_km: float = Field(default=50.0)
    default_time_range_days: int = Field(default=30)
    vector_similarity_threshold: float = Field(default=0.7)
    top_k_vector_results: int = Field(default=50)
    final_top_k_matches: int = Field(default=10)
    
    # ===========================================
    # RATE LIMITING
    # ===========================================
    rate_limit_requests: int = Field(default=100)
    rate_limit_period: int = Field(default=60)
    
    # ===========================================
    # APPLICATION
    # ===========================================
    debug: bool = Field(default=True)
    environment: str = Field(default="development")
    api_v1_prefix: str = Field(default="/api/v1")
    
    @property
    def allowed_image_types_list(self) -> List[str]:
        """Parse allowed image types into a list."""
        return [t.strip() for t in self.allowed_image_types.split(",")]
    
    @property
    def max_image_size_bytes(self) -> int:
        """Convert MB to bytes."""
        return self.max_image_size_mb * 1024 * 1024

    @model_validator(mode="after")
    def validate_production_secrets(self):
        """Refuse to start production with the public development JWT secret."""
        if not self.debug and self.jwt_secret_key == "change-this-in-production":
            raise ValueError("JWT_SECRET_KEY must be configured for production")
        self.storage_backend = self.storage_backend.strip().lower()
        if self.storage_backend not in {"local", "supabase"}:
            raise ValueError("STORAGE_BACKEND must be either 'local' or 'supabase'")
        if self.storage_backend == "supabase":
            if not self.supabase_url or not self.supabase_service_role_key:
                raise ValueError(
                    "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required "
                    "when STORAGE_BACKEND=supabase"
                )
            self.supabase_url = self.supabase_url.rstrip("/")
        return self
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to avoid reloading .env on every request.
    """
    return Settings()


# Global settings instance
settings = get_settings()

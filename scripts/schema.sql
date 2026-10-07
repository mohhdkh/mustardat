-- Lost & Found Image-Matching System
-- PostgreSQL Database Schema with pgvector extension
-- 
-- Run this script to create the database schema manually.
-- Alternatively, use Alembic migrations for version control.

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ===========================================
-- USERS TABLE
-- ===========================================
-- Stores user accounts and authentication info.
-- Personal info is only revealed after mutual match confirmation.

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    phone_number VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

CREATE INDEX idx_users_email ON users(email);

-- ===========================================
-- ITEM TYPES ENUM
-- ===========================================

CREATE TYPE item_type AS ENUM (
    'phone', 'wallet', 'keys', 'bag', 'laptop', 'tablet',
    'watch', 'jewelry', 'glasses', 'headphones', 'camera',
    'documents', 'pet', 'clothing', 'electronics', 'other'
);

-- ===========================================
-- ITEM STATUS ENUM
-- ===========================================

CREATE TYPE item_status AS ENUM (
    'active', 'matched', 'resolved', 'expired', 'cancelled'
);

-- ===========================================
-- ITEMS TABLE
-- ===========================================
-- Lost or found item listings with location and metadata.

CREATE TABLE items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    item_type item_type NOT NULL,
    lost_or_found VARCHAR(10) NOT NULL CHECK (lost_or_found IN ('lost', 'found')),
    status item_status DEFAULT 'active',
    title VARCHAR(255) NOT NULL,
    description TEXT,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    location_name VARCHAR(255),
    event_date TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_items_user_id ON items(user_id);
CREATE INDEX idx_items_item_type ON items(item_type);
CREATE INDEX idx_items_lost_or_found ON items(lost_or_found);
CREATE INDEX idx_items_status ON items(status);
CREATE INDEX idx_items_event_date ON items(event_date);
CREATE INDEX idx_items_location ON items(latitude, longitude);

-- ===========================================
-- IMAGES TABLE
-- ===========================================
-- Uploaded images with S3 paths and EXIF metadata.

CREATE TABLE images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    original_filename VARCHAR(255) NOT NULL,
    s3_key_original VARCHAR(512) NOT NULL UNIQUE,
    s3_key_processed VARCHAR(512),
    s3_key_thumbnail VARCHAR(512),
    content_type VARCHAR(50) NOT NULL,
    file_size INTEGER NOT NULL,
    width INTEGER,
    height INTEGER,
    exif_data JSONB,
    exif_latitude DOUBLE PRECISION,
    exif_longitude DOUBLE PRECISION,
    exif_datetime TIMESTAMPTZ,
    is_processed BOOLEAN DEFAULT FALSE,
    processing_error TEXT,
    display_order INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_images_item_id ON images(item_id);
CREATE INDEX idx_images_is_processed ON images(is_processed);

-- ===========================================
-- IMAGE EMBEDDINGS TABLE
-- ===========================================
-- Vector embeddings and perceptual features for similarity search.
-- Uses pgvector for efficient vector operations.

CREATE TABLE image_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    image_id UUID NOT NULL UNIQUE REFERENCES images(id) ON DELETE CASCADE,
    
    -- CLIP embedding (512 dimensions for ViT-B/32)
    embedding vector(512) NOT NULL,
    
    -- Perceptual hashes (64-bit as hex strings)
    phash VARCHAR(16) NOT NULL,
    dhash VARCHAR(16),
    ahash VARCHAR(16),
    
    -- ORB descriptors (serialized numpy arrays)
    orb_keypoints_count INTEGER DEFAULT 0,
    orb_descriptors BYTEA,
    orb_keypoints BYTEA,
    
    -- YOLO detection info
    detected_class VARCHAR(100),
    detection_confidence DOUBLE PRECISION,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_embeddings_image_id ON image_embeddings(image_id);
CREATE INDEX idx_embeddings_phash ON image_embeddings(phash);

-- Create HNSW index for fast vector similarity search
-- This enables efficient approximate nearest neighbor search
CREATE INDEX idx_embeddings_vector ON image_embeddings 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ===========================================
-- MATCH STATUS ENUM
-- ===========================================

CREATE TYPE match_status AS ENUM (
    'pending', 'source_confirmed', 'target_confirmed', 
    'both_confirmed', 'rejected', 'expired'
);

-- ===========================================
-- MATCHES TABLE
-- ===========================================
-- Potential matches between lost and found items.
-- Stores similarity scores and confirmation status.

CREATE TABLE matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    target_item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    
    -- Similarity scores (0-1, higher is better)
    overall_score DOUBLE PRECISION NOT NULL,
    vector_similarity DOUBLE PRECISION NOT NULL,
    phash_similarity DOUBLE PRECISION NOT NULL,
    orb_match_score DOUBLE PRECISION NOT NULL,
    location_score DOUBLE PRECISION NOT NULL,
    distance_km DOUBLE PRECISION NOT NULL,
    score_details JSONB,
    
    -- Status tracking
    status match_status DEFAULT 'pending',
    source_confirmed_at TIMESTAMPTZ,
    target_confirmed_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    rejected_by VARCHAR(10) CHECK (rejected_by IN ('source', 'target')),
    rejection_reason VARCHAR(500),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent duplicate matches
    UNIQUE(source_item_id, target_item_id)
);

CREATE INDEX idx_matches_source_item ON matches(source_item_id);
CREATE INDEX idx_matches_target_item ON matches(target_item_id);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_matches_overall_score ON matches(overall_score DESC);

-- ===========================================
-- NOTIFICATION TYPE ENUM
-- ===========================================

CREATE TYPE notification_type AS ENUM (
    'match_found', 'match_confirmed', 'match_rejected',
    'contact_revealed', 'item_expired', 'system'
);

-- ===========================================
-- NOTIFICATION CHANNEL ENUM
-- ===========================================

CREATE TYPE notification_channel AS ENUM (
    'email', 'sms', 'push'
);

-- ===========================================
-- NOTIFICATIONS TABLE
-- ===========================================
-- Notification records for email/SMS delivery tracking.

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type notification_type NOT NULL,
    channel notification_channel DEFAULT 'email',
    subject VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    related_item_id UUID,
    related_match_id UUID,
    metadata JSONB,
    is_sent BOOLEAN DEFAULT FALSE,
    is_read BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    send_error TEXT,
    retry_count INTEGER DEFAULT 0,
    external_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_type ON notifications(notification_type);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- ===========================================
-- HELPER FUNCTIONS
-- ===========================================

-- Function to calculate distance between two points (Haversine formula)
CREATE OR REPLACE FUNCTION calculate_distance_km(
    lat1 DOUBLE PRECISION,
    lon1 DOUBLE PRECISION,
    lat2 DOUBLE PRECISION,
    lon2 DOUBLE PRECISION
) RETURNS DOUBLE PRECISION AS $$
DECLARE
    R DOUBLE PRECISION := 6371; -- Earth's radius in km
    dlat DOUBLE PRECISION;
    dlon DOUBLE PRECISION;
    a DOUBLE PRECISION;
    c DOUBLE PRECISION;
BEGIN
    dlat := radians(lat2 - lat1);
    dlon := radians(lon2 - lon1);
    a := sin(dlat/2) * sin(dlat/2) + 
         cos(radians(lat1)) * cos(radians(lat2)) * 
         sin(dlon/2) * sin(dlon/2);
    c := 2 * atan2(sqrt(a), sqrt(1-a));
    RETURN R * c;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_items_updated_at
    BEFORE UPDATE ON items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_images_updated_at
    BEFORE UPDATE ON images
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_matches_updated_at
    BEFORE UPDATE ON matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===========================================
-- COMMENTS
-- ===========================================

COMMENT ON TABLE users IS 'User accounts with authentication and profile info';
COMMENT ON TABLE items IS 'Lost and found item listings';
COMMENT ON TABLE images IS 'Uploaded images with S3 paths and EXIF metadata';
COMMENT ON TABLE image_embeddings IS 'Vector embeddings and perceptual features for matching';
COMMENT ON TABLE matches IS 'Potential matches between lost and found items';
COMMENT ON TABLE notifications IS 'Email/SMS notification records';

COMMENT ON COLUMN image_embeddings.embedding IS 'CLIP ViT-B/32 embedding (512 dimensions)';
COMMENT ON COLUMN image_embeddings.phash IS 'Perceptual hash for visual similarity';
COMMENT ON COLUMN image_embeddings.orb_descriptors IS 'Serialized ORB descriptors for geometric matching';
COMMENT ON COLUMN matches.overall_score IS 'Weighted combination of all similarity scores (0-1)';

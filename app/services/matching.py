"""
Matching engine for finding similar items.

Matching pipeline:
1. Metadata filter: same item type + time range
2. Vector similarity (cosine) using numpy → top 50
3. Re-rank using multiple signals:
   - Cosine similarity (CLIP embeddings)
   - pHash difference
   - ORB match count
4. Return top 10 matches with scores
"""

import json
import pickle
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass

import numpy as np
import cv2
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.item import Item, ItemType, ItemStatus
from app.models.image import Image
from app.models.embedding import ImageEmbedding
from app.models.match import Match, MatchStatus


@dataclass
class MatchCandidate:
    """Intermediate match candidate with scores."""
    item_id: str
    image_id: str
    embedding_id: str
    
    # Raw data
    embedding_json: str
    phash: str
    orb_descriptors: Optional[bytes]
    orb_keypoints: Optional[bytes]
    
    # Item metadata
    event_date: datetime
    
    # Computed scores (0-1, higher is better)
    vector_similarity: float = 0.0
    phash_similarity: float = 0.0
    orb_match_score: float = 0.0
    overall_score: float = 0.0


@dataclass
class MatchResult:
    """Final match result to return."""
    item_id: str
    overall_score: float
    vector_similarity: float
    phash_similarity: float
    orb_match_score: float
    score_details: Dict[str, Any]


class MatchingEngine:
    """
    Engine for finding and ranking potential matches between items.
    
    Uses a multi-stage pipeline:
    1. Coarse filtering with metadata
    2. Vector similarity search using numpy
    3. Fine-grained re-ranking with multiple signals
    """
    
    def __init__(self):
        # Scoring weights (must sum to 1.0)
        self.weights = {
            'vector': 0.50,    # CLIP embedding similarity
            'phash': 0.30,     # Perceptual hash similarity
            'orb': 0.20,       # ORB keypoint matches
        }
        
        # ORB matcher for keypoint matching
        self.bf_matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    
    def _compute_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def _compute_phash_similarity(self, hash1: str, hash2: str) -> float:
        """
        Compute similarity between two perceptual hashes.
        
        Uses Hamming distance, converted to similarity score (0-1).
        Max Hamming distance for 64-bit hash is 64.
        """
        if not hash1 or not hash2:
            return 0.0
        
        try:
            # Convert hex strings to integers
            int1 = int(hash1, 16)
            int2 = int(hash2, 16)
            
            # Compute Hamming distance
            xor = int1 ^ int2
            hamming_distance = bin(xor).count('1')
            
            # Convert to similarity (0-1)
            similarity = 1.0 - (hamming_distance / 64.0)
            return max(0.0, similarity)
        except Exception:
            return 0.0
    
    def _compute_orb_match_score(
        self,
        desc1: Optional[bytes],
        desc2: Optional[bytes]
    ) -> float:
        """
        Compute ORB keypoint match score between two images.
        
        Uses brute-force matching with Hamming distance.
        """
        if desc1 is None or desc2 is None:
            return 0.0
        
        try:
            # Deserialize descriptors
            descriptors1 = pickle.loads(desc1)
            descriptors2 = pickle.loads(desc2)
            
            if descriptors1 is None or descriptors2 is None:
                return 0.0
            
            if len(descriptors1) == 0 or len(descriptors2) == 0:
                return 0.0
            
            # Match descriptors
            matches = self.bf_matcher.match(descriptors1, descriptors2)
            
            # Filter good matches (distance < threshold)
            good_matches = [m for m in matches if m.distance < 50]
            
            # Score based on number of good matches
            min_desc = min(len(descriptors1), len(descriptors2))
            if min_desc == 0:
                return 0.0
            
            score = len(good_matches) / min_desc
            return min(1.0, score)
        except Exception as e:
            print(f"ORB matching error: {e}")
            return 0.0
    
    async def find_matches(
        self,
        db: AsyncSession,
        source_item_id: str,
        time_range_days: Optional[int] = None,
        min_score: Optional[float] = None,
        top_k: int = None
    ) -> List[MatchResult]:
        """
        Find matching items for a source item.
        
        Args:
            db: Database session
            source_item_id: ID of the item to find matches for
            time_range_days: Time range in days
            min_score: Minimum overall score threshold
            top_k: Number of top matches to return
        
        Returns:
            List of MatchResult sorted by overall score
        """
        # Apply defaults
        time_range_days = (
            settings.default_time_range_days
            if time_range_days is None
            else time_range_days
        )
        min_score = (
            settings.vector_similarity_threshold
            if min_score is None
            else min_score
        )
        top_k = settings.final_top_k_matches if top_k is None else top_k
        
        # Get source item with images and embeddings
        source_result = await db.execute(
            select(Item)
            .options(
                selectinload(Item.images).selectinload(Image.embedding)
            )
            .where(Item.id == source_item_id)
        )
        source_item = source_result.scalar_one_or_none()
        
        if not source_item:
            raise ValueError(f"Item not found: {source_item_id}")
        
        if not source_item.images:
            raise ValueError("Item has no images")
        
        # Get source embeddings
        source_embeddings = []
        for img in source_item.images:
            if img.embedding:
                source_embeddings.append(img.embedding)
        
        if not source_embeddings:
            raise ValueError("Item images have not been processed")
        
        # Parse source embedding
        source_embedding = np.array(json.loads(source_embeddings[0].embedding_json))
        source_phash = source_embeddings[0].phash
        source_orb = source_embeddings[0].orb_descriptors
        
        # Determine opposite type (lost searches found, found searches lost)
        target_type = "found" if source_item.lost_or_found == "lost" else "lost"
        
        # Calculate time range
        time_min = source_item.event_date - timedelta(days=time_range_days)
        time_max = source_item.event_date + timedelta(days=time_range_days)
        
        # Query candidate items with metadata filters
        candidates_query = (
            select(Item, Image, ImageEmbedding)
            .join(Image, Item.id == Image.item_id)
            .join(ImageEmbedding, Image.id == ImageEmbedding.image_id)
            .where(
                and_(
                    Item.item_type == source_item.item_type,
                    Item.lost_or_found == target_type,
                    Item.status == ItemStatus.ACTIVE.value,
                    Item.id != source_item_id,
                    Item.event_date >= time_min,
                    Item.event_date <= time_max
                )
            )
        )
        
        result = await db.execute(candidates_query)
        rows = result.all()
        
        # Build candidates
        candidates = []
        seen_items = set()  # Only keep one image per item
        
        for item, image, embedding in rows:
            if item.id in seen_items:
                continue
            
            seen_items.add(item.id)
            
            candidate = MatchCandidate(
                item_id=item.id,
                image_id=image.id,
                embedding_id=embedding.id,
                embedding_json=embedding.embedding_json,
                phash=embedding.phash,
                orb_descriptors=embedding.orb_descriptors,
                orb_keypoints=embedding.orb_keypoints,
                event_date=item.event_date
            )
            candidates.append(candidate)
        
        if not candidates:
            return []
        
        # Compute similarity scores for all candidates
        for candidate in candidates:
            # Vector similarity
            candidate_embedding = np.array(json.loads(candidate.embedding_json))
            candidate.vector_similarity = self._compute_cosine_similarity(
                source_embedding, candidate_embedding
            )
            
            # pHash similarity
            candidate.phash_similarity = self._compute_phash_similarity(
                source_phash, candidate.phash
            )
            
            # ORB match score
            candidate.orb_match_score = self._compute_orb_match_score(
                source_orb, candidate.orb_descriptors
            )
            
            # Compute weighted overall score
            candidate.overall_score = (
                self.weights['vector'] * candidate.vector_similarity +
                self.weights['phash'] * candidate.phash_similarity +
                self.weights['orb'] * candidate.orb_match_score
            )
        
        # Sort by overall score (descending)
        candidates.sort(key=lambda x: x.overall_score, reverse=True)
        
        # Filter by minimum score and take top K
        filtered = [c for c in candidates if c.overall_score >= min_score]
        top_candidates = filtered[:top_k]
        
        # Convert to MatchResult
        results = []
        for c in top_candidates:
            result = MatchResult(
                item_id=c.item_id,
                overall_score=c.overall_score,
                vector_similarity=c.vector_similarity,
                phash_similarity=c.phash_similarity,
                orb_match_score=c.orb_match_score,
                score_details={
                    'weights': self.weights,
                }
            )
            results.append(result)
        
        return results
    
    async def create_matches(
        self,
        db: AsyncSession,
        source_item_id: str,
        match_results: List[MatchResult]
    ) -> List[Match]:
        """
        Create Match records in the database for found matches.
        """
        matches = []
        
        for result in match_results:
            # A match is one relationship between two items. Do not create a
            # second record when the other owner searches in reverse.
            existing = await db.execute(
                select(Match).where(
                    or_(
                        and_(
                            Match.source_item_id == source_item_id,
                            Match.target_item_id == result.item_id,
                        ),
                        and_(
                            Match.source_item_id == result.item_id,
                            Match.target_item_id == source_item_id,
                        ),
                    )
                )
            )
            
            if existing.scalar_one_or_none():
                continue  # Skip existing match
            
            match = Match(
                source_item_id=source_item_id,
                target_item_id=result.item_id,
                overall_score=result.overall_score,
                vector_similarity=result.vector_similarity,
                phash_similarity=result.phash_similarity,
                orb_match_score=result.orb_match_score,
                score_details_json=json.dumps(result.score_details),
                status=MatchStatus.PENDING.value
            )
            
            db.add(match)
            matches.append(match)
        
        await db.commit()
        
        # Refresh to get IDs
        for match in matches:
            await db.refresh(match)
        
        return matches


# Singleton instance
matching_engine = MatchingEngine()

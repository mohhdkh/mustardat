"""
Image processing pipeline for the Lost & Found system.

Processing steps:
1. Fix orientation using EXIF data
2. Resize to standard dimensions
3. YOLO object detection and cropping
4. Generate CLIP embeddings
5. Generate perceptual hash (pHash)
6. Extract ORB descriptors
"""

import io
import pickle
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ExifTags

# The full AI stack is optional in local development. OpenCV provides a
# deterministic fallback so uploads can still be processed and matched.
try:
    import imagehash
except ImportError:
    imagehash = None

try:
    import torch
    from ultralytics import YOLO
    import open_clip
except ImportError:
    torch = None
    YOLO = None
    open_clip = None

from app.config import settings


@dataclass
class ProcessingResult:
    """Result of image processing pipeline."""
    processed_image: bytes           # Processed/cropped image as bytes
    thumbnail: bytes                 # Thumbnail image as bytes
    embedding: np.ndarray            # CLIP embedding vector
    phash: str                       # Perceptual hash (hex string)
    dhash: str                       # Difference hash
    ahash: str                       # Average hash
    orb_descriptors: Optional[bytes] # Serialized ORB descriptors
    orb_keypoints: Optional[bytes]   # Serialized keypoint coordinates
    orb_keypoints_count: int         # Number of keypoints
    detected_class: Optional[str]    # YOLO detected class
    detection_confidence: Optional[float]  # YOLO confidence
    width: int                       # Processed image width
    height: int                      # Processed image height
    exif_data: Optional[Dict[str, Any]]  # Extracted EXIF metadata


class ImageProcessor:
    """
    Image processing pipeline using YOLO, OpenCV, and CLIP.
    
    Thread-safe singleton that loads models once and reuses them.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if ImageProcessor._initialized:
            return
        
        # Set device (GPU if available)
        self.device = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"
        print(f"ImageProcessor using device: {self.device}")
        
        # Initialize models lazily
        self._yolo_model = None
        self._clip_model = None
        self._clip_preprocess = None
        self._clip_tokenizer = None
        
        # ORB detector configuration
        self.orb = cv2.ORB_create(
            nfeatures=500,      # Max keypoints
            scaleFactor=1.2,
            nlevels=8,
            edgeThreshold=31,
            patchSize=31
        )
        
        # Standard image dimensions
        self.target_size = (640, 640)  # For YOLO
        self.embedding_size = (224, 224)  # For CLIP
        self.thumbnail_size = (256, 256)
        
        ImageProcessor._initialized = True
    
    @property
    def yolo_model(self):
        """Lazy load YOLO model."""
        if YOLO is None:
            return None
        if self._yolo_model is None:
            print("Loading YOLO model...")
            self._yolo_model = YOLO(settings.yolo_model_path)
            self._yolo_model.to(self.device)
        return self._yolo_model
    
    @property
    def clip_model(self):
        """Lazy load CLIP model."""
        if open_clip is None or torch is None:
            return None
        if self._clip_model is None:
            print("Loading CLIP model...")
            model, _, preprocess = open_clip.create_model_and_transforms(
                'ViT-B-32',
                pretrained='laion2b_s34b_b79k'
            )
            self._clip_model = model.to(self.device)
            self._clip_preprocess = preprocess
            self._clip_model.eval()
        return self._clip_model
    
    @property
    def clip_preprocess(self):
        """Get CLIP preprocessing transform."""
        if open_clip is None or torch is None:
            return None
        if self._clip_preprocess is None:
            _ = self.clip_model  # Trigger lazy load
        return self._clip_preprocess
    
    def extract_exif(self, image: Image.Image) -> Dict[str, Any]:
        """
        Extract EXIF metadata from image.
        
        Returns dict with relevant metadata including GPS coordinates.
        """
        exif_data = {}
        
        try:
            raw_exif = image._getexif()
            if raw_exif is None:
                return exif_data
            
            # Map EXIF tag IDs to names
            for tag_id, value in raw_exif.items():
                tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                
                # Skip binary data
                if isinstance(value, bytes):
                    continue
                
                # Handle GPS info specially
                if tag_name == 'GPSInfo':
                    gps_data = self._parse_gps_info(value)
                    if gps_data:
                        exif_data['gps'] = gps_data
                else:
                    # Convert to string for JSON serialization
                    try:
                        exif_data[str(tag_name)] = str(value)
                    except:
                        pass
            
        except Exception as e:
            print(f"EXIF extraction error: {e}")
        
        return exif_data
    
    def _parse_gps_info(self, gps_info: dict) -> Optional[Dict[str, float]]:
        """Parse GPS EXIF data into lat/lng coordinates."""
        try:
            # GPS tag IDs
            GPS_LATITUDE = 2
            GPS_LATITUDE_REF = 1
            GPS_LONGITUDE = 4
            GPS_LONGITUDE_REF = 3
            
            def convert_to_degrees(value):
                """Convert GPS coordinates to degrees."""
                d, m, s = value
                return float(d) + float(m) / 60 + float(s) / 3600
            
            if GPS_LATITUDE in gps_info and GPS_LONGITUDE in gps_info:
                lat = convert_to_degrees(gps_info[GPS_LATITUDE])
                lng = convert_to_degrees(gps_info[GPS_LONGITUDE])
                
                # Apply reference direction
                if gps_info.get(GPS_LATITUDE_REF) == 'S':
                    lat = -lat
                if gps_info.get(GPS_LONGITUDE_REF) == 'W':
                    lng = -lng
                
                return {'latitude': lat, 'longitude': lng}
        except Exception as e:
            print(f"GPS parsing error: {e}")
        
        return None
    
    def fix_orientation(self, image: Image.Image) -> Image.Image:
        """
        Fix image orientation based on EXIF data.
        
        Many phone cameras store images rotated with EXIF orientation tag.
        """
        try:
            exif = image._getexif()
            if exif is None:
                return image
            
            orientation_tag = 274  # EXIF orientation tag
            if orientation_tag not in exif:
                return image
            
            orientation = exif[orientation_tag]
            
            # Apply rotation based on orientation value
            rotations = {
                3: Image.Transpose.ROTATE_180,
                6: Image.Transpose.ROTATE_270,
                8: Image.Transpose.ROTATE_90,
            }
            
            if orientation in rotations:
                image = image.transpose(rotations[orientation])
            
            # Handle mirrored orientations
            if orientation in [2, 4, 5, 7]:
                image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            
        except Exception as e:
            print(f"Orientation fix error: {e}")
        
        return image
    
    def detect_and_crop(
        self,
        image: np.ndarray,
        padding_ratio: float = 0.1
    ) -> Tuple[np.ndarray, Optional[str], Optional[float]]:
        """
        Use YOLO to detect the main object and crop with padding.
        
        Args:
            image: Input image as numpy array (BGR)
            padding_ratio: Padding around detected object (0.1 = 10%)
        
        Returns:
            Tuple of (cropped_image, detected_class, confidence)
        """
        # Run YOLO detection when the optional model is installed. Keeping the
        # original frame is a valid fallback for local/mobile development.
        model = self.yolo_model
        if model is None:
            return image, None, None

        try:
            results = model(image, verbose=False)
        except Exception as exc:
            print(f"YOLO detection unavailable, using full image: {exc}")
            return image, None, None
        
        if len(results) == 0 or len(results[0].boxes) == 0:
            # No detection, return original image
            return image, None, None
        
        # Get the detection with highest confidence
        boxes = results[0].boxes
        confidences = boxes.conf.cpu().numpy()
        best_idx = np.argmax(confidences)
        
        # Get bounding box
        box = boxes.xyxy[best_idx].cpu().numpy()
        x1, y1, x2, y2 = map(int, box)
        
        # Get class name
        class_id = int(boxes.cls[best_idx].cpu().numpy())
        class_name = results[0].names[class_id]
        confidence = float(confidences[best_idx])
        
        # Add padding
        h, w = image.shape[:2]
        pad_w = int((x2 - x1) * padding_ratio)
        pad_h = int((y2 - y1) * padding_ratio)
        
        x1 = max(0, x1 - pad_w)
        y1 = max(0, y1 - pad_h)
        x2 = min(w, x2 + pad_w)
        y2 = min(h, y2 + pad_h)
        
        # Crop image
        cropped = image[y1:y2, x1:x2]
        
        return cropped, class_name, confidence
    
    def generate_embedding(self, image: Image.Image) -> np.ndarray:
        """
        Generate CLIP embedding for an image.
        
        Args:
            image: PIL Image
        
        Returns:
            512-dimensional numpy array (or zeros if CLIP not available)
        """
        if torch is not None and open_clip is not None:
            try:
                image_tensor = self.clip_preprocess(image).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    embedding = self.clip_model.encode_image(image_tensor)
                    embedding = embedding / embedding.norm(dim=-1, keepdim=True)
                return embedding.cpu().numpy().flatten()
            except Exception as exc:
                print(f"CLIP embedding unavailable, using OpenCV fallback: {exc}")

        # 8 x 8 x 8 HSV histogram = 512 dimensions, matching CLIP's output
        # shape. It is normalized so cosine similarity remains meaningful.
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
        histogram = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
        embedding = histogram.flatten().astype(np.float32)
        norm = np.linalg.norm(embedding)
        return embedding / norm if norm > 0 else embedding
    
    def generate_phash(self, image: Image.Image) -> Tuple[str, str, str]:
        """
        Generate perceptual hashes for an image.
        
        Returns:
            Tuple of (phash, dhash, ahash) as hex strings
        """
        if imagehash is not None:
            phash = str(imagehash.phash(image))
            dhash = str(imagehash.dhash(image))
            ahash = str(imagehash.average_hash(image))
            return phash, dhash, ahash

        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)

        # pHash: low-frequency 8x8 DCT values from a 32x32 image.
        resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
        low_frequency = cv2.dct(resized)[:8, :8]
        phash_bits = low_frequency > np.median(low_frequency[1:])

        # dHash and aHash use the same 64-bit hexadecimal representation.
        dhash_image = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
        dhash_bits = dhash_image[:, 1:] > dhash_image[:, :-1]
        ahash_image = cv2.resize(gray, (8, 8), interpolation=cv2.INTER_AREA)
        ahash_bits = ahash_image > ahash_image.mean()

        def bits_to_hex(bits: np.ndarray) -> str:
            value = 0
            for bit in bits.flatten():
                value = (value << 1) | int(bit)
            return f"{value:016x}"

        phash = bits_to_hex(phash_bits)
        dhash = bits_to_hex(dhash_bits)
        ahash = bits_to_hex(ahash_bits)
        
        return phash, dhash, ahash
    
    def extract_orb_features(
        self,
        image: np.ndarray
    ) -> Tuple[Optional[bytes], Optional[bytes], int]:
        """
        Extract ORB keypoints and descriptors.
        
        Args:
            image: Grayscale image as numpy array
        
        Returns:
            Tuple of (serialized_descriptors, serialized_keypoints, count)
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Detect keypoints and compute descriptors
        keypoints, descriptors = self.orb.detectAndCompute(gray, None)
        
        if keypoints is None or len(keypoints) == 0:
            return None, None, 0
        
        # Serialize keypoints (just coordinates for matching)
        kp_coords = np.array([[kp.pt[0], kp.pt[1]] for kp in keypoints], dtype=np.float32)
        
        # Serialize using pickle
        descriptors_bytes = pickle.dumps(descriptors)
        keypoints_bytes = pickle.dumps(kp_coords)
        
        return descriptors_bytes, keypoints_bytes, len(keypoints)
    
    def create_thumbnail(
        self,
        image: Image.Image,
        size: Tuple[int, int] = None
    ) -> bytes:
        """
        Create a thumbnail of the image.
        
        Args:
            image: PIL Image
            size: Target size (width, height)
        
        Returns:
            Thumbnail as JPEG bytes
        """
        if size is None:
            size = self.thumbnail_size
        
        # Create thumbnail maintaining aspect ratio
        thumb = image.copy()
        thumb.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Convert to bytes
        buffer = io.BytesIO()
        thumb.save(buffer, format='JPEG', quality=85)
        return buffer.getvalue()
    
    async def process_image(self, image_data: bytes) -> ProcessingResult:
        """
        Run the complete image processing pipeline.
        
        Args:
            image_data: Raw image bytes
        
        Returns:
            ProcessingResult with all extracted features
        """
        # Load image with PIL
        pil_image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Extract EXIF before any processing
        exif_data = self.extract_exif(pil_image)
        
        # Fix orientation
        pil_image = self.fix_orientation(pil_image)
        
        # Convert to OpenCV format (BGR)
        cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        # YOLO detection and cropping
        cropped_cv, detected_class, confidence = self.detect_and_crop(cv_image)
        
        # Convert cropped back to PIL for CLIP
        cropped_rgb = cv2.cvtColor(cropped_cv, cv2.COLOR_BGR2RGB)
        cropped_pil = Image.fromarray(cropped_rgb)
        
        # Resize for CLIP embedding
        clip_image = cropped_pil.copy()
        clip_image = clip_image.resize(self.embedding_size, Image.Resampling.LANCZOS)
        
        # Generate CLIP embedding
        embedding = self.generate_embedding(clip_image)
        
        # Generate perceptual hashes
        phash, dhash, ahash = self.generate_phash(cropped_pil)
        
        # Extract ORB features
        orb_desc, orb_kp, orb_count = self.extract_orb_features(cropped_cv)
        
        # Create thumbnail
        thumbnail = self.create_thumbnail(cropped_pil)
        
        # Encode processed image as JPEG
        processed_buffer = io.BytesIO()
        cropped_pil.save(processed_buffer, format='JPEG', quality=90)
        processed_bytes = processed_buffer.getvalue()
        
        return ProcessingResult(
            processed_image=processed_bytes,
            thumbnail=thumbnail,
            embedding=embedding,
            phash=phash,
            dhash=dhash,
            ahash=ahash,
            orb_descriptors=orb_desc,
            orb_keypoints=orb_kp,
            orb_keypoints_count=orb_count,
            detected_class=detected_class,
            detection_confidence=confidence,
            width=cropped_pil.width,
            height=cropped_pil.height,
            exif_data=exif_data
        )


# Singleton instance
image_processor = ImageProcessor()

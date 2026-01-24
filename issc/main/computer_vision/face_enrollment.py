import cv2
import numpy as np
# Lazy import DeepFace to avoid TensorFlow loading at startup
# from deepface import DeepFace
import hashlib
from PIL import Image
import os
import time
import json
from typing import Optional

class FaceEnrollment:
    def __init__(self, device='cpu', model_name='Facenet'):
        """
        Initialize face enrollment system using DeepFace library
        
        Args:
            device: Not used (DeepFace handles this)
            model_name: DeepFace model ('Facenet', 'VGG-Face', 'ArcFace', etc.)
        """
        self.model_name = 'Facenet'  # Use Facenet for 128-dim embeddings
        self.is_bgr = True  # OpenCV uses BGR color order
        self.last_error_time = 0  # For throttling error messages
        self._deepface = None  # Lazy-loaded DeepFace module
        
        print(f"✅ FaceEnrollment initialized (DeepFace will load on first use)")
        
        # Note: face_recognition library doesn't need GPU initialization
        # It uses dlib which is CPU-optimized and very fast
    
    @property
    def DeepFace(self):
        """Lazy-load DeepFace only when needed"""
        if self._deepface is None:
            from deepface import DeepFace
            self._deepface = DeepFace
        return self._deepface
        
    def __del__(self):
        """Cleanup resources when object is destroyed"""
        # No cleanup needed for face_recognition library
        pass
    
    def ensure_contiguous_arrays(self, image):
        """Ensures arrays are contiguous in memory - critical for CUDA operations"""
        if not image.flags['C_CONTIGUOUS']:
            return np.ascontiguousarray(image)
        return image
    
    def clean_gpu_memory(self):
        """Manual method to clean up GPU memory when needed"""
        if getattr(self, 'device', 'cpu') == 'cuda':
            try:
                import torch
                torch.cuda.empty_cache()
            except Exception:
                pass
            import gc
            gc.collect()
    
    def detect_faces(self, image):
        """
        Detect faces using DeepFace library
        
        Args:
            image: Input image as numpy array (BGR format from OpenCV)
            
        Returns:
            tuple: (list of cropped face images, annotated original image)
        """
        if image is None or not isinstance(image, np.ndarray):
            return [], image
            
        try:
            # Convert BGR to RGB for DeepFace
            if self.is_bgr and len(image.shape) == 3:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = image
            
            # Detect faces using DeepFace
            face_objs = self.DeepFace.extract_faces(
                img_path=image_rgb,
                detector_backend='mtcnn',  # Use MTCNN for face detection
                enforce_detection=False,  # Don't throw error if no face found
                align=True  # Align faces
            )
            
            cropped_faces = []
            annotated_image = image.copy()
            
            for face_obj in face_objs:
                # Get facial area coordinates
                facial_area = face_obj['facial_area']
                x, y, w, h = facial_area['x'], facial_area['y'], facial_area['w'], facial_area['h']
                
                # Draw rectangle on annotated image
                cv2.rectangle(annotated_image, (x, y), (x+w, y+h), (0, 255, 0), 3)
                
                # Get aligned face (already extracted by DeepFace)
                face = face_obj['face']
                
                # DeepFace returns normalized float array [0,1], convert to uint8 [0,255]
                if face.dtype == np.float32 or face.dtype == np.float64:
                    face = (face * 255).astype(np.uint8)
                
                # Convert RGB back to BGR for OpenCV consistency
                if len(face.shape) == 3:
                    face = cv2.cvtColor(face, cv2.COLOR_RGB2BGR)
                
                # Resize to 160x160 for consistent embedding
                face_resized = cv2.resize(face, (160, 160))
                cropped_faces.append(face_resized)
            
            return cropped_faces, annotated_image
            
        except Exception as e:
            # Rate limit error messages
            current_time = time.time()
            if current_time - self.last_error_time > 5:
                print(f"Error in face detection: {str(e)}")
                self.last_error_time = current_time
            return [], image


    def extract_embeddings(self, face_image):
        """
        Extract embeddings using DeepFace library

        Args:
            face_image: Cropped face image as numpy array (BGR)

        Returns:
            numpy.ndarray: Embedding vector or None if failed
        """
        try:
            # Check if image is valid
            if face_image is None or face_image.size == 0:
                return None
            
            # Convert BGR to RGB for DeepFace
            if self.is_bgr:
                face_rgb = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
            else:
                face_rgb = face_image
            
            # Get face representation (embedding) using DeepFace
            result = self.DeepFace.represent(
                img_path=face_rgb,
                model_name=self.model_name,  # 'Facenet' for 128-dim or 'Facenet512' for 512-dim
                detector_backend='skip',  # Skip detection since face is already cropped
                enforce_detection=False,  # Don't throw error if detection fails
                align=False  # Already aligned during detection
            )
            
            # DeepFace.represent returns list of dicts, get first one
            if result and len(result) > 0:
                embedding = np.array(result[0]['embedding'])
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm
                return embedding
            else:
                return None
                
        except Exception as e:
            # Rate limit error messages
            current_time = time.time()
            if current_time - self.last_error_time > 5:
                print(f"Error extracting embeddings: {str(e)}")
                self.last_error_time = current_time
            return None

    
    def generate_embedding_hash(self, embedding):
        """Generate a hash from an embedding for quick comparisons"""
        if embedding is None:
            return None
        
        # Convert embedding to bytes and create hash
        embedding_bytes = np.array(embedding).tobytes()
        return hashlib.md5(embedding_bytes).hexdigest()
    
    def save_embeddings_to_file(self, embeddings, id_number, output_path='embeddings'):
        """Save embeddings to JSON file for backup or offline processing"""
        os.makedirs(output_path, exist_ok=True)
        
        filename = os.path.join(output_path, f'{id_number}.json')
        
        # Add timestamp and metadata
        data = {
            'id_number': id_number,
            'timestamp': time.time(),
            'embeddings': embeddings
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f)
        
        print(f"Saved embeddings to {filename}")
        return filename
    
    def enroll_face(self, id_number, front_img=None, left_img=None, right_img=None):
        """
        Enroll a face with multiple poses
        
        Args:
            id_number: Unique identifier for the person
            front_img: Front face image as numpy array
            left_img: Left profile face image as numpy array
            right_img: Right profile face image as numpy array
            
        Returns:
            dict: Dictionary containing embeddings for each pose
        """
        print(f"Starting face enrollment for ID: {id_number}")
        embeddings = {}
        
        for pose, img in [("front", front_img), ("left", left_img), ("right", right_img)]:
            if img is not None:
                print(f"Processing {pose} image...")
                # Detect face in the image
                faces, annotated_img = self.detect_faces(img)
                if faces and len(faces) > 0:
                    print(f"Found {len(faces)} face(s) in {pose} image")
                    # Use the first detected face
                    face_img = faces[0]
                    
                    # Extract embeddings with GPU acceleration
                    embedding = self.extract_embeddings(face_img)
                    if embedding is not None:
                        print(f"Successfully extracted embeddings for {pose} image")
                        embeddings[pose] = embedding.tolist()
                    else:
                        print(f"Failed to extract embeddings for {pose} image")
                        embeddings[pose] = None
                else:
                    print(f"No faces detected in {pose} image")
                    embeddings[pose] = None
            else:
                print(f"No {pose} image provided")
                embeddings[pose] = None
        
        print(f"Enrollment complete for ID: {id_number}")
        return embeddings
    
    def compare_faces(self, embedding1, embedding2, threshold=0.6):
        """
        Compare two face embeddings using Euclidean distance
        
        Args:
            embedding1: First face embedding (128-dim)
            embedding2: Second face embedding (128-dim)
            threshold: Distance threshold (default 0.6 for face_recognition)
            
        Returns:
            tuple: (is_match, distance)
        """
        if embedding1 is None or embedding2 is None:
            return False, 1.0
            
        # Convert to numpy arrays if they aren't already
        if not isinstance(embedding1, np.ndarray):
            embedding1 = np.array(embedding1)
        if not isinstance(embedding2, np.ndarray):
            embedding2 = np.array(embedding2)
            
        # Calculate cosine distance on normalized vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        if norm1 == 0 or norm2 == 0:
            return False, 1.0

        cosine_similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        cosine_distance = 1.0 - cosine_similarity

        is_match = cosine_distance < threshold

        return is_match, cosine_distance
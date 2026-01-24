import os
import numpy as np
import torch
import torch.nn.functional as F
import time
import json
from pathlib import Path
from typing import Optional

class FaceMatcher:
    """
    Matches face embeddings against stored embeddings with CPU fallback for CUDA errors
    """
    def __init__(self, use_gpu=False, threshold=0.4):
        """Initialize face matcher with configurable GPU settings"""
        self.embeddings = {}  # Store embeddings as {id_number: embedding}
        self.use_gpu = use_gpu
        self.threshold = threshold
        self.last_error_time = 0
        self.error_cooldown = 5  # seconds
        
        # Check CUDA availability early
        self.has_cuda = torch.cuda.is_available() and self.use_gpu
        
        # Configure GPU settings
        if self.has_cuda:
            try:
                # Configure TensorFlow GPU if installed (optional)
                try:
                    import tensorflow as tf  # type: ignore
                    gpus = tf.config.list_physical_devices('GPU')
                    if gpus:
                        try:
                            for gpu in gpus:
                                tf.config.experimental.set_memory_growth(gpu, True)
                            print("FaceMatcher: TensorFlow GPU configured successfully")
                        except Exception as e:
                            print(f"FaceMatcher: Error configuring TensorFlow GPU: {e}")
                except Exception:
                    pass
                        
                # PyTorch GPU info
                print(f"FaceMatcher: PyTorch CUDA available: {torch.cuda.get_device_name(0)}")
                
                # Clean up any GPU memory at startup
                torch.cuda.empty_cache()
                
            except ImportError:
                pass
    
    def load_embeddings(self):
        """Load face embeddings from database"""
        try:
            from ..models import FacesEmbeddings, AccountRegistration
            
            # Load all embeddings from database
            embedding_records = FacesEmbeddings.objects.all()
            
            for record in embedding_records:
                id_number = record.id_number.id_number
                
                # Create a dictionary of embeddings for this ID
                embeddings_dict = {}
                
                if record.front_embedding:
                    # Convert from database JSON format to numpy
                    if isinstance(record.front_embedding, str):
                        try:
                            front_embedding = json.loads(record.front_embedding)
                        except:
                            front_embedding = record.front_embedding
                    else:
                        front_embedding = record.front_embedding
                    embeddings_dict['front'] = front_embedding
                    
                if record.left_embedding:
                    if isinstance(record.left_embedding, str):
                        try:
                            left_embedding = json.loads(record.left_embedding)
                        except:
                            left_embedding = record.left_embedding
                    else:
                        left_embedding = record.left_embedding
                    embeddings_dict['left'] = left_embedding
                    
                if record.right_embedding:
                    if isinstance(record.right_embedding, str):
                        try:
                            right_embedding = json.loads(record.right_embedding)
                        except:
                            right_embedding = record.right_embedding
                    else:
                        right_embedding = record.right_embedding
                    embeddings_dict['right'] = right_embedding
                
                # Store in our dictionary
                self.embeddings[id_number] = embeddings_dict
                
            print(f"Loaded {len(self.embeddings)} face embeddings")
            
        except Exception as e:
            print(f"Error loading embeddings: {e}")
            # Continue with empty embeddings
    
    def compare_gpu(self, embedding1, embedding2):
        """Compare embeddings using GPU for faster processing"""
        try:
            if not self.has_cuda:
                return self.compare_cpu(embedding1, embedding2)
            
            # Convert to tensors on GPU
            emb1 = torch.tensor(embedding1, dtype=torch.float32, device='cuda')
            emb2 = torch.tensor(embedding2, dtype=torch.float32, device='cuda')
            
            # Normalize embeddings
            emb1_norm = F.normalize(emb1, p=2, dim=0)
            emb2_norm = F.normalize(emb2, p=2, dim=0)
            
            # Calculate cosine similarity
            similarity = torch.dot(emb1_norm, emb2_norm)
            
            # Return distance (lower is better) and move back to CPU
            distance = 1.0 - similarity.cpu().item()
            return distance
            
        except Exception as e:
            print(f"GPU comparison error, falling back to CPU: {e}")
            return self.compare_cpu(embedding1, embedding2)
    
    def compare_cpu(self, embedding1, embedding2):
        """Compare embeddings using CPU for reliability"""
        try:
            # Ensure numpy arrays
            emb1 = np.array(embedding1, dtype=np.float32)
            emb2 = np.array(embedding2, dtype=np.float32)
            
            # Normalize
            emb1 = emb1 / np.linalg.norm(emb1)
            emb2 = emb2 / np.linalg.norm(emb2)
            
            # Calculate cosine similarity
            similarity = np.dot(emb1, emb2)
            
            # Return distance (lower is better)
            return 1.0 - similarity
        except Exception as e:
            print(f"CPU comparison error: {e}")
            return float('inf')  # Indicate failure
    
    def match(self, live_embedding, threshold=None):
        """
        Match a live embedding against stored embeddings with robust error handling
        
        Args:
            live_embedding: Embedding vector of the face to match
            threshold: Optional threshold override (lower = stricter)
            
        Returns:
            tuple: (id_number or None, confidence)
        """
        if threshold is None:
            threshold = self.threshold
            
        if live_embedding is None or len(self.embeddings) == 0:
            return None, 0.0
            
        try:
            print(f"Matching against {len(self.embeddings)} stored embeddings")
            
            # Make sure embedding is numpy array and contiguous
            if not isinstance(live_embedding, np.ndarray):
                live_embedding = np.array(live_embedding, dtype=np.float32)
            
            # Ensure contiguous memory layout (critical for CUDA)
            live_embedding = np.ascontiguousarray(live_embedding, dtype=np.float32)
            
            # CPU approach - more reliable
            best_match_id = None
            best_distance = float('inf')
            
            for id_number, stored_embedding in self.embeddings.items():
                # Handle dict of embeddings or direct embedding
                if isinstance(stored_embedding, dict):
                    # Try front embedding first, then others
                    embedding_list = []
                    if stored_embedding.get('front') is not None:
                        embedding_list.append(stored_embedding['front'])
                    if stored_embedding.get('left') is not None:
                        embedding_list.append(stored_embedding['left'])
                    if stored_embedding.get('right') is not None:
                        embedding_list.append(stored_embedding['right'])
                else:
                    embedding_list = [stored_embedding]
                
                # Find best match across all angles
                for embedding in embedding_list:
                    # Skip if none
                    if embedding is None:
                        continue
                        
                    # Use GPU-accelerated comparison when available
                    distance = self.compare_gpu(live_embedding, embedding)
                    
                    # Update best match
                    if distance < best_distance:
                        best_distance = distance
                        best_match_id = id_number
            
            # Print for debugging
            if best_match_id:
                print(f"Best match: {best_match_id}, distance: {best_distance}")
                
            # Return match if distance is below threshold
            if best_distance < threshold:
                return best_match_id, 1.0 - best_distance  # Return ID and confidence
            else:
                return None, 0.0
                
        except Exception as e:
            current_time = time.time()
            if current_time - self.last_error_time > self.error_cooldown:
                print(f"Error in match: {str(e)}")
                self.last_error_time = current_time
            return None, 0.0
    
    def debug_embedding(self, embedding):
        """Print debug info about an embedding"""
        if embedding is None:
            print("Embedding is None")
            return
            
        try:
            if isinstance(embedding, list):
                print(f"Embedding is a list of length {len(embedding)}")
                embedding = np.array(embedding)
            
            if isinstance(embedding, np.ndarray):
                print(f"Embedding shape: {embedding.shape}")
                print(f"Embedding dtype: {embedding.dtype}")
                print(f"Embedding min: {np.min(embedding)}, max: {np.max(embedding)}")
                print(f"Embedding mean: {np.mean(embedding)}")
                print(f"Embedding is contiguous: {embedding.flags['C_CONTIGUOUS']}")
            else:
                print(f"Embedding type: {type(embedding)}")
        except Exception as e:
            print(f"Error debugging embedding: {e}")
    
    def optimize_embeddings(self):
        """Make sure all stored embeddings are in optimal format"""
        optimized_count = 0
        
        try:
            for id_number, stored_embedding in self.embeddings.items():
                if isinstance(stored_embedding, dict):
                    for angle in stored_embedding:
                        if stored_embedding[angle] is not None:
                            # Ensure numpy array
                            if not isinstance(stored_embedding[angle], np.ndarray):
                                stored_embedding[angle] = np.array(stored_embedding[angle], dtype=np.float32)
                            
                            # Ensure contiguous
                            if not stored_embedding[angle].flags['C_CONTIGUOUS']:
                                stored_embedding[angle] = np.ascontiguousarray(stored_embedding[angle], dtype=np.float32)
                                optimized_count += 1
                else:
                    # Convert to numpy if needed
                    if not isinstance(stored_embedding, np.ndarray):
                        self.embeddings[id_number] = np.array(stored_embedding, dtype=np.float32)
                        optimized_count += 1
                    
                    # Ensure contiguous
                    if not self.embeddings[id_number].flags['C_CONTIGUOUS']:
                        self.embeddings[id_number] = np.ascontiguousarray(self.embeddings[id_number], dtype=np.float32)
                        optimized_count += 1
                        
            print(f"Optimized {optimized_count} embeddings")
        except Exception as e:
            print(f"Error optimizing embeddings: {e}")
    
    def extract_embedding_fast(self, face_image):
        """Lightning-fast embedding extraction optimized for speed"""
        try:
            # Quick preprocessing
            if face_image.shape[0] < 20 or face_image.shape[1] < 20:
                return None
            
            # Use existing face detector for speed
            if hasattr(self, 'face_detector') and self.face_detector:
                embedding = self.face_detector.extract_embeddings(face_image)
                return embedding
            else:
                # Fallback to simple feature extraction if no detector
                return self._simple_feature_extraction(face_image)
                
        except Exception as e:
            return None
    
    def match_fast(self, embedding):
        """Lightning-fast face matching optimized for speed"""
        if embedding is None or len(self.embeddings) == 0:
            return None, 0.0
        
        try:
            best_match_id = None
            best_confidence = 0.0
            
            # Quick comparison using numpy operations
            embedding = np.array(embedding, dtype=np.float32)
            
            for id_number, stored_embedding in self.embeddings.items():
                try:
                    # Fast cosine similarity
                    stored_embedding = np.array(stored_embedding, dtype=np.float32)
                    
                    # Normalize vectors
                    embedding_norm = embedding / (np.linalg.norm(embedding) + 1e-8)
                    stored_norm = stored_embedding / (np.linalg.norm(stored_embedding) + 1e-8)
                    
                    # Cosine similarity
                    similarity = np.dot(embedding_norm, stored_norm)
                    
                    if similarity > best_confidence:
                        best_confidence = float(similarity)
                        best_match_id = id_number
                        
                except Exception:
                    continue
            
            # Return match if above threshold
            if best_confidence > self.threshold:
                return best_match_id, best_confidence
            else:
                return None, best_confidence
                
        except Exception as e:
            return None, 0.0
    
    def _simple_feature_extraction(self, face_image):
        """Simple feature extraction as fallback"""
        try:
            # Resize to standard size
            import cv2
            face_resized = cv2.resize(face_image, (64, 64))
            
            # Convert to grayscale and flatten
            gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
            features = gray.flatten().astype(np.float32)
            
            # Normalize
            features = features / (np.linalg.norm(features) + 1e-8)
            
            return features
            
        except Exception:
            return None

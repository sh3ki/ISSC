"""
ISSC Face Recognition Engine
Optimized for real-time face recognition in live feed
Carbon copy of PROTECH implementation - WITHOUT spoofing detection
"""
import os
import numpy as np
from django.conf import settings
from main.models import AccountRegistration, FacesEmbeddings
import threading
import time
import json

class FaceRecognitionEngine:
    """Singleton class for managing face recognition"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.embeddings_cache = {}  # {id_number: embeddings_array}
        self.user_info_cache = {}  # {id_number: {'first_name': ..., 'last_name': ...}}
        self.last_cache_update = 0
        self.cache_ttl = 300  # Refresh cache every 5 minutes
        self.match_threshold = 0.95  # Very strict - only accept 95%+ confidence
        
        print(f"✅ ISSC Face Recognition Engine initialized")
        
        # Pre-compute normalized embeddings for ultra-fast comparison
        self.normalized_embeddings_cache = {}  # {id_number: normalized_embeddings}
        
        # Load all embeddings into memory at startup
        self.load_all_embeddings()
    
    def load_all_embeddings(self):
        """Load all user face embeddings into memory for ultra-fast comparison"""
        print("Loading face embeddings into memory...")
        start_time = time.time()
        
        try:
            # Get all users with face embeddings (status='allowed')
            users = AccountRegistration.objects.filter(
                status='allowed'
            ).values('id_number', 'first_name', 'middle_name', 'last_name')
            
            loaded_count = 0
            
            for user in users:
                id_number = user['id_number']
                
                try:
                    # Get face embeddings from database
                    face_embeddings = FacesEmbeddings.objects.filter(
                        id_number__id_number=id_number
                    ).first()
                    
                    if face_embeddings:
                        # Average the three embeddings (front, left, right)
                        embeddings_list = []
                        
                        if face_embeddings.front_embedding:
                            front_emb = np.array(face_embeddings.front_embedding)
                            if front_emb.size > 0:
                                embeddings_list.append(front_emb)
                        
                        if face_embeddings.left_embedding:
                            left_emb = np.array(face_embeddings.left_embedding)
                            if left_emb.size > 0:
                                embeddings_list.append(left_emb)
                        
                        if face_embeddings.right_embedding:
                            right_emb = np.array(face_embeddings.right_embedding)
                            if right_emb.size > 0:
                                embeddings_list.append(right_emb)
                        
                        if embeddings_list:
                            # Average all available embeddings
                            averaged_embedding = np.mean(embeddings_list, axis=0)
                            
                            # Pre-normalize for faster comparison
                            normalized = self._normalize_embedding(averaged_embedding)
                            
                            # Store in cache
                            self.embeddings_cache[id_number] = averaged_embedding
                            self.normalized_embeddings_cache[id_number] = normalized
                            self.user_info_cache[id_number] = {
                                'first_name': user['first_name'],
                                'middle_name': user['middle_name'] or '',
                                'last_name': user['last_name']
                            }
                            loaded_count += 1
                            
                except Exception as e:
                    print(f"Error loading embedding for user {id_number}: {e}")
            
            self.last_cache_update = time.time()
            elapsed = time.time() - start_time
            print(f"✅ Loaded {loaded_count} face embeddings in {elapsed:.2f}s")
            
        except Exception as e:
            print(f"❌ Error in load_all_embeddings: {e}")
    
    def _normalize_embedding(self, embedding):
        """Normalize embedding for cosine similarity"""
        embedding = np.array(embedding).flatten()
        norm = np.linalg.norm(embedding)
        if norm == 0:
            return embedding
        return embedding / norm
    
    def refresh_cache_if_needed(self):
        """Refresh cache if TTL expired"""
        if time.time() - self.last_cache_update > self.cache_ttl:
            self.load_all_embeddings()
    
    def compare_embeddings_vectorized(self, input_embedding, threshold=None):
        """
        Ultra-fast vectorized comparison using pre-normalized embeddings
        
        Args:
            input_embedding: 128-d face embedding from detected face
            threshold: Cosine similarity threshold (default 0.95)
        
        Returns:
            tuple: (id_number, confidence) or (None, 0) if no match
        """
        if threshold is None:
            threshold = self.match_threshold

        if not self.normalized_embeddings_cache:
            return None, 0
        
        # Normalize input embedding
        input_normalized = self._normalize_embedding(input_embedding)
        
        if np.linalg.norm(input_normalized) == 0:
            return None, 0
        
        best_match_id = None
        best_similarity = 0
        
        # Ultra-fast vectorized comparison using pre-normalized embeddings
        for id_number, stored_embedding_normalized in self.normalized_embeddings_cache.items():
            # Fast dot product (cosine similarity with normalized vectors)
            similarity = np.dot(input_normalized, stored_embedding_normalized)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match_id = id_number
        
        # Return match if above threshold
        if best_similarity >= threshold:
            return best_match_id, float(best_similarity)
        
        return None, 0
    
    def recognize_face(self, face_embedding):
        """
        Recognize a face from its embedding
        
        Args:
            face_embedding: Face embedding array
        
        Returns:
            dict: {'id_number': str, 'name': str, 'confidence': float, 'matched': bool}
        """
        # Refresh cache if needed
        self.refresh_cache_if_needed()
        
        # Compare against all cached embeddings
        id_number, confidence = self.compare_embeddings_vectorized(face_embedding, self.match_threshold)
        
        if id_number:
            user_info = self.user_info_cache.get(id_number, {})
            full_name = f"{user_info.get('first_name', '')} {user_info.get('middle_name', '')} {user_info.get('last_name', '')}".replace('  ', ' ').strip()
            
            return {
                'matched': True,
                'id_number': id_number,
                'first_name': user_info.get('first_name', ''),
                'middle_name': user_info.get('middle_name', ''),
                'last_name': user_info.get('last_name', ''),
                'name': full_name,
                'confidence': confidence
            }
        
        return {
            'matched': False,
            'id_number': None,
            'first_name': None,
            'middle_name': None,
            'last_name': None,
            'name': None,
            'confidence': 0
        }
    
    def recognize_multiple_faces(self, face_embeddings_list):
        """
        Recognize multiple faces at once
        
        Args:
            face_embeddings_list: List of face embedding arrays
        
        Returns:
            list: List of recognition results
        """
        results = []
        for face_embedding in face_embeddings_list:
            result = self.recognize_face(face_embedding)
            results.append(result)
        
        return results


# Create singleton instance
face_engine = FaceRecognitionEngine()

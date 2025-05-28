import redis
import json
import uuid
from datetime import datetime
import logging
import os
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, filename='output_logs/memory.log')

class SharedMemory:
    def __init__(self, host=None, port=None, db=0):
        self.host = host or os.getenv('REDIS_HOST', 'localhost')
        self.port = port or int(os.getenv('REDIS_PORT', 6379))
        self.db = db
        self.redis_client = None
        self.fallback_storage = {}  # In-memory fallback
        
        self._connect_redis()

    def _connect_redis(self):
        """Attempt to connect to Redis with fallback to in-memory storage"""
        try:
            self.redis_client = redis.Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)
            self.redis_client.ping()
            logging.info(f"Connected to Redis at {self.host}:{self.port}")
        except redis.ConnectionError as e:
            logging.warning(f"Redis connection failed, using in-memory fallback: {e}")
            self.redis_client = None

    def save_context(self, source: str, input_type: str, intent: str, extracted_data: Dict[str, Any]) -> str:
        thread_id = str(uuid.uuid4())
        context = {
            'source': source,
            'type': input_type,
            'intent': intent,
            'timestamp': datetime.utcnow().isoformat(),
            'extracted_data': extracted_data,
            'thread_id': thread_id
        }
        
        try:
            if self.redis_client:
                self.redis_client.setex(thread_id, 3600, json.dumps(context))  # Expire after 1 hour
                logging.info(f"Saved context to Redis for thread_id: {thread_id}")
            else:
                self.fallback_storage[thread_id] = context
                logging.info(f"Saved context to fallback storage for thread_id: {thread_id}")
            return thread_id
        except Exception as e:
            logging.error(f"Failed to save context: {e}")
            # Fallback to in-memory
            self.fallback_storage[thread_id] = context
            return thread_id

    def get_context(self, thread_id: str) -> Optional[Dict[str, Any]]:
        try:
            if self.redis_client:
                data = self.redis_client.get(thread_id)
                if data:
                    logging.info(f"Retrieved context from Redis for thread_id: {thread_id}")
                    return json.loads(data)
            
            # Check fallback storage
            if thread_id in self.fallback_storage:
                logging.info(f"Retrieved context from fallback storage for thread_id: {thread_id}")
                return self.fallback_storage[thread_id]
                
            logging.warning(f"No context found for thread_id: {thread_id}")
            return None
        except Exception as e:
            logging.error(f"Failed to retrieve context: {e}")
            return self.fallback_storage.get(thread_id)

    def update_context(self, thread_id: str, additional_data: Dict[str, Any]) -> bool:
        """Update existing context with additional data"""
        try:
            context = self.get_context(thread_id)
            if not context:
                return False
                
            context['extracted_data'].update(additional_data)
            context['timestamp'] = datetime.utcnow().isoformat()
            
            if self.redis_client:
                self.redis_client.setex(thread_id, 3600, json.dumps(context))
            else:
                self.fallback_storage[thread_id] = context
                
            logging.info(f"Updated context for thread_id: {thread_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to update context: {e}")
            return False

    def get_all_contexts(self) -> Dict[str, Dict[str, Any]]:
        """Get all stored contexts (for debugging/monitoring)"""
        all_contexts = {}
        
        try:
            if self.redis_client:
                keys = self.redis_client.keys("*")
                for key in keys:
                    try:
                        data = self.redis_client.get(key)
                        if data:
                            all_contexts[key] = json.loads(data)
                    except json.JSONDecodeError:
                        continue
            
            # Add fallback storage
            all_contexts.update(self.fallback_storage)
            
        except Exception as e:
            logging.error(f"Failed to retrieve all contexts: {e}")
            return self.fallback_storage
            
        return all_contexts
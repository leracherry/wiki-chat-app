"""In-memory conversation history storage."""
from typing import Dict, List, Any
import threading
import time

class ConversationStore:
    """Thread-safe in-memory storage for conversation history."""

    def __init__(self, ttl_hours: int = 24):
        self._conversations: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._ttl_seconds = ttl_hours * 3600

    def add_message(self, chat_id: str, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        with self._lock:
            if chat_id not in self._conversations:
                self._conversations[chat_id] = {
                    "messages": [],
                    "last_updated": time.time()
                }

            self._conversations[chat_id]["messages"].append({
                "role": role,
                "content": content
            })
            self._conversations[chat_id]["last_updated"] = time.time()

    def get_messages(self, chat_id: str, max_messages: int = 20) -> List[Dict[str, str]]:
        """Get conversation history for a chat ID."""
        with self._lock:
            self._cleanup_expired()

            if chat_id not in self._conversations:
                return []

            messages = self._conversations[chat_id]["messages"]
            # Return last N messages to avoid token limit issues
            return messages[-max_messages:] if len(messages) > max_messages else messages

    def _cleanup_expired(self) -> None:
        """Remove expired conversations."""
        current_time = time.time()
        expired_chats = [
            chat_id for chat_id, data in self._conversations.items()
            if current_time - data["last_updated"] > self._ttl_seconds
        ]
        for chat_id in expired_chats:
            del self._conversations[chat_id]

# Global instance
conversation_store = ConversationStore()

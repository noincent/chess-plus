from typing import List, Dict, Any
from pathlib import Path
import json
from datetime import datetime
from .types import ChatMessage

class ChatHistory:
    """Manages the history of chat messages with circular buffer behavior."""
    
    def __init__(self, max_messages: int = 50):
        self.messages: List[ChatMessage] = []
        self.max_messages = max_messages
        
    def add(self, message: ChatMessage):
        """Add a new message to the history, removing oldest if at capacity."""
        if len(self.messages) >= self.max_messages:
            self.messages.pop(0)  # Remove oldest message
        self.messages.append(message)
        
    def get_recent_messages(self, count: int) -> List[ChatMessage]:
        """Get the most recent messages from history."""
        return self.messages[-count:] if count > 0 else []
        
    def save_to_file(self, session_id: str, save_dir: Path):
        """Save chat history to a JSON file."""
        history_file = Path(save_dir) / f"chat_history_{session_id}.json"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(history_file, 'w') as f:
            json.dump([msg.dict() for msg in self.messages], f, indent=2)
            
    @classmethod
    def load_from_file(cls, session_id: str, save_dir: Path) -> 'ChatHistory':
        """Load chat history from a JSON file."""
        history_file = Path(save_dir) / f"chat_history_{session_id}.json"
        
        if not history_file.exists():
            return cls()
            
        with open(history_file, 'r') as f:
            messages_data = json.load(f)
            
        history = cls()
        for msg_data in messages_data:
            msg_data['timestamp'] = datetime.fromisoformat(msg_data['timestamp'])
            history.messages.append(ChatMessage(**msg_data))
            
        return history
        
    def get_formatted_history(self, count: int = 3) -> str:
        """Get formatted string of recent message history."""
        recent = self.get_recent_messages(count)
        formatted = []
        
        for msg in recent:
            formatted.extend([
                f"Time: {msg.timestamp.isoformat()}",
                f"Question: {msg.content}",
                f"Generated SQL: {msg.sql_query or 'None'}",
                f"Response: {msg.response or 'None'}",
                "---"
            ])
            
        return "\n".join(formatted)
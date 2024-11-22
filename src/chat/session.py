import uuid
from datetime import datetime
from typing import Dict, Optional, Any
from .types import ChatMessage
from .history import ChatHistory
from .context import ChatContext
from langchain.memory import ConversationBufferWindowMemory
import logging

class ChatSession:
    """Manages a chat session including history, context, and memory."""
    
    def __init__(self, session_id: str, db_id: str, window_size: int = 10, max_history: int = 50):
        self.session_id = session_id
        self.db_id = db_id
        self.history = ChatHistory(max_messages=max_history)
        self.context = ChatContext()
        self.memory = ConversationBufferWindowMemory(k=window_size)
        self.max_history = max_history
        logging.info(f"Created new chat session {session_id} for database {db_id}")
        
    def add_message(self, message: ChatMessage):
        """Add a message to both history and context."""
        logging.info(f"Adding message to history: {message.content}")
        self.history.add(message)
        logging.debug("Message added to history.")
        
        logging.info("Updating context with the new message.")
        self.context.update(message)
        if len(self.context.conversation_history) > self.max_history:
            self.context.conversation_history.pop(0)
        logging.debug("Context updated successfully.")
        
        logging.info("Updating memory with the new message.")
        self._update_memory(message)
        logging.debug("Memory buffer updated successfully.")
        
    def _update_memory(self, message: ChatMessage):
        """Update the conversation memory with the new message."""
        self.memory.save_context(
            {"input": message.content},
            {"output": message.response if message.response else None}
        )
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversation context."""
        return {
            'session_id': self.session_id,
            'db_id': self.db_id,
            'message_count': len(self.history.messages),
            'context': self.context.get_summary(),
            'memory': self.memory.load_memory_variables({})
        }

    def save(self, save_dir: str):
        """Save the session state to disk."""
        self.history.save_to_file(self.session_id, save_dir)
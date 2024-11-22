from typing import Dict, List, Any, Optional
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseMessage

class ChatMemoryManager:
    """Manages memory for chat sessions with enhanced functionality."""
    
    def __init__(self, window_size: int = 10, relevance_threshold: float = 0.7):
        self.memory = ConversationBufferWindowMemory(k=window_size)
        self.relevance_threshold = relevance_threshold
        self.message_metadata: Dict[str, Any] = {}
        
    def add_message(self, message: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """Add a message to memory with optional metadata."""
        self.memory.save_context(
            {"input": message.get("content")},
            {"output": message.get("response")}
        )
        
        if metadata:
            message_id = message.get("id", str(len(self.message_metadata)))
            self.message_metadata[message_id] = metadata
            
    def get_relevant_history(self, current_context: Dict[str, Any]) -> List[BaseMessage]:
        """Get relevant message history based on current context."""
        messages = self.memory.chat_memory.messages
        
        # If we have no context matching logic yet, return all messages
        return messages
        
    def get_memory_variables(self) -> Dict[str, Any]:
        """Get all variables stored in memory."""
        return self.memory.load_memory_variables({})
        
    def clear(self):
        """Clear all memory."""
        self.memory.clear()
        self.message_metadata.clear()

    def get_context_window(self) -> List[Dict[str, Any]]:
        """Get the current context window as a list of messages."""
        messages = self.memory.chat_memory.messages
        return [
            {
                "content": msg.content,
                "type": msg.type,
                "metadata": self.message_metadata.get(str(i), {})
            }
            for i, msg in enumerate(messages)
        ]
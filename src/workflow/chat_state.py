from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime

from runner.task import Task
from workflow.system_state import SystemState
from chat.context import ChatContext
from chat.types import ChatMessage

class ChatSystemState(SystemState):
    """Extended system state that includes chat functionality."""
    
    chat_context: Optional[ChatContext] = None
    chat_memory: Optional[List[ChatMessage]] = None
    chat_session_id: Optional[str] = None
    
    def update_chat_context(self,
                          message: str,
                          tables: List[str],
                          columns: List[str],
                          query_result: Optional[Dict[str, Any]] = None):
        """Update the chat context with new information."""
        if not self.chat_context:
            self.chat_context = ChatContext()
            
        self.chat_context.referenced_tables.update(tables)
        self.chat_context.referenced_columns.update(columns)
        if query_result:
            self.chat_context.last_query_result = query_result
            
    def get_chat_history(self) -> List[Dict[str, Any]]:
        """Get the chat history."""
        if self.chat_memory:
            return [msg.dict() for msg in self.chat_memory]
        return []
    
    def clear_chat_context(self):
        """Clear the chat context and memory."""
        if self.chat_context:
            self.chat_context.clear()
        if self.chat_memory:
            self.chat_memory.clear()
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary, including chat information."""
        base_dict = super().to_dict()
        chat_dict = {
            'chat_session_id': self.chat_session_id,
            'chat_context': self.chat_context.get_summary() if self.chat_context else None,
            'chat_history_length': len(self.get_chat_history())
        }
        return {**base_dict, **chat_dict}
    
    def get_formatted_history(self, max_messages: int = 3) -> str:
        """
        Format recent chat history into a string with improved context.
        
        Args:
            max_messages (int): Maximum number of previous messages to include
            
        Returns:
            str: Formatted chat history string
        """
        if not self.chat_memory:
            return ""
        
        recent_messages = self.chat_memory[-max_messages:]
        formatted = []
        
        # Add timestamp and query results for better context
        for msg in recent_messages:
            formatted.append(f"Time: {msg.timestamp}")
            formatted.append(f"User: {msg.content}")
            if msg.response:
                formatted.append(f"Assistant: {msg.response}")
            if msg.query_result:  # Add query results if available
                formatted.append(f"Query Result: {msg.query_result}")
            formatted.append("---")  # Separator between messages
        
        return "\n".join(formatted)

    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of the chat context state."""
        return {
            'context': self.chat_context.get_summary() if self.chat_context else {},
            'history': self.chat_context.get_conversation_summary(max_entries=3) if self.chat_context else "",
            'session_id': self.chat_session_id
        }

    def update_context_from_query(self, query_result: Dict[str, Any]) -> None:
        """
        Update context based on the latest query result.
        
        Args:
            query_result (Dict[str, Any]): The result of the latest query
        """
        if not self.chat_context:
            self.chat_context = ChatContext()
        
        # Update referenced tables and columns from the query
        if 'tables_used' in query_result:
            self.chat_context.referenced_tables.update(query_result['tables_used'])
        if 'columns_used' in query_result:
            self.chat_context.referenced_columns.update(query_result['columns_used'])
            
        # Update current topic if available
        if 'topic' in query_result:
            self.chat_context.current_topic = query_result['topic']
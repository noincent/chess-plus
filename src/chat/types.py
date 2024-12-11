from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel

class ChatMessage(BaseModel):
    """Represents a single message in the chat conversation."""
    content: str
    role: str  # 'user' or 'assistant'
    timestamp: datetime = datetime.now()
    sql_query: Optional[str] = None
    query_result: Optional[Any] = None
    response: Optional[str] = None
    enhanced_question: Optional[str] = None  # Store enhanced question

    def dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format for serialization."""
        return {
            'content': self.content,
            'role': self.role,
            'timestamp': self.timestamp.isoformat(),
            'sql_query': self.sql_query,
            'query_result': self.query_result,
            'response': self.response,
            'enhanced_question': self.enhanced_question,
        }
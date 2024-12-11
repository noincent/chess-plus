from typing import Set, Dict, Any, Optional, List
from dataclasses import dataclass, field
from .types import ChatMessage
import logging

@dataclass
class ChatContext:
    """Maintains context information for a chat session."""
    
    def __init__(self):
        self.current_topic: Optional[str] = None
        self.referenced_tables: Set[str] = set()
        self.referenced_columns: Set[str] = set()
        self.conversation_history: List[Dict[str, Any]] = []
        self.active_constraints: Dict[str, Any] = {}
        self.question_context: Dict[str, Any] = {
            'questions': [],  # List to store all questions
            'timestamps': [],  # List to store corresponding timestamps
            'has_sql': []     # List to store SQL flags
        }
        logging.debug("Initialized new ChatContext")

    @property
    def last_query_result(self) -> Optional[Any]:
        """Compatibility property to get last query result from conversation history."""
        if self.conversation_history:
            return self.conversation_history[-1].get('query_result')
        return None

    def update(self, message: ChatMessage):
        """Update context based on a new message."""
        logging.info(f"Updating context with message: {message.content[:100]}...")
        
        if message.sql_query:
            logging.info(f"Processing SQL query for context: {message.sql_query[:100]}...")
            self._update_references(message.sql_query)
            
        # Store complete interaction in conversation history
        conversation_entry = {
            'timestamp': message.timestamp.isoformat(),
            'original_question': message.content,  # Store original question
            'question': getattr(message, 'enhanced_question', message.content),  # Use enhanced if available
            'sql_query': message.sql_query,
            'query_result': message.query_result,
            'response': message.response,
            'order': len(self.conversation_history) + 1
        }
        self.conversation_history.append(conversation_entry)
            
        self._update_question_context(message)
            
        logging.debug(f"Updated context state: {self.get_conversation_summary()}")

    def _update_references(self, sql_query: str):
        """Extract and update table/column references from SQL query."""
        previous_tables = set(self.referenced_tables)
        previous_columns = set(self.referenced_columns)
        
        # Extract table names (after FROM and JOIN)
        sql_lower = sql_query.lower()
        from_parts = sql_lower.split(' from ')[1].split(' where ')[0] if ' from ' in sql_lower else ''
        table_parts = from_parts.replace('join', ',').split(',')
        
        for part in table_parts:
            table_name = part.strip().split(' as ')[0].strip()
            if table_name:
                self.referenced_tables.add(table_name)
        
        # Extract column names (after SELECT and WHERE)
        if 'select ' in sql_lower:
            select_parts = sql_lower.split('select ')[1].split(' from ')[0]
            columns = [col.strip().split('.')[-1] for col in select_parts.split(',')]
            self.referenced_columns.update(col for col in columns if col)

        # Log changes
        new_tables = self.referenced_tables - previous_tables
        new_columns = self.referenced_columns - previous_columns
        if new_tables:
            logging.info(f"Added new tables to context: {new_tables}")
        if new_columns:
            logging.info(f"Added new columns to context: {new_columns}")

    def _update_question_context(self, message: ChatMessage):
        """Update the context based on the question content."""
        self.question_context['questions'].append(message.content)
        self.question_context['timestamps'].append(message.timestamp)
        self.question_context['has_sql'].append(bool(message.sql_query))
        
        logging.info(f"Updated question context with new question. Total questions: {len(self.question_context['questions'])}")

    def get_conversation_summary(self, max_entries: int = 3, format_type: str = 'full') -> Dict[str, Any]:
        """Get a comprehensive summary of recent conversations and context.
        
        Args:
            max_entries: Maximum number of recent entries to include
            format_type: Type of format to return ('full', 'sql_focused')
                - 'full': Original format with all context (backward compatibility)
                - 'sql_focused': Only SQL-related information
        """
        if not self.conversation_history:
            return {
                'current_topic': self.current_topic,
                'referenced_tables': list(self.referenced_tables),
                'referenced_columns': list(self.referenced_columns),
                'has_previous_result': False,
                'active_constraints': self.active_constraints,
                'conversation': [],
                'question_context': self.question_context
            } if format_type == 'full' else {
                'queries': [],
                'tables': list(self.referenced_tables),
                'columns': list(self.referenced_columns)
            }
            
        recent_entries = self.conversation_history[-max_entries:]
        
        if format_type == 'sql_focused':
            sql_focused = []
            for entry in recent_entries:
                if entry['sql_query']:  # Only include entries with SQL queries
                    sql_focused.append({
                        'question': entry['question'],
                        'sql': entry['sql_query'],
                        'result': entry['query_result'],
                        'timestamp': entry['timestamp']
                    })
            return {
                'queries': sql_focused,
                'tables': list(self.referenced_tables),
                'columns': list(self.referenced_columns)
            }
        
        # Original format for backward compatibility
        formatted_conversation = []
        for entry in recent_entries:
            formatted_conversation.extend([
                f"Time: {entry['timestamp']}",
                f"Question: {entry['question']}",
                f"Generated SQL: {entry['sql_query']}",
                f"Response: {entry['response']}",
                "---"
            ])
            
        return {
            'current_topic': self.current_topic,
            'referenced_tables': list(self.referenced_tables),
            'referenced_columns': list(self.referenced_columns),
            'has_previous_result': bool(self.last_query_result),
            'active_constraints': self.active_constraints,
            'conversation': formatted_conversation,
            'question_context': self.question_context
        }

    def clear(self):
        """Clear all context information."""
        self.current_topic = None
        self.referenced_tables.clear()
        self.referenced_columns.clear()
        self.conversation_history.clear()
        self.active_constraints.clear()
        self.question_context = {
            'questions': [],
            'timestamps': [],
            'has_sql': []
        }

    def get_last_n_queries(self, n: int = 3) -> List[Dict[str, Any]]:
        """Get the last n queries with their full context."""
        return self.conversation_history[-n:] if self.conversation_history else []
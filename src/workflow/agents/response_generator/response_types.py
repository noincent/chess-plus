from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class QueryContext(BaseModel):
    """Context for a database query."""
    question: str
    sql_query: str
    query_results: List[Any]
    current_topic: Optional[str] = None
    referenced_tables: List[str] = Field(default_factory=list)
    referenced_columns: List[str] = Field(default_factory=list)
    previous_result: Optional[Dict[str, Any]] = None
    question_context: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the context to a dictionary for JSON serialization."""
        return {
            "question": self.question,
            "sql_query": self.sql_query,
            "query_results": self.query_results,
            "current_topic": self.current_topic,
            "referenced_tables": self.referenced_tables,
            "referenced_columns": self.referenced_columns,
            "previous_result": self.previous_result,
            "question_context": self.question_context
        }

class ResponseMetadata(BaseModel):
    """Metadata about the generated response."""
    tables_mentioned: List[str] = Field(default_factory=list)
    columns_mentioned: List[str] = Field(default_factory=list)
    referenced_previous_query: bool = False
    contains_aggregates: bool = False
    response_type: str = "direct_answer"  # or "clarification", "error", "no_results"

    def to_dict(self) -> Dict[str, Any]:
        """Convert the metadata to a dictionary for JSON serialization."""
        return {
            "tables_mentioned": self.tables_mentioned,
            "columns_mentioned": self.columns_mentioned,
            "referenced_previous_query": self.referenced_previous_query,
            "contains_aggregates": self.contains_aggregates,
            "response_type": self.response_type
        }

class GeneratedResponse(BaseModel):
    """Complete response including metadata."""
    response_text: str
    reasoning: str
    context_used: QueryContext
    metadata: ResponseMetadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "response": self.response_text,
            "chain_of_thought_reasoning": self.reasoning,
            "context": self.context_used.dict(),
            "metadata": self.metadata.dict()
        }

class ResponseTemplates:
    """Templates for common response patterns."""
    
    @staticmethod
    def no_results(context: QueryContext) -> str:
        return (
            f"I searched the {', '.join(context.referenced_tables)} "
            f"but didn't find any matching results. "
            f"This might be because no data matches the specific criteria "
            f"in your question."
        )
    
    @staticmethod
    def error_response(error: str) -> str:
        return (
            f"I encountered an issue while processing your query. "
            f"The specific error was: {error}. "
            f"Could you please rephrase your question or provide more details?"
        )
    
    @staticmethod
    def clarification_needed(unclear_terms: List[str]) -> str:
        terms = ", ".join(unclear_terms)
        return (
            f"I need some clarification about {terms} to provide an accurate answer. "
            f"Could you please provide more details about these terms?"
        )
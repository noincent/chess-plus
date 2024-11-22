from typing import Optional, Any, Dict
from pydantic import BaseModel

class Task(BaseModel):
    """
    Represents a task to be processed by the system.
    
    Attributes:
        question_id (str): Unique identifier for the question
        db_id (str): Database identifier
        question (str): The question to be processed
        evidence (str): Supporting evidence for the task
        SQL (Optional[str]): SQL query if available
        difficulty (Optional[str]): Difficulty level of the task
        original_question (Optional[str]): Original question before context enhancement
        context_reasoning (Optional[str]): Reasoning for context-based modifications
    """
    question_id: str
    db_id: str
    question: str
    evidence: str = ""
    SQL: Optional[str] = None
    difficulty: Optional[str] = None
    original_question: Optional[str] = None
    context_reasoning: Optional[str] = None

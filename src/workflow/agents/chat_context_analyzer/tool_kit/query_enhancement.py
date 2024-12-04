from typing import Dict, Any
from workflow.agents.chat_tool import ChatTool
from workflow.chat_state import ChatSystemState
from llm.models import async_llm_chain_call, get_llm_chain
from llm.prompts import get_prompt
from llm.parsers import get_parser

class QueryEnhancement(ChatTool):
    """Tool for enhancing queries with conversation context."""
    
    def __init__(self, template_name: str = None, engine_config: Dict[str, Any] = None, 
                 parser_name: str = None):
        super().__init__()
        self.template_name = template_name
        self.engine_config = engine_config
        self.parser_name = parser_name
        
    def _run(self, state: ChatSystemState) -> None:
        """Enhance the query with or without contextual information."""
        # Prepare request with focus on schema-based improvements
        request_kwargs = {
            "CURRENT_QUESTION": state.task.question,
            "CONVERSATION_HISTORY": state.chat_context.get_conversation_summary() if state.chat_context else "",
            "REFERENCED_TABLES": list(state.chat_context.referenced_tables) if state.chat_context else [],
            "REFERENCED_COLUMNS": list(state.chat_context.referenced_columns) if state.chat_context else []
        }
        
        # Call LLM to enhance query
        response = async_llm_chain_call(
            prompt=get_prompt(template_name=self.template_name),
            engine=get_llm_chain(**self.engine_config),
            parser=get_parser(self.parser_name),
            request_list=[request_kwargs],
            step=self.tool_name,
            sampling_count=1
        )[0][0]
        
        # Update state with enhanced question
        state.task.original_question = state.task.question  # preserve original
        state.task.question = response["enhanced_question"]
        state.task.context_reasoning = response["reasoning"]
        
    def _get_updates(self, state: ChatSystemState) -> Dict[str, Any]:
        return {
            "original_question": state.task.original_question,
            "enhanced_question": state.task.question,
            "context_reasoning": state.task.context_reasoning
        }
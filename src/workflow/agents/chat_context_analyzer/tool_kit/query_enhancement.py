from typing import Dict, Any
from workflow.agents.tool import Tool
from workflow.chat_state import ChatSystemState
from llm.models import async_llm_chain_call, get_llm_chain
from llm.prompts import get_prompt
from llm.parsers import get_parser
import logging

class QueryEnhancement(Tool):
    """Tool for enhancing queries with database schema and specific values."""
    
    def __init__(self, template_name: str = None, engine_config: Dict[str, Any] = None, 
                 parser_name: str = None):
        super().__init__()
        self.template_name = template_name
        self.engine_config = engine_config
        self.parser_name = parser_name
        
    def _run(self, state: ChatSystemState) -> None:
        """Enhance the query with database schema and specific values."""
        logging.info(f"[QueryEnhancement] Original question: {state.task.question}")
        
        # Prepare request with focus on schema-based improvements
        request_kwargs = {
            "CURRENT_QUESTION": state.task.question,
            "INSTRUCTIONS": state.task.evidence,
            "CONVERSATION_HISTORY": state.chat_context.get_conversation_summary(format_type="sql_focused") if state.chat_context else "",
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
        
        # Update question with schema-enhanced version
        state.task.question = response["enhanced_question"]
        if state.task.context_reasoning is None:
            state.task.context_reasoning = ""
        state.task.context_reasoning += f"\nSchema reasoning: {response['reasoning']}"
        
        # Update message with enhanced question if it exists
        if state.chat_context and state.chat_context.conversation_history:
            latest_message = state.chat_context.conversation_history[-1]
            latest_message['enhanced_question'] = response["enhanced_question"]
        
        logging.info(f"[QueryEnhancement] Enhanced with schema: {state.task.question}")
        
    def _get_updates(self, state: ChatSystemState) -> Dict[str, Any]:
        """Return updates made by this tool for logging."""
        return {
            "original_question": state.task.original_question,
            "enhanced_question": state.task.question,
            "context_reasoning": state.task.context_reasoning
        }
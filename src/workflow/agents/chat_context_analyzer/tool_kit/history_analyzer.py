from typing import Dict, Any
from workflow.agents.tool import Tool
from workflow.chat_state import ChatSystemState
from llm.models import async_llm_chain_call, get_llm_chain
from llm.prompts import get_prompt
from llm.parsers import get_parser
import logging

class HistoryAnalyzer(Tool):
    """Tool for analyzing conversation history and extracting relevant context."""
    
    def __init__(self, template_name: str = None, engine_config: Dict[str, Any] = None, 
                 parser_name: str = None):
        super().__init__()
        self.template_name = template_name
        self.engine_config = engine_config
        self.parser_name = parser_name
        
    def _run(self, state: ChatSystemState) -> None:
        """Analyze conversation history to extract relevant context."""
        logging.info("=" * 80)
        logging.info("[HistoryAnalyzer] Starting history analysis")
        logging.info(f"[HistoryAnalyzer] Original question received: {state.task.question}")
        
        # Store original question
        state.task.original_question = state.task.question
        
        # If this is the first question (no chat context), return original question
        if not state.chat_context or not state.chat_context.conversation_history:
            logging.info("[HistoryAnalyzer] First question in session, no history to analyze")
            logging.info(f"[HistoryAnalyzer] Passing through original question: {state.task.question}")
            logging.info("=" * 80)
            return
            
        # Log conversation context that will be used for analysis
        conversation_summary = state.chat_context.get_conversation_summary(format_type="sql_focused") if state.chat_context else ""
        logging.info("[HistoryAnalyzer] Using conversation context for analysis:")
        logging.info(f"Conversation Summary (SQL focused):\n{conversation_summary}")
      
        # Prepare request focusing on conversation history analysis
        request_kwargs = {
            "CURRENT_QUESTION": state.task.question,
            "CONVERSATION_HISTORY": conversation_summary,
            "REFERENCED_TABLES": list(state.chat_context.referenced_tables) if state.chat_context else [],
            "REFERENCED_COLUMNS": list(state.chat_context.referenced_columns) if state.chat_context else []
        }
        
        # Call LLM to analyze history
        response = async_llm_chain_call(
            prompt=get_prompt(template_name=self.template_name),
            engine=get_llm_chain(**self.engine_config),
            parser=get_parser(self.parser_name),
            request_list=[request_kwargs],
            step=self.tool_name,
            sampling_count=1
        )[0][0]
        
        # Update with history-enhanced version
        state.task.question = response["enhanced_question"]
        state.task.context_reasoning = response["reasoning"]
        
        logging.info("[HistoryAnalyzer] Analysis complete")
        logging.info(f"[HistoryAnalyzer] Original question: {state.task.original_question}")
        logging.info(f"[HistoryAnalyzer] Enhanced question: {state.task.question}")
        logging.info(f"[HistoryAnalyzer] Context reasoning: {state.task.context_reasoning}")
        logging.info(f"[HistoryAnalyzer] Question being passed to next step: {state.task.question}")
        logging.info("=" * 80)
        
    def _get_updates(self, state: ChatSystemState) -> Dict[str, Any]:
        """Return updates made by this tool for logging."""
        return {
            "original_question": state.task.original_question,
            "enhanced_question": state.task.question,
            "context_reasoning": state.task.context_reasoning
        }

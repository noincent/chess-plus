from typing import Dict, List
from workflow.agents.chat_tool import ChatTool
from workflow.system_state import SystemState
from workflow.chat_state import ChatSystemState
from llm.models import get_llm_chain, async_llm_chain_call
from llm.prompts import get_prompt
from llm.parsers import get_parser

class ExtractKeywords(ChatTool):
    """
    Tool for extracting keywords from the question and hint, with context awareness.
    """
    
    def __init__(self, template_name: str = None, engine_config: str = None, parser_name: str = None):
        super().__init__()
        
        self.template_name = template_name
        self.engine_config = engine_config
        self.parser_name = parser_name
        
    def _run(self, state: SystemState):
        # If we have a ChatSystemState, get the conversation summary
        conversation_summary = None
        if isinstance(state, ChatSystemState) and state.chat_context:
            conversation_summary = state.chat_context.get_conversation_summary(max_entries=3)
        
        request_kwargs = {
            "QUESTION": state.task.question,
            "HINT": state.task.evidence,
            "CHAT_CONTEXT": conversation_summary if conversation_summary else "",
            "CHAT_HISTORY": conversation_summary.get('conversation', []) if conversation_summary else []
        }        
        
        # Call LLM with enhanced context
        engine = get_llm_chain(**self.engine_config)
        prompt = get_prompt(template_name=self.template_name)
        parser = get_parser(self.parser_name)
        
        results = async_llm_chain_call(
            prompt=prompt,
            engine=engine,
            parser=parser,
            request_list=[request_kwargs],
            step=self.tool_name,
            sampling_count=1
        )
        
        try:
            # Validate response format
            if not isinstance(results, list) or not isinstance(results[0], list) or not isinstance(results[0][0], list):
                raise ValueError("Invalid response format from LLM")
            
            # Extract and clean keywords
            keywords = results[0][0]
            if not isinstance(keywords, list):
                raise ValueError("Invalid response format: keywords must be a list")
            
            # Remove duplicates while preserving order
            seen = set()
            cleaned_keywords = [k for k in keywords if not (k in seen or seen.add(k))]
            
            state.keywords = cleaned_keywords
            
        except (IndexError, AttributeError) as e:
            raise ValueError(f"Invalid response format from LLM: {str(e)}")

    def _get_updates(self, state: SystemState) -> Dict:
        return {"keywords": state.keywords}
